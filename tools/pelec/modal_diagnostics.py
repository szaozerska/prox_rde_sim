"""Queue bounded independent GPU diagnostics on one H100, preserving every result."""
import json,base64
from pathlib import Path
from modal_prototype import app,run_case
@app.local_entrypoint()
def batch(manifest:str):
    spec=json.loads(Path(manifest).read_text());out=Path(spec['output']);out.mkdir(parents=True,exist_ok=True)
    calls=[]
    for item in spec['cases']:
        target=out/(item['name']+'.json')
        if target.exists():raise FileExistsError(target)
        c=json.loads(Path(item['case']).read_text());profile=Path(item['profile']).read_text() if item.get('profile') else ''
        call=run_case.spawn(c,profile,item['limit']);calls.append((item,c,call))
    (out/'calls.json').write_text(json.dumps([dict(name=i['name'],id=call.object_id) for i,c,call in calls],indent=2))
    for item,c,call in calls:
        try:r=call.get(timeout=7500)
        except Exception as e:
            (out/(item['name']+'.error.json')).write_text(json.dumps(dict(error=repr(e),call=call.object_id)));print(item['name'],repr(e),flush=True);continue
        (out/(item['name']+'.json')).write_text(json.dumps(r))
        summary=out/(item['name']+'_summary');summary.mkdir(exist_ok=False)
        (summary/'case.json').write_text(json.dumps(c,indent=2));(summary/'result.json').write_text(json.dumps(r['run'],indent=2))
        if r.get('checks') is not None:(summary/'checks.json').write_text(json.dumps(r['checks'],indent=2))
        if r.get('preview_base64'):(summary/'preview.npz').write_bytes(base64.b64decode(r['preview_base64']))
        print(item['name'],r['run'],r.get('checks',{}).get('checks') if r.get('checks') else None,flush=True)
