"""Cold embedded-annulus control using the existing native parser and Sod binary."""
from pathlib import Path
import json
import os
import modal
from modal_controls import image
if os.environ.get('PELEC_GEOMETRY_DIAGNOSTICS')=='1':
    from build_geometry_diagnostics import build_geometry_diagnostics
    image=(image.add_local_dir(Path(__file__).resolve().parents[2]/'rde3d/native/pelec/GeometryDiagnostics',
                               '/opt/geometry-diagnostics',copy=True)
        .add_local_file(Path(__file__).with_name('build_geometry_diagnostics.py'),'/root/build_geometry_diagnostics.py',copy=True)
        .run_function(build_geometry_diagnostics,cpu=16,memory=65536,timeout=1800,include_source=False))
app=modal.App('prox-rde-3d-cold-geometry',include_source=False)


@app.function(image=image,serialized=True,gpu='H100!',cpu=(8.,8.),memory=(32768,32768),
              timeout=420,startup_timeout=180,retries=0,max_containers=1)
def cold_geometry(nx: int=80):
    import base64
    import hashlib
    import io
    import json
    import subprocess
    import tarfile
    import time
    from pathlib import Path
    from validation import native_log_errors
    if nx not in (80,160):raise ValueError('Only the two declared isotropic cold grids are allowed')
    nz=nx*19//10
    root=Path('/tmp/cold-geometry');root.mkdir()
    run=root/f'n{nx}';run.mkdir()
    source=Path('/opt/PeleC')
    text=(source/'Exec/RegTests/Sod/sod-1.inp').read_text()
    text='\n'.join(line for line in text.splitlines() if not line.strip().startswith(
        ('amr.ref_ratio','amr.regrid_int')))+'\n'
    (run/'inputs.inp').write_text(text)
    # EB implicit sign convention: positive solid; negative fluid.
    implicit='max(sqrt(x*x+y*y)-3.81,min(3.31-sqrt(x*x+y*y),7.62-z))'
    executable=source/'build-gpu/Exec/RegTests/GeometryDiagnostics/PeleC-GeometryDiagnostics'
    diagnostic=executable.exists()
    if not diagnostic:executable=source/'build-gpu/Exec/RegTests/Sod/PeleC-Sod'
    command=[str(executable),'inputs.inp',
        'geometry.prob_lo=-4 -4 0','geometry.prob_hi=4 4 15.2',f'amr.n_cell={nx} {nx} {nz}',
        'amr.max_level=0','amr.blocking_factor=8','amr.max_grid_size=32',
        'prob.p_l=1','prob.p_r=1','prob.rho_l=1','prob.rho_r=1','prob.u_l=0','prob.u_r=0',
        'pelec.lo_bc=SlipWall SlipWall SlipWall','pelec.hi_bc=SlipWall SlipWall SlipWall',
        'pelec.do_mol=1','pelec.cfl=0.3','pelec.eb_isothermal=0','pelec.eb_noslip=0',
        'pelec.redistribution_type=StateRedist','pelec.eb_srd_max_order=0',
        'pelec.eb_clean_massfrac=0','pelec.fixed_dt=0.0001','pelec.init_shrink=1',
        'max_step=10','stop_time=0.001','eb2.geom_type=parser',f'eb2.parser_function={implicit}',
        'amr.plot_int=1000000','amr.plot_vars=density Temp rho_E',
        'amr.derive_plot_vars=pressure x_velocity y_velocity z_velocity',
        'amrex.abort_on_unused_inputs=1']
    started=time.monotonic()
    with (run/'solver.log').open('w') as log:
        try:
            result=subprocess.run(command,cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code=124;log.write('\nSUBPROCESS TIMEOUT: incomplete cold geometry control\n')
    elapsed=time.monotonic()-started;plots=sorted(run.glob('plt[0-9]*'));actual=None
    if plots:
        h=(plots[-1]/'Header').read_text().splitlines();actual=float(h[3+int(h[1])])
    errors=native_log_errors((run/'solver.log').read_text())
    passed=code==0 and actual is not None and abs(actual-.001)<1e-14 and not errors
    record=dict(command=command,returncode=code,final_time=actual,target_time=.001,
        wall_seconds=elapsed,log_errors=errors,completion_passed=passed,n_cell=[nx,nx,nz],
        geometry_m=dict(outer_radius=.0381,inner_radius=.0331,core_length=.0762,outlet_z=.152),
        parser_function_cgs=implicit,surface_diagnostics=diagnostic,
        binary_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
        scope='Closed nondimensional GammaLaw equilibrium and geometry only; no methane/feed/engine/normal-area gate pass')
    (run/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w:gz') as archive:
        archive.add(root,arcname='geometry')
        if diagnostic:archive.add('/opt/pelec-geometry-build',arcname='build')
    raw=payload.getvalue()
    return json.dumps(dict(status='control_completed' if passed else 'control_incomplete',runs=[record],
        artifact_sha256=hashlib.sha256(raw).hexdigest(),artifact_tar_gz_base64=base64.b64encode(raw).decode()))


@app.local_entrypoint()
def main(output: str, nx: int=80):
    target=Path(output)
    if target.exists():raise FileExistsError('Refusing to overwrite cold geometry evidence')
    call=cold_geometry.spawn(nx)
    try:
        result=call.get(timeout=600)  # Includes queueing after the bounded image build.
    except modal.exception.TimeoutError:
        call.cancel()
        target.write_text(json.dumps({'status':'client_deadline_exceeded','function_call_id':call.object_id,
            'scope':'Queue/startup/execution exceeded 600 s; cancelled this call only; no validation or artifact claimed'})+'\n')
        raise
    target.write_text(result+'\n')
    print('Saved cold geometry control: '+str(target))
