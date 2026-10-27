"""Checkpointed MPI/CUDA NETL-startup jobs; at most four GPUs per job."""
from pathlib import Path
import modal
import os
from modal_smoke import image as base_image
from build_startup import build_startup
ROOT=Path(__file__).resolve().parents[2]
image=(base_image.apt_install('libopenmpi-dev','openmpi-bin')
    .add_local_dir(ROOT/'rde3d/native/pelec/RDEStartup','/opt/startup-case',copy=True)
    .add_local_dir(ROOT/'rde3d/mechanisms/FFCMy12','/opt/compact-mechanism',copy=True)
    .add_local_file(Path(__file__).with_name('build_startup.py'),'/root/build_startup.py',copy=True)
    .run_function(build_startup,cpu=32,memory=98304,timeout=3600,include_source=False)
    .pip_install('numpy==1.26.4','yt==4.4.1')
    .add_local_file(Path(__file__).with_name('analyze_startup.py'),'/opt/analyze_startup.py',copy=True)
    .add_local_file(Path(__file__).with_name('mpi_gpu_rank.py'),'/opt/mpi_gpu_rank.py',copy=True))
if os.environ.get('RDE_CUDA_MPI_IMAGE'):
    image=(modal.Image.from_id(os.environ['RDE_CUDA_MPI_IMAGE'])
        .add_local_file(Path(__file__).with_name('analyze_startup.py'),'/opt/analyze_startup.py',copy=True)
        .add_local_file(Path(__file__).with_name('mpi_gpu_rank.py'),'/opt/mpi_gpu_rank.py',copy=True))
elif os.environ.get('RDE_CUDA_MPI')=='1':
    from build_cuda_mpi import build_cuda_mpi
    image=(image.add_local_file(Path(__file__).with_name('build_cuda_mpi.py'),'/root/build_cuda_mpi.py',copy=True)
        .run_function(build_cuda_mpi,cpu=32,memory=65536,timeout=3600,include_source=False))
if os.environ.get('RDE_CVODE_DIRECT_BUILD')=='1':
    from build_cvode_direct import build_cvode_direct
    image=(image.add_local_file(Path(__file__).with_name('build_cvode_direct.py'),'/root/build_cvode_direct.py',copy=True)
        .run_function(build_cvode_direct,cpu=32,memory=98304,timeout=3600,include_source=False))
image=image.add_local_file(Path(__file__).with_name('audit_native_log.py'),'/opt/audit_native_log.py',copy=True)
app=modal.App('prox-rde-netl-startup',include_source=False)
volume=modal.Volume.from_name('prox-rde-netl-startup',create_if_missing=True)
@app.function(image=image,serialized=True,gpu='H100:4',cpu=(16.,16.),memory=(98304,98304),
              timeout=18000,startup_timeout=600,retries=0,max_containers=1,volumes={'/results':volume})
