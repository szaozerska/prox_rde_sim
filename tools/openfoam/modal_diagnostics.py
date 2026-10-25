"""Queue bounded independent CPU diagnostics on one 16-core worker."""
import json,base64,io,tarfile
from pathlib import Path
from modal_solver import app,run_case
@app.local_entrypoint()
def batch(manifest:str):
    spec=json.loads(Path(manifest).read_text());out=Path(spec['output']);out.mkdir(parents=True,exist_ok=True);calls=[]
    for item in spec['cases']:
        if (out/(item['name']+'.json')).exists():raise FileExistsError(item['name'])
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as t:
            for p in Path(item['case']).iterdir():t.add(p,arcname=p.name)
        call=run_case.spawn(buf.getvalue(),item['limit'],item.get('ranks',16));calls.append((item,call))
    (out/'calls.json').write_text(json.dumps([dict(name=i['name'],id=call.object_id) for i,call in calls],indent=2))
    for item,call in calls:
        try:r=call.get(timeout=7500)
        except Exception as e:
            (out/(item['name']+'.error.json')).write_text(json.dumps(dict(error=repr(e),call=call.object_id)));print(item['name'],repr(e),flush=True);continue
        (out/(item['name']+'.json')).write_text(json.dumps(r))
        if r.get('checks') is not None:
            summary=out/(item['name']+'_summary');summary.mkdir(exist_ok=False)
            for key in ('case','checks','manifest'):(summary/(key+'.json')).write_text(json.dumps(r[key],indent=2))
            (summary/'preview.npz').write_bytes(base64.b64decode(r['preview_base64']))
        print(item['name'],r['manifest'],r.get('checks',{}).get('checks') if r.get('checks') else None,flush=True)
