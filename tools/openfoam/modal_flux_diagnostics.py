"""Experimental one-line mass-flux consistency repair; retain the upstream controls."""
import json,io,tarfile,base64
from pathlib import Path
import modal
from modal_solver import image as baseline_image

from build_flux_patch import patch_flux

image=baseline_image.add_local_file(Path(__file__).with_name('build_flux_patch.py'),'/root/build_flux_patch.py',copy=True).run_function(patch_flux,cpu=8,memory=32768,timeout=1200,include_source=False)
app=modal.App('prox-rde-3d-foam-flux-diagnostic',include_source=False)
@app.function(image=image,serialized=True,cpu=(16.,16.),memory=(32768,32768),timeout=7500,retries=0,max_containers=1)
def run_patched(payload:bytes,limit:int=600,ranks:int=16):
    import sys
    sys.path.insert(0,'/opt/cfd-tools')
    from native_execution import execute_case
    return execute_case(payload,limit,ranks)

@app.local_entrypoint()
def batch(manifest:str):
    spec=json.loads(Path(manifest).read_text());out=Path(spec['output']);out.mkdir(exist_ok=True,parents=True);calls=[]
    for item in spec['cases']:
        if (out/(item['name']+'.json')).exists():raise FileExistsError(item['name'])
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as t:
            for p in Path(item['case']).iterdir():t.add(p,arcname=p.name)
        call=run_patched.spawn(buf.getvalue(),item['limit'],16);calls.append((item,call))
    (out/'calls.json').write_text(json.dumps([dict(name=i['name'],id=c.object_id) for i,c in calls],indent=2))
    for item,call in calls:
        try:r=call.get(timeout=7500)
        except Exception as e:(out/(item['name']+'.error.json')).write_text(json.dumps(dict(error=repr(e))));print(item['name'],repr(e),flush=True);continue
        (out/(item['name']+'.json')).write_text(json.dumps(r));s=out/(item['name']+'_summary');s.mkdir(exist_ok=False)
        for key in ('case','checks','manifest'):(s/(key+'.json')).write_text(json.dumps(r[key],indent=2))
        print(item['name'],(r.get('checks') or {}).get('checks'),flush=True)
