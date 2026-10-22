"""One bounded native GRI closed-reactor numerical control, never an engine run."""
from pathlib import Path
import json
import modal
from modal_controls import image as controls_image
from build_methane import build_methane
ROOT=Path(__file__).resolve().parents[2]
image=(controls_image
       .add_local_dir(ROOT/'rde3d/native/pelec/MethaneZeroD','/opt/methane-case',copy=True)
       .add_local_file(Path(__file__).with_name('build_methane.py'),'/root/build_methane.py',copy=True)
       .run_function(build_methane,cpu=16,memory=65536,timeout=3600,include_source=False))
app=modal.App('prox-rde-3d-methane-control',include_source=False)


@app.function(image=image,serialized=True,gpu='H100!',cpu=(8.,8.),memory=(16384,16384),
              timeout=300,startup_timeout=180,retries=0,max_containers=1)
def control(case: dict, backend: str = 'gpu', dt: float = 5e-9,
            rtol: float = 1e-11, atol: float = 1e-22):
    import base64
    import hashlib
    import io
    import math
    import subprocess
    import tarfile
    import time
    from pathlib import Path
    from validation import native_log_errors
    if backend not in ('cpu','gpu') or not 1e-10 <= dt <= 1e-8:
        raise ValueError('Invalid bounded reactor configuration')
    if not 0 < rtol <= 1e-8 or not 0 < atol <= 1e-18:
        raise ValueError('Expected strict chemistry tolerances')
    if case['species_count']!=53 or not 0 < case['final_time_s'] <= 1e-6:
        raise ValueError('Only the declared short GRI control is permitted')
    if not case['independent_reference_checked']:
        raise ValueError('Independent reactor reference must pass before native execution')
    root=Path('/tmp/methane-control'); root.mkdir()
    name=f'{backend}_MethaneZeroD_dt{dt:g}'
    run=root/name; run.mkdir()
    source=Path('/opt/PeleC')
    text=(source/'Exec/RegTests/zeroD/zerod-1.inp').read_text()
    text='\n'.join(line for line in text.splitlines() if not line.strip().startswith(
        ('prob.','amr.regrid_int','amr.ref_ratio'))) + '\n'
    (run/'inputs.inp').write_text(text)
    (run/'reactor_case.json').write_text(json.dumps(case,indent=2)+'\n')
    command=[str(source/f'build-{backend}/Exec/RegTests/MethaneZeroD/PeleC-MethaneZeroD'),'inputs.inp',
        f"prob.T_init={case['temperature_K']}",f"prob.p_init={case['pressure_Pa']*10}",
        'prob.mass_fractions='+' '.join(map(str,case['Y'])),
        'pelec.do_hydro=0','pelec.chem_integrator=ReactorCvode','cvode.solve_type=GMRES',
        'cvode.max_order=5',f'ode.rtol={rtol}',f'ode.atol={atol}',f'pelec.fixed_dt={dt}',
        'pelec.init_shrink=1','max_step=10000',f"stop_time={case['final_time_s']}",
        'amr.plot_int=1000000','amr.plot_per=5e-9','amr.data_log=datlog',
        'amrex.abort_on_unused_inputs=1']
    started=time.monotonic()
    with (run/'solver.log').open('w') as log:
        try:
            result=subprocess.run(command,cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code=124;log.write('\nSUBPROCESS TIMEOUT: incomplete methane control\n')
    elapsed=time.monotonic()-started
    plots=sorted(run.glob('plt[0-9]*')); actual=None
    if plots:
        header=(plots[-1]/'Header').read_text().splitlines();actual=float(header[3+int(header[1])])
    logtext=(run/'solver.log').read_text(); errors=native_log_errors(logtext)
    passed=(code==0 and actual is not None and abs(actual-case['final_time_s'])<1e-15
        and not errors and 'Initializing CVODE:' in logtext
        and 'WARNING: turning on reactions while using ReactorNull' not in logtext)
    record=dict(name=name,backend=backend,dt=dt,rtol=rtol,atol=atol,command=command,
        returncode=code,final_time=actual,target_time=case['final_time_s'],wall_seconds=elapsed,
        log_errors=errors,completion_passed=passed,
        scope='Declared GRI polynomial-law numerical control; thermo fit validity and engine behavior unverified')
    (run/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w:gz') as archive:
        archive.add(root,arcname='controls')
        archive.add('/opt/pelec-methane-build',arcname='build')
    raw=payload.getvalue()
    return json.dumps(dict(status='controls_completed' if passed else 'controls_incomplete',runs=[record],
        artifact_sha256=hashlib.sha256(raw).hexdigest(),artifact_tar_gz_base64=base64.b64encode(raw).decode()))


@app.local_entrypoint()
def main(case_file: str, output: str, backend: str='gpu', dt: float=5e-9,
         rtol: float=1e-11, atol: float=1e-22):
    target=Path(output)
    if target.exists():raise FileExistsError('Refusing to overwrite methane evidence')
    result=control.remote(json.loads(Path(case_file).read_text()),backend,dt,rtol,atol)
    target.write_text(result+'\n')
    print('Saved bounded methane control: '+str(target))
