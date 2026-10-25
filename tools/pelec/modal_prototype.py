"""Bounded one-H100 native 3D prototype and controls; never certify on completion alone."""
from pathlib import Path
import modal,json
from modal_controls import image as base_image
from build_prototype import build_prototype
ROOT=Path(__file__).resolve().parents[2]
image=(base_image.add_local_dir(ROOT/'rde3d/native/pelec/RDEPrototype','/opt/prototype-case',copy=True)
    .add_local_dir(ROOT/'rde3d/mechanisms/FFCMy12','/opt/compact-mechanism',copy=True)
    .add_local_file(Path(__file__).with_name('build_prototype.py'),'/root/build_prototype.py',copy=True)
    .run_function(build_prototype,cpu=16,memory=65536,timeout=2100,include_source=False)
    .pip_install('numpy==1.26.4','scipy==1.15.2','cantera==3.1.0','yt==4.4.1')
    .add_local_file(Path(__file__).with_name('analyze_prototype.py'),'/opt/prototype/tools/pelec/analyze_prototype.py',copy=True)
    .add_local_file(Path(__file__).with_name('analyze_sod.py'),'/opt/prototype/tools/pelec/analyze_sod.py',copy=True)
    .add_local_file(Path(__file__).with_name('wave_history.py'),'/opt/prototype/tools/pelec/wave_history.py',copy=True)
    .add_local_file(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml','/opt/prototype/rde3d/mechanisms/FFCMy12/mechanism.yaml',copy=True))
app=modal.App('prox-rde-3d-compact-prototype',include_source=False)
@app.function(image=image,serialized=True,gpu='H100!',cpu=(8.,8.),memory=(32768,32768),timeout=7500,startup_timeout=180,retries=0,max_containers=1)
def run_case(config:dict,profile:str='',limit:int=1200):
    import subprocess,time,io,tarfile,base64,hashlib,json
    from pathlib import Path
    from validation import native_log_errors
    if not 10<=limit<=7200 or config['mode'] not in (0,1,2):raise ValueError('Invalid bounded job')
    if not 0<config['stop']<=.005 or not 0<config['dt']<=1e-7:raise ValueError('Invalid time envelope')
    root=Path('/tmp/prototype');root.mkdir();(root/'case.json').write_text(json.dumps(config,indent=2))
    if profile:(root/'profile.dat').write_text(profile)
    (root/'inputs').write_text(config['inputs'])
    exe='/opt/PeleC/build-gpu/Exec/RegTests/RDEPrototype/PeleC-RDEPrototype'
    start=time.monotonic()
    with (root/'solver.log').open('w') as log:
        try:r=subprocess.run([exe,'inputs'],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=limit);code=r.returncode
        except subprocess.TimeoutExpired:code=124;log.write('\nTIME LIMIT: incomplete prototype\n')
    plots=sorted(root.glob('plt[0-9]*'));actual=None
    if plots:
        h=(plots[-1]/'Header').read_text().splitlines();actual=float(h[3+int(h[1])])
    errors=native_log_errors((root/'solver.log').read_text())
    result=dict(wall_seconds=time.monotonic()-start,returncode=code,actual_time=actual,requested_time=config['stop'],errors=errors,
        completed=code==0 and not errors and actual is not None and abs(actual-config['stop'])<1e-13,scope='Native CFD execution; physical validation separate.')
    (root/'result.json').write_text(json.dumps(result,indent=2))
    if config['mode']==2 and len(plots)>=2:
        with (root/'analysis.log').open('w') as log:
            analysis=subprocess.run(['python','/opt/prototype/tools/pelec/analyze_prototype.py',str(root)],stdout=log,stderr=subprocess.STDOUT,timeout=900)
        result['analysis_returncode']=analysis.returncode
        result['retained_output']='All sampled slices and diagnostics; full 3D initial/final fields. Intermediate full plotfiles omitted from download.'
        (root/'result.json').write_text(json.dumps(result,indent=2))
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz') as t:
        for p in root.iterdir():
            if config['mode']==2 and p.name.startswith('plt') and p not in (plots[0],plots[-1]) and (root/'preview.npz').exists():continue
            t.add(p,arcname='case/'+p.name)
        t.add('/opt/prototype-build',arcname='build')
    raw=buf.getvalue()
    return dict(run=result,checks=json.loads((root/'checks.json').read_text()) if (root/'checks.json').exists() else None,preview_base64=base64.b64encode((root/'preview.npz').read_bytes()).decode() if (root/'preview.npz').exists() else None,artifact_sha256=hashlib.sha256(raw).hexdigest(),artifact_tar_gz_base64=base64.b64encode(raw).decode())
@app.local_entrypoint()
def main(case_file:str,output:str,profile_file:str='',limit:int=1200):
    target=Path(output)
    if target.exists():raise FileExistsError(target)
    config=json.loads(Path(case_file).read_text());profile=Path(profile_file).read_text() if profile_file else ''
    call=run_case.spawn(config,profile,limit)
    target.with_suffix('.call.json').write_text(json.dumps(dict(function_call_id=call.object_id)))
    try:result=call.get(timeout=limit+600)
    except modal.exception.TimeoutError:call.cancel();raise
    target.write_text(json.dumps(result))
    if result.get('checks') is not None:
        import base64
        compact=target.parent/(target.stem+'_summary');compact.mkdir(exist_ok=False)
        (compact/'case.json').write_text(json.dumps(config,indent=2));(compact/'result.json').write_text(json.dumps(result['run'],indent=2));(compact/'checks.json').write_text(json.dumps(result['checks'],indent=2))
        if result.get('preview_base64'):(compact/'preview.npz').write_bytes(base64.b64decode(result['preview_base64']))
        print('Field checks:',result['checks']['checks'],flush=True)
    print(json.dumps(result['run'],indent=2))
