"""Pinned detonationFoam CPU execution, bounded jobs and complete failure evidence."""
from pathlib import Path
import json
import modal
ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads(Path(__file__).with_name('source.lock.json').read_text())

from build_cpu import build_solver

image=(modal.Image.from_registry(LOCK['openfoam_image'],add_python='3.12')
    .dockerfile_commands('USER root','ENTRYPOINT []')
    .apt_install('git','build-essential')
    .add_local_file(Path(__file__).with_name('foam-env.sh'),'/opt/foam-env.sh',copy=True)
    .add_local_file(Path(__file__).with_name('build_cpu.py'),'/root/build_cpu.py',copy=True)
    .run_function(build_solver,kwargs={'lock':LOCK},cpu=16,memory=32768,timeout=3600,include_source=False))
image=(image.add_local_file(Path(__file__).with_name('initialize_annulus.py'),'/opt/cfd-tools/initialize_annulus.py',copy=True)
    .dockerfile_commands('RUN useradd --uid 2101 --create-home cfd-runner')
    .pip_install('numpy==1.26.4','scipy==1.15.2')
    .add_local_file(Path(__file__).with_name('analyze_annulus.py'),'/opt/cfd-tools/tools/openfoam/analyze_annulus.py',copy=True)
    .add_local_file(ROOT/'rde3d/native.py','/opt/cfd-tools/rde3d/native.py',copy=True)
    .add_local_file(Path(__file__).with_name('native_execution.py'),'/opt/cfd-tools/native_execution.py',copy=True))
app=modal.App('prox-rde-3d-detonationfoam',include_source=False)

@app.function(image=image,serialized=True,cpu=(16.,16.),memory=(32768,32768),timeout=7500,retries=0,max_containers=1)
def run_case(payload:bytes,limit:int=600,ranks:int=1):
    import sys
    sys.path.insert(0,'/opt/cfd-tools')
    from native_execution import execute_case
    return execute_case(payload,limit,ranks)

@app.local_entrypoint()
def main(case_dir:str,output:str,limit:int=600,ranks:int=1):
    import io,tarfile
    target=Path(output)
    if target.exists():raise FileExistsError(target)
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz') as t:
        for p in Path(case_dir).iterdir():t.add(p,arcname=p.name)
    call=run_case.spawn(buf.getvalue(),limit,ranks)
    target.with_suffix('.call.json').write_text(json.dumps(dict(function_call_id=call.object_id)))
    try:result=call.get(timeout=limit+600)
    except modal.exception.TimeoutError:call.cancel();raise
    target.write_text(json.dumps(result))
    if result.get('checks') is not None:
        import base64
        compact=target.parent/(target.stem+'_summary');compact.mkdir(exist_ok=False)
        for key in ('case','checks','manifest'):(compact/(key+'.json')).write_text(json.dumps(result[key],indent=2))
        (compact/'preview.npz').write_bytes(base64.b64decode(result['preview_base64']))
    print(json.dumps(result['manifest'],indent=2))
