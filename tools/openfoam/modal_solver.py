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
    .add_local_file(ROOT/'rde3d/native.py','/opt/cfd-tools/rde3d/native.py',copy=True))
app=modal.App('prox-rde-3d-detonationfoam',include_source=False)

@app.function(image=image,serialized=True,cpu=(16.,16.),memory=(32768,32768),timeout=7500,retries=0,max_containers=1)
def run_case(payload:bytes,limit:int=600,ranks:int=1):
    import io,tarfile,subprocess,time,hashlib,base64,json
    from pathlib import Path
    if not 1<=limit<=7200 or ranks not in (1,2,4,8,16):raise ValueError('Outside authorized bounded CPU envelope')
    root=Path('/tmp/case');root.mkdir()
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:archive.extractall(root,filter='data')
    annulus=(root/'init_annulus.json').exists()
    if annulus:subprocess.run(['chown','-R','2101:2101',str(root)],check=True)
    if not (root/'system/controlDict').is_file():raise ValueError('Missing case')
    start=time.monotonic();records=[]
    commands=[['chemkinToFoam','mechanism.inp','thermo.dat','transport.foam','constant/foam/reactions.foam','constant/foam/thermo.foam'],['blockMesh'],['checkMesh','-allTopology','-allGeometry']]
    if annulus:commands += [['postProcess','-func','writeCellCentres','-time','0'],['python','/opt/cfd-tools/initialize_annulus.py']]
    if ranks>1:commands.append(['decomposePar','-force'])
    commands.append((['mpirun','--allow-run-as-root','-np',str(ranks),'detonationFoam_V2.0','-parallel'] if ranks>1 else ['detonationFoam_V2.0']))
    if ranks>1:commands.append(['reconstructPar'])
    if annulus:commands.append(['python','/opt/cfd-tools/tools/openfoam/analyze_annulus.py',str(root)])
    for i,cmd in enumerate(commands):
        stamp=time.monotonic();name=cmd[0]
        with (root/f'log.{i}.{name}').open('w') as log:
            try:
                r=subprocess.run((['runuser','-u','cfd-runner','--'] if annulus else [])+['bash','-c','cfd_command=("$@"); set --; source /opt/foam-env.sh && exec "${cfd_command[@]}"','bash',*cmd],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=600 if cmd[0]=='reconstructPar' or 'analyze_annulus.py' in ' '.join(cmd) else max(10,limit-(time.monotonic()-start)))
                code=r.returncode
            except subprocess.TimeoutExpired:code=124;log.write('\nTIME LIMIT: incomplete run\n')
        if name=='checkMesh' and code==0 and 'Mesh OK.' not in (root/f'log.{i}.{name}').read_text():code=65
        records.append(dict(command=cmd,returncode=code,wall_seconds=time.monotonic()-stamp))
        if code:break
    manifest=dict(commands=records,wall_seconds=time.monotonic()-start,input_sha256=hashlib.sha256(payload).hexdigest(),ranks=ranks,
        scope='Execution evidence only. Completion, clipping, chemistry and wave checks required.')
    (root/'run.json').write_text(json.dumps(manifest,indent=2))
    times=sorted((p for p in root.iterdir() if p.is_dir() and p.name.replace('.','',1).replace('e-','').isdigit()),key=lambda p:float(p.name))
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as t:
        for p in root.iterdir():
            if p.name.startswith('processor') or p.name=='dynamicCode':continue
            if annulus and (root/'preview.npz').exists() and p in times and p not in (times[0],times[-1]):continue
            t.add(p,arcname='case/'+p.name)
        t.add('/opt/foam-build',arcname='build')
    raw=out.getvalue()
    return dict(manifest=manifest,checks=json.loads((root/'checks.json').read_text()) if (root/'checks.json').exists() else None,case=json.loads((root/'case.json').read_text()) if (root/'case.json').exists() else None,preview_base64=base64.b64encode((root/'preview.npz').read_bytes()).decode() if (root/'preview.npz').exists() else None,artifact_sha256=hashlib.sha256(raw).hexdigest(),artifact_tar_gz_base64=base64.b64encode(raw).decode())

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
