"""Test the remaining chemistry integration closure residual after the flux repair."""
import json,re,shutil,sys
from pathlib import Path
out=Path(sys.argv[1]).resolve();case=out/'foam_fixed_flux_tight_chemistry'
shutil.copytree(out/'foam_react_closed_upwind',case)
p=case/'constant/chemistryProperties';text=p.read_text()
for key,value in [('absTol','1e-12'),('relTol','1e-8')]:
    text,n=re.subn(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',text)
    if n!=1:raise ValueError((key,n))
p.write_text(text)
spec=dict(output=str(out/'cpu_flux_tight_results'),cases=[dict(name='fixed_flux_tight_chemistry',case=str(case),limit=900,ranks=16)])
(out/'cpu_flux_tight_manifest.json').write_text(json.dumps(spec,indent=2))
