"""Small native CPU/GPU shock and closed-reactor controls; no RDE run."""
from pathlib import Path
import modal
import os
from modal_smoke import image as smoke_image
from build_controls import build_controls

image=(smoke_image.add_local_file(Path(__file__).with_name('build_controls.py'),
                                 '/root/build_controls.py',copy=True)
       .run_function(build_controls,cpu=16,memory=65536,timeout=3600,include_source=False)
       .add_local_file(Path(__file__).with_name('validation.py'),'/root/validation.py',copy=True))
if os.environ.get('PELEC_STRICT_EOS') == '1':
    from build_convergence import build_convergence
    image=(image.add_local_file(Path(__file__).with_name('build_convergence.py'),
                                '/root/build_convergence.py',copy=True)
           .run_function(build_convergence,cpu=16,memory=65536,timeout=3600,include_source=False))
app=modal.App('prox-rde-3d-pelec-controls',include_source=False)


@app.function(image=image,serialized=True,gpu='H100!',cpu=(8.0,8.0),
              memory=(16384,16384),timeout=900,startup_timeout=180,
              retries=0,max_containers=1)
def controls(suite: str = "all", rtol: float = 1e-11, atol: float = 1e-22, backend_filter: str = "both", linear_solver: str = "GMRES", chem_dt: float = 5e-6, chem_order: int = 5):
    import base64
    import hashlib
    import io
    import json
    import math
    import subprocess
    import tarfile
    import time
    from datetime import datetime,timezone
    from pathlib import Path
    from validation import native_log_errors
    root=Path('/tmp/pelec-controls');root.mkdir()
    source=Path('/opt/PeleC')
    records=[]
    cases=[('gpu','Sod',64,.001),('gpu','Sod',128,.0005),
           ('gpu','Sod',256,.00025),('gpu','Sod',128,.00025),
           ('cpu','Sod',128,.0005),
           ('cpu','zeroD',8,chem_dt),('gpu','zeroD',8,chem_dt),('gpu','zeroD',8,chem_dt/2)]
    if chem_order not in (1,2,3,4,5):
        raise ValueError('CVODE BDF order must be 1 through 5')
    if not 2e-7 <= chem_dt <= 1e-5:
        raise ValueError('Chemistry control dt must keep the 1 ms horizon within max_step')
    if suite not in ('all','shock','chem'):
        raise ValueError('suite must be all, shock, or chem')
    if suite != 'all':
        cases=[item for item in cases if (item[1]=='Sod') == (suite=='shock')]
    if linear_solver not in ('GMRES','dense_direct','denseAJ_direct'):
        raise ValueError('Unsupported control linear solver')
    if linear_solver != 'GMRES' and backend_filter != 'cpu':
        raise ValueError('Dense direct controls require the CPU-only case filter')
    if backend_filter not in ('both','cpu','gpu'):
        raise ValueError('backend_filter must be both, cpu, or gpu')
    if backend_filter != 'both':
        cases=[item for item in cases if item[0]==backend_filter]
    if not (0 < rtol <= 1e-6 and 0 < atol <= 1e-6):
        raise ValueError('Expected positive strict chemistry tolerances')
    for backend,case,nx,dt in cases:
        name=f'{backend}_{case}_n{nx}_dt{dt:g}'
        run=root/name;run.mkdir()
        input_name='sod-1.inp' if case=='Sod' else 'zerod-1.inp'
        text=(source/f'Exec/RegTests/{case}/{input_name}').read_text()
        text='\n'.join(line for line in text.splitlines()
                       if not line.strip().startswith(('amr.regrid_int','amr.ref_ratio'))) + '\n'
        (run/'inputs.inp').write_text(text)
        final=.2 if case=='Sod' else .001
        exe=source/f'build-{backend}/Exec/RegTests/{case}/PeleC-{case}'
        command=[str(exe),'inputs.inp','amr.max_level=0',f'amr.n_cell={nx} 8 8',
                 'amr.max_grid_size=64','max_step=10000',f'stop_time={final}',
                 f'pelec.fixed_dt={dt}','pelec.init_shrink=1',
                 'amrex.abort_on_unused_inputs=1','amr.plot_int=1000000']
        if case=='Sod':
            command+=['amr.plot_vars=density Temp',
                      'amr.derive_plot_vars=pressure x_velocity y_velocity z_velocity']
        else:
            command+=['prob.T_init=1001','pelec.do_hydro=0',f'amr.plot_per={max(5e-6,min(1e-5,dt))}',
                      'amr.data_log=datlog','pelec.plot_massfrac=1',
                      'pelec.chem_integrator=ReactorCvode',f'cvode.solve_type={linear_solver}',
                      f'ode.rtol={rtol}',f'ode.atol={atol}',f'cvode.max_order={chem_order}']
        started=time.monotonic()
        with (run/'solver.log').open('w') as log:
            try:
                completed=subprocess.run(command,cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=90)
                code=completed.returncode
            except subprocess.TimeoutExpired:
                code=124;log.write('\nSUBPROCESS TIMEOUT: incomplete control\n')
        elapsed=time.monotonic()-started
        plots=sorted(run.glob('plt[0-9]*'));actual=None
        if plots:
            header=(plots[-1]/'Header').read_text().splitlines()
            actual=float(header[3+int(header[1])])
        passed=code==0 and actual is not None and math.isclose(actual,final,rel_tol=0,abs_tol=1e-13)
        logtext=(run/'solver.log').read_text()
        log_errors=native_log_errors(logtext)
        passed=passed and not log_errors
        if case=='zeroD':
            passed=passed and 'Initializing CVODE:' in logtext and 'WARNING: turning on reactions while using ReactorNull' not in logtext
        record=dict(name=name,backend=backend,case=case,dt=dt,nx=nx,command=command,
                    returncode=code,final_time=actual,target_time=final,
                    wall_seconds=elapsed,log_errors=log_errors,completion_passed=passed)
        records.append(record)
        (run/'result.json').write_text(json.dumps(record,indent=2)+'\n')
        if not passed:
            break  # Preserve first failure; no dependent batch through it.
    manifest={'status':'controls_completed' if len(records)==len(cases) and all(r['completion_passed'] for r in records) else 'controls_incomplete',
              'checked_at_utc':datetime.now(timezone.utc).isoformat(),
              'scope':'Native control execution only; independent field/reference checks required',
              'build_variant':'strict_eos' if Path('/opt/pelec-controls-build/strict-eos.json').exists() else 'upstream_default',
              'runs':records}
    (root/'result.json').write_text(json.dumps(manifest,indent=2)+'\n')
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w:gz') as archive:
        archive.add(root,arcname='controls')
        archive.add('/opt/pelec-controls-build',arcname='build')
    raw=payload.getvalue()
    return json.dumps(dict(manifest,artifact_sha256=hashlib.sha256(raw).hexdigest(),
                           artifact_tar_gz_base64=base64.b64encode(raw).decode()))
