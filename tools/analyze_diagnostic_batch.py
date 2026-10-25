"""Wait for bounded planar batch results, verify artifacts, then analyze native fields."""
import sys,json,time,subprocess
from pathlib import Path
from cfd_artifacts import unpack
ROOT=Path(__file__).resolve().parents[1]
def main(manifest,backend):
    m=json.loads(Path(manifest).read_text());out=Path(m['output']);deadline=time.monotonic()+7200
    for item in m['cases']:
        source=out/(item['name']+'.json');error=out/(item['name']+'.error.json')
        while not source.exists() and not error.exists():
            if time.monotonic()>deadline:raise TimeoutError(item['name'])
            time.sleep(10)
        if error.exists():continue
        # Result writes can take seconds; a compact summary or next return is not guaranteed.
        for retry in range(60):
            try:v=json.loads(source.read_text());break
            except json.JSONDecodeError:time.sleep(2)
        else:raise RuntimeError('Incomplete result JSON')
        if v.get('checks') is not None:continue # Annular runs were analyzed in the native container.
        dest=out/(item['name']+'_native')
        if not dest.exists():unpack(source,dest)
        case=dest/'case'
        if backend=='gpu':
            c=json.loads((case/'case.json').read_text())
            args=[sys.executable,str(ROOT/'tools/pelec/analyze_contact.py'),str(case)] if c.get('case_type')=='contact' else [sys.executable,str(ROOT/'tools/pelec/analyze_wave.py'),str(case),c['diagnostic']['reference']]
        else:args=[sys.executable,str(ROOT/'tools/openfoam/analyze_wave.py'),str(case)]
        with (dest/'analysis.log').open('w') as log:r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
        (dest/'analysis_status.json').write_text(json.dumps(dict(returncode=r.returncode,command=args),indent=2))
        if backend=='cpu' and r.returncode==0:
            with (dest/'element_audit.log').open('w') as log:subprocess.run([sys.executable,str(ROOT/'tools/openfoam/audit_element_conventions.py'),str(case)],stdout=log,stderr=subprocess.STDOUT,check=True)
        print(item['name'],'analysis',r.returncode,flush=True)
if __name__=='__main__':main(*sys.argv[1:])
