"""Fetch compact evidence from the dedicated startup volume; never remove raw data."""
import argparse,json,hashlib
from pathlib import Path
import modal

def fetch(run_id,output):
    target=Path(output);target.mkdir(parents=True,exist_ok=True)
    volume=modal.Volume.from_name('prox-rde-netl-startup')
    hashes={}
    for name in ('case.json','result.json','checks.json','allocation.json','solver.log','analysis.log','gridlog','preview.npz','build/manifest.json','build/cuda_mpi.json','operator_stop.json','emergency_stop.json'):
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
        try:
            raw=b''.join(volume.read_file(run_id+'/'+name));path.write_bytes(raw)
            hashes[name]=hashlib.sha256(raw).hexdigest();print(name,len(raw),flush=True)
        except (modal.exception.NotFoundError,FileNotFoundError):print('not yet available:',name,flush=True)
    (target/'fetch.json').write_text(json.dumps({'volume':'prox-rde-netl-startup','run_id':run_id,'sha256':hashes},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run_id');p.add_argument('output');a=p.parse_args();fetch(a.run_id,a.output)
