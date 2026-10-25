"""Bounded formed-wave control on one H100; no engine or persistent deployment."""
from pathlib import Path
import json
import modal
from modal_methane import image as methane_image
from build_wave import build_wave
ROOT=Path(__file__).resolve().parents[2]
image=(methane_image.add_local_dir(ROOT/'rde3d/native/pelec/FormedWave','/opt/wave-case',copy=True)
    .add_local_file(Path(__file__).with_name('build_wave.py'),'/root/build_wave.py',copy=True)
    .run_function(build_wave,cpu=16,memory=65536,timeout=1500,include_source=False))
app=modal.App('prox-rde-3d-formed-wave',include_source=False)

@app.function(image=image,serialized=True,gpu='H100!',cpu=(8.,8.),memory=(16384,16384),
    timeout=1100,startup_timeout=180,retries=0,max_containers=1)
def run_wave(case:dict,profile:str,stop_time:float=2e-9,dt:float=2e-10,reacting:bool=True,reconstruction_order:int=1, hydro:str="mol"):
    import base64,hashlib,io,subprocess,tarfile,time
    from pathlib import Path
    from validation import native_log_errors
    if hydro not in ('mol','godunov','weno'):raise ValueError('Unknown native transport')
    if reconstruction_order not in (1,2):raise ValueError('Expected native first/second-order reconstruction')
    if case['nx'] not in (256,512) or not case['independent_reference_checked']:
        raise ValueError('Only prepared short planar controls permitted')
    if not 0<stop_time<=2e-7 or not 0<dt<=case['dx_m']/40000*(1+1e-12):
        raise ValueError('Outside bounded time/CFL envelope')
    if hashlib.sha256(profile.encode()).hexdigest()!=case['profile_sha256']:
        raise ValueError('Initial profile checksum mismatch')
    root=Path('/tmp/formed-wave');root.mkdir();(root/'profile.dat').write_text(profile)
    (root/'case.json').write_text(json.dumps(case,indent=2)+'\n')
    source=Path('/opt/PeleC');nx=case['nx'];dx=case['dx_m']*100
    inputs=f'''stop_time = {stop_time}
max_step = 10000
geometry.is_periodic = 0 1 1
geometry.coord_sys = 0
geometry.prob_lo = 0 0 0
geometry.prob_hi = {nx*dx} {8*dx} {8*dx}
amr.n_cell = {nx} 8 8
amr.max_level = 0
amr.blocking_factor = 8
amr.max_grid_size = 64
amr.checkpoint_files_output = 0
amr.plot_files_output = 1
amr.plot_file = plt
amr.plot_int = 1000000
amr.plot_per = 1e-8
amr.plot_vars = density rho_E Temp
amr.derive_plot_vars = pressure x_velocity y_velocity z_velocity
pelec.plot_massfrac = 1
pelec.plot_rhoy = 0
amr.data_log = datlog
pelec.lo_bc = FOExtrap Interior Interior
pelec.hi_bc = FOExtrap Interior Interior
pelec.do_react = {int(reacting)}
pelec.do_hydro = 1
pelec.do_mol = {int(hydro == "mol")}
pelec.mol_iters = 1
pelec.mol_iorder = {reconstruction_order}
pelec.plm_iorder = {reconstruction_order}
pelec.diffuse_temp = 0
pelec.diffuse_enth = 0
pelec.diffuse_spec = 0
pelec.diffuse_vel = 0
pelec.chem_integrator = ReactorCvode
cvode.solve_type = GMRES
cvode.max_order = 5
ode.rtol = 1e-11
ode.atol = 1e-22
pelec.fixed_dt = {dt}
pelec.init_shrink = 1
pelec.cfl = 0.3
pelec.dt_cutoff = 1e-20
pelec.eb_clean_massfrac = 0
pelec.sum_interval = 1
pelec.v = 1
amr.v = 1
prob.profile = profile.dat
amrex.abort_on_unused_inputs = 1
amrex.signal_handling = 0
'''
    if hydro != 'mol':
        inputs += 'pelec.ppm_type = 1\npelec.use_hybrid_weno = '+str(int(hydro == 'weno'))+'\n'
    if not reacting:inputs='\n'.join(line for line in inputs.splitlines() if not line.startswith(('cvode.','ode.')))+'\n'
    (root/'inputs').write_text(inputs)
    command=[str(source/'build-gpu/Exec/RegTests/FormedWave/PeleC-FormedWave'),'inputs']
    started=time.monotonic();limit=120 if stop_time<=2e-9 else 900
    with (root/'solver.log').open('w') as log:
        try:code=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=limit).returncode
        except subprocess.TimeoutExpired:code=124;log.write('\nSUBPROCESS TIMEOUT: incomplete formed wave\n')
    elapsed=time.monotonic()-started;errors=native_log_errors((root/'solver.log').read_text())
    plots=sorted(root.glob('plt[0-9]*'));actual=None
    if plots:
        header=(plots[-1]/'Header').read_text().splitlines();actual=float(header[3+int(header[1])])
    completed=code==0 and not errors and actual is not None and abs(actual-stop_time)<1e-15
    record=dict(returncode=code,completion_passed=completed,log_errors=errors,command=command,
        target_time=stop_time,final_time=actual,dt=dt,reacting=reacting,reconstruction_order=reconstruction_order,hydro=hydro,wall_seconds=elapsed,subprocess_limit_s=limit,
        scope='Completion only; independent field/propagation checks required; not an engine result')
    (root/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w:gz') as archive:
        archive.add(root,arcname='wave');archive.add('/opt/pelec-wave-build',arcname='build')
    raw=payload.getvalue()
    return json.dumps(dict(status='completed' if completed else 'incomplete',run=record,
        artifact_sha256=hashlib.sha256(raw).hexdigest(),artifact_tar_gz_base64=base64.b64encode(raw).decode()))

@app.local_entrypoint()
def main(case_file:str,profile_file:str,output:str,stop_time:float=2e-9,dt:float=2e-10,reacting:bool=True,reconstruction_order:int=1, hydro:str="mol"):
    target=Path(output)
    if target.exists():raise FileExistsError('Refusing to overwrite wave evidence')
    call=run_wave.spawn(json.loads(Path(case_file).read_text()),Path(profile_file).read_text(),stop_time,dt,reacting,reconstruction_order,hydro)
    target.with_suffix(target.suffix+'.call.json').write_text(json.dumps(dict(function_call_id=call.object_id,output=str(target),scope='Recovery identifier only; no completion or validation claim'))+'\n')
    try:result=call.get(timeout=600 if stop_time<=2e-9 else 1400)
    except modal.exception.TimeoutError:
        call.cancel();target.write_text(json.dumps(dict(status='client_deadline_exceeded',function_call_id=call.object_id))+'\n');raise
    target.write_text(result+'\n');print('Saved bounded native wave artifacts: '+str(target))