def run(config:dict,run_id:str,ranks:int=4,limit:int=7200,restart:str=''):
    import subprocess,time,json,re,os,shutil,sys
    sys.path.insert(0,'/opt')
    from audit_native_log import audit_native_log
    from pathlib import Path
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',run_id) or ranks not in (1,2,4) or not 10<=limit<=14400:
        raise ValueError('Invalid bounded allocation')
    root=Path('/results')/run_id
    if root.exists():raise FileExistsError(root)
    root.mkdir();(root/'case.json').write_text(json.dumps(config,indent=2));(root/'inputs').write_text(config['inputs'])
    direct=config.get('chemistry_linear_solver')=='sparse_direct'
    build_dir='/opt/cvode-direct-build' if direct else '/opt/startup-build'
    executable='/opt/PeleC/'+('build-mpi-direct' if direct else 'build-mpi')+'/Exec/RegTests/RDEStartup/PeleC-RDEStartup'
    shutil.copytree(build_dir,root/'build')
    built=json.loads((root/'build/manifest.json').read_text())
    if config.get('native_source_sha256') and config['native_source_sha256']!=built['case_sha256']:
        raise ValueError('Cached binary does not match requested native source')
    mpirun='/opt/cuda-mpi/bin/mpirun' if Path('/opt/cuda-mpi/bin/mpirun').exists() else 'mpirun'
    command=[mpirun,'--allow-run-as-root','--bind-to','none','-np',str(ranks),
        'python','/opt/mpi_gpu_rank.py',executable,'inputs','amr.message_int=1']
    if Path('/opt/cuda-mpi-build/manifest.json').exists():shutil.copy('/opt/cuda-mpi-build/manifest.json',root/'build/cuda_mpi.json')
    if restart:
        path=Path('/results')/restart
        if not path.is_dir() or not path.resolve().is_relative_to(Path('/results').resolve()):raise ValueError('Invalid checkpoint')
        command+=['amr.restart='+str(path)]
    device=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.total','--format=csv'],capture_output=True,text=True).stdout
    topology=subprocess.run(['nvidia-smi','topo','-m'],capture_output=True,text=True).stdout
    (root/'allocation.json').write_text(json.dumps({'devices':device,'topology':topology,'ranks':ranks,'command':command},indent=2))
    start=time.monotonic();env=dict(os.environ,OMP_NUM_THREADS='1');last_analysis=start
    if mpirun.startswith('/opt/cuda-mpi'):
        env['LD_LIBRARY_PATH']='/opt/cuda-mpi/lib:'+env.get('LD_LIBRARY_PATH','')
        env['OMPI_MCA_btl']='self,smcuda,tcp'
        env['OMPI_MCA_pml']='ob1'
    analyzer=None;analysis_log=(root/'analysis.log').open('w')
    with (root/'solver.log').open('w') as log:
        process=subprocess.Popen(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        while process.poll() is None and time.monotonic()-start<limit:
            time.sleep(15)
            audit=audit_native_log((root/'solver.log').read_text())
            if audit['emergency_stop_required'] and not (root/'emergency_stop.json').exists():
                (root/'emergency_stop.json').write_text(json.dumps(audit,indent=2,allow_nan=False))
                if not (root/'operator_stop.json').exists():
                    (root/'operator_stop.json').write_text(json.dumps({'action':'checkpoint_stop','reason':'Native extrema exceeded emergency bounds; see emergency_stop.json'}))
                (root/'dump_and_stop').touch()
            # Read the control through the API: mounted-volume snapshots do not auto-reload.
            try:
                control=json.loads(b''.join(volume.read_file('controls/'+run_id+'.json')))
            except FileNotFoundError:control={}
            if control.get('action')=='checkpoint_stop' and not (root/'operator_stop.json').exists():
                (root/'operator_stop.json').write_text(json.dumps(control,indent=2))
                (root/'dump_and_stop').touch()
            if (analyzer is None or analyzer.poll() is not None) and time.monotonic()-last_analysis>120:
                analyzer=subprocess.Popen(['python','/opt/analyze_startup.py',str(root)],stdout=analysis_log,stderr=subprocess.STDOUT)
                last_analysis=time.monotonic()
            if limit>=600 and time.monotonic()-start>=limit-120:
                (root/'dump_and_stop').touch()
                if not (root/'operator_stop.json').exists():
                    (root/'operator_stop.json').write_text(json.dumps({'action':'checkpoint_stop','reason':'Approaching bounded wall-time limit'}))
            volume.commit()
        if process.poll() is None:
            import signal
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            code=124
        else:code=process.returncode
    if analyzer is not None:analyzer.wait(timeout=900)
    analysis=subprocess.run(['python','/opt/analyze_startup.py',str(root),'--final'],stdout=analysis_log,stderr=subprocess.STDOUT,timeout=1200)
    analysis_log.close()
    plots=sorted(root.glob('plt[0-9]*'));actual=None
    if plots:
        h=(plots[-1]/'Header').read_text().splitlines();actual=float(h[3+int(h[1])])
    result={'returncode':code,'wall_seconds':time.monotonic()-start,'actual_saved_time_s':actual,
        'analysis_returncode':analysis.returncode,'requested_time_s':config['stop'],'completed':code==0 and actual is not None and abs(actual-config['stop'])<1e-12,
        'checkpoints':[p.name for p in sorted(root.glob('chk[0-9]*'))],
        'emergency_stop':(root/'emergency_stop.json').exists(),
        'operator_stop':json.loads((root/'operator_stop.json').read_text()) if (root/'operator_stop.json').exists() else None,
        'scope':'Execution status only; physical conclusions require native-field analysis.'}
    (root/'result.json').write_text(json.dumps(result,indent=2));volume.commit();print(result,flush=True)
    return result
@app.function(image=image,serialized=True,cpu=1,timeout=120)
def probe_build():
    import subprocess,json
    from pathlib import Path
    p=Path('/opt/cuda-mpi-build/manifest.json')
    report=json.loads(p.read_text()) if p.exists() else {'mpi':'system MPI'}
    direct=Path('/opt/cvode-direct-build/manifest.json')
    if direct.exists():report['direct_backend']=json.loads(direct.read_text())
    return report
@app.local_entrypoint()
def main(case_file:str='',run_id:str='',ranks:int=4,limit:int=7200,restart:str='',build_only:bool=False,launch_only:bool=False):
    import json
    if build_only:
        print(probe_build.remote(),flush=True);return
    import hashlib
    config=json.loads(Path(case_file).read_text())
    config['native_source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'rde3d/native/pelec/RDEStartup').glob('prob*')}
    call=run.spawn(config,run_id,ranks,limit,restart)
    Path(case_file).with_suffix('.call.json').write_text(json.dumps({'id':call.object_id,'run_id':run_id}))
    print('CALL',call.object_id,flush=True)
    if not launch_only:print(call.get(),flush=True)
