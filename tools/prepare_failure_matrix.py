"""One-change-at-a-time annular diagnostics; retain controls and declared hypotheses."""
import sys,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/pelec'))
from prepare_prototype import prepare as gpu_prepare
sys.path.insert(0,str(ROOT/'tools/openfoam'))
from prepare_annulus import prepare as cpu_prepare

def replace_input(c,key,value):
    pattern=r'^'+re.escape(key)+r'\s*=.*$'
    c['inputs'],n=re.subn(pattern,key+' = '+str(value),c['inputs'],flags=re.M)
    if n!=1:raise ValueError((key,n))
def main(out):
    out=Path(out).resolve();out.mkdir(exist_ok=False,parents=True);gpu=[];cpu=[]
    variants=[('frozen_closed',False,0,True,True,2e-8),('frozen_open',False,2,True,True,2e-8),('react_closed',True,0,True,True,2e-8),('react_closed_dt5ns',True,0,True,True,5e-9),('chemistry_only',True,0,True,False,2e-8),('react_unseeded',True,0,False,True,2e-8),('cold_open',False,2,False,True,2e-8)]
    for name,react,feed,seed,hydro,dt in variants:
        p=out/(name+'.json');c=gpu_prepare(p,mode='cold' if name=='cold_open' else 'annulus',n=128,stop=1e-6,dt=dt,feed=feed,seed=seed,reacting=react,clean_species=True)
        replace_input(c,'amr.plot_per',5e-7);replace_input(c,'pelec.hi_bc','SlipWall SlipWall SlipWall');replace_input(c,'pelec.do_hydro',int(hydro))
        c['diagnostic']=dict(name=name,closed_outlet=True,hydro=hydro,scope='Isolating numerical failure, not an engine performance case.');p.write_text(json.dumps(c,indent=2))
        gpu.append(dict(name=name,case=str(p),limit=600))
    base=ROOT/'runs3d/foam_compact_reactor_v6'
    for name,react,feed,seed,dt,scheme in [('frozen_closed',False,False,True,2e-8,'limitedLinear 1'),('frozen_open',False,True,True,2e-8,'limitedLinear 1'),('react_closed',True,False,True,2e-8,'limitedLinear 1'),('react_closed_dt5ns',True,False,True,5e-9,'limitedLinear 1'),('react_closed_upwind',True,False,True,2e-8,'upwind'),('react_unseeded',True,False,False,2e-8,'limitedLinear 1'),('cold_open',False,True,False,2e-8,'limitedLinear 1')]:
        d=out/('foam_'+name);cpu_prepare(base,d,ntheta=576,stop=1e-6,dt=dt)
        p=d/'init_annulus.json';c=json.loads(p.read_text());c['diagnostic']=dict(name=name,reacting=react,feed=feed,seed=seed,closed_outlet=True,species_convection=scheme)
        if not seed:c['seed_length']=0
        if name=='cold_open':c['Yprod']=c['Y'];c['Tprod']=300
        p.write_text(json.dumps(c,indent=2))
        p=d/'system/controlDict';p.write_text(re.sub(r'writeInterval\s+[^;]+;','writeInterval 5e-7;',p.read_text()))
        if not react:
            p=d/'constant/chemistryProperties';p.write_text(re.sub(r'chemistry\s+on;','chemistry off;',p.read_text()))
        if scheme=='upwind':
            p=d/'system/fvSchemes';p.write_text(p.read_text().replace('Gauss limitedLinear 1','Gauss upwind'))
        for p in (d/'0').iterdir():
            s=p.read_text();s=s.replace('outlet { type zeroGradient; }','outlet { type slip; }') if p.name=='U' else s
            if not feed:
                kind='slip' if p.name=='U' else 'zeroGradient'
                s=s.split('boundaryField')[0]+f'boundaryField {{ injector {{ type {kind}; }} innerWall {{ type {kind}; }} outerWall {{ type {kind}; }} outlet {{ type {kind}; }} }}\n'
            p.write_text(s)
        cpu.append(dict(name=name,case=str(d),limit=900,ranks=16))
    for backend,cases in [('gpu',gpu),('cpu',cpu)]:
        (out/(backend+'_manifest.json')).write_text(json.dumps(dict(output=str(out/(backend+'_results')),cases=cases),indent=2))
    print(out)
if __name__=='__main__':main(sys.argv[1])
