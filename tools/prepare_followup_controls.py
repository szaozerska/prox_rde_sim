"""Reproduce the additional controls motivated by the first diagnostic results."""
import json,sys,shutil
from pathlib import Path
from prepare_failure_matrix import replace_input

def main(folder):
    out=Path(folder).resolve();manifest=out/'gpu_planar_manifest.json';spec=json.loads(manifest.read_text());extra=[]
    variants=[('react_no_cleanup','pelec.eb_clean_massfrac',0,{'species_cleanup':False}),('react_closed_dt1ns','pelec.fixed_dt','1e-9',{'dt':1e-9}),('react_seed_u0','prob.seed_u',0,{})]
    for name,key,value,metadata in variants:
        if any(v['name']==name for v in spec['cases']):raise ValueError('Follow-up already prepared: '+name)
        c=json.loads((out/'react_closed.json').read_text());replace_input(c,key,value);c.update(metadata);c['diagnostic'].update(name=name,changed_input={key:value})
        p=out/(name+'.json');p.write_text(json.dumps(c,indent=2));extra.append(dict(name=name,case=str(p),limit=900 if name=='react_closed_dt1ns' else 600))
    spec['cases']=extra+spec['cases'];manifest.write_text(json.dumps(spec,indent=2))
    frozen=out/'foam_frozen_closed_upwind';shutil.copytree(out/'foam_frozen_closed',frozen);p=frozen/'system/fvSchemes';p.write_text(p.read_text().replace('Gauss limitedLinear 1','Gauss upwind'))
    variants=[('fixed_flux_unseeded','foam_react_unseeded',600),('fixed_flux_frozen_upwind','foam_frozen_closed_upwind',600),('fixed_flux_react_upwind','foam_react_closed_upwind',900),('fixed_flux_react_limited','foam_react_closed',900),('fixed_flux_short8um','foam_short_8um_dt01ns',600)]
    cases=[dict(name=name,case=str(out/case),limit=limit,ranks=16) for name,case,limit in variants]
    (out/'cpu_flux_manifest.json').write_text(json.dumps(dict(output=str(out/'cpu_flux_results'),cases=cases),indent=2))
if __name__=='__main__':main(sys.argv[1])
