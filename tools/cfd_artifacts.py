"""Verify a cloud result checksum before safely extracting its native evidence."""
import argparse,base64,hashlib,io,json,tarfile
from pathlib import Path
def unpack(source,out,endpoints=False):
    v=json.loads(Path(source).read_text());raw=base64.b64decode(v['artifact_tar_gz_base64'],validate=True)
    if hashlib.sha256(raw).hexdigest()!=v['artifact_sha256']:raise ValueError('Artifact checksum mismatch')
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(raw)) as t:
        members=t.getmembers()
        plots=sorted({m.name.split('/')[1] for m in members if len(m.name.split('/'))>1 and m.name.split('/')[1].startswith('plt')})
        if endpoints and plots:
            members=[m for m in members if len(m.name.split('/'))<2 or m.name.split('/')[1] not in plots[1:-1]]
        t.extractall(out,members=members,filter='data')
    print(json.dumps(v.get('run',v.get('manifest',{})),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--endpoints',action='store_true');a=p.parse_args();unpack(a.source,a.out,a.endpoints)
