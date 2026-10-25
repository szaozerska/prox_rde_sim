"""Explicitly invoked, bounded CPU integration batch. Imports do not launch jobs."""
import json
from pathlib import Path
import modal
from build import build

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT/'source_lock.json').read_text())
image = (modal.Image.debian_slim(python_version='3.12')
         .apt_install('git','build-essential','cmake','ninja-build')
         .add_local_dir(ROOT/'native','/opt/adapter/native',copy=True)
         .add_local_file(ROOT/'build.py','/root/build.py',copy=True)
         .run_function(build,kwargs={'lock':LOCK},cpu=16,memory=32768,
                       timeout=3600,include_source=False)
         .add_local_file(ROOT/'control.py','/opt/adapter/control.py',copy=True))
app = modal.App('prox-rde-2d-pelec',include_source=False)

@app.function(image=image,serialized=True,cpu=2,memory=4096,timeout=900,
              retries=0,max_containers=1)
def run_controls():
    import base64
    import hashlib
    import io
    import json
    import shutil
    import subprocess
    import sys
    import tarfile
    import time
    from pathlib import Path
    sys.path.insert(0,'/opt/adapter')
    from control import CASE,inputs,log_errors,plot_time
    root=Path('/tmp/pelec-2d-controls');root.mkdir()
    exe=Path('/opt/PeleC/build-2d/Exec/RegTests/Methane2D/PeleC-Methane2D')
    rows=[]
    for name,dt,reacting in [('reacting',1e-8,True),('half_step',5e-9,True),('frozen',1e-8,False)]:
        run=root/name;run.mkdir()
        (run/'inputs').write_text(inputs(CASE,dt,reacting))
        (run/'case.json').write_text(json.dumps(dict(CASE,dt=dt,reacting=reacting),indent=2)+'\n')
        start=time.monotonic()
        with (run/'solver.log').open('w') as log:
            try:
                proc=subprocess.run([str(exe),'inputs'],cwd=run,stdout=log,
                                    stderr=subprocess.STDOUT,timeout=240)
                code=proc.returncode
            except subprocess.TimeoutExpired:
                code=124;log.write('\nERROR: native subprocess timeout\n')
        plots=sorted(run.glob('plt[0-9]*'))
        actual=plot_time(plots[-1]) if plots else None
        errors=log_errors((run/'solver.log').read_text())
        complete=code==0 and not errors and actual is not None and abs(actual-CASE['final_time_s'])<1e-16
        row=dict(name=name,returncode=code,log_errors=errors,final_time_s=actual,
                 completion_passed=complete,wall_seconds=time.monotonic()-start)
        rows.append(row);(run/'execution.json').write_text(json.dumps(row,indent=2)+'\n')
        if not complete:break
    shutil.copytree('/opt/pelec-2d-build',root/'build')
    mech=Path('/opt/PeleC/Submodules/PelePhysics/Mechanisms/grimech30')
    (root/'mechanism').mkdir()
    for name in ('mechanism.yaml','mechanism.H','mechanism.cpp'):
        shutil.copyfile(mech/name,root/'mechanism'/name)
    record=dict(backend='pelec',dimension=2,runs=rows,
                status='native_controls_completed' if len(rows)==3 and all(r['completion_passed'] for r in rows) else 'native_controls_failed',
                interpretation='Execution only; independent analysis must pass. Not an RDE.')
    (root/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as tar:tar.add(root,arcname='controls')
    data=stream.getvalue()
    return dict(record,artifact_sha256=hashlib.sha256(data).hexdigest(),artifact_base64=base64.b64encode(data).decode())

@app.local_entrypoint()
def main(output: str):
    path=Path(output)
    if path.exists():raise FileExistsError('Use a new output directory')
    path.mkdir(parents=True)
    call=run_controls.spawn()
    (path/'call.json').write_text(json.dumps({'function_call_id':call.object_id})+'\n')
    try:result=call.get(timeout=1200)
    except BaseException:
        call.cancel()
        (path/'status.json').write_text('{"status":"client_failed_or_interrupted"}\n')
        raise
    import base64,hashlib
    raw=base64.b64decode(result.pop('artifact_base64'),validate=True)
    if hashlib.sha256(raw).hexdigest()!=result['artifact_sha256']:raise ValueError('Artifact checksum mismatch')
    (path/'native.tar.gz').write_bytes(raw)
    (path/'status.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if result['status']!='native_controls_completed':raise RuntimeError('Native integration failed; inspect saved evidence')
