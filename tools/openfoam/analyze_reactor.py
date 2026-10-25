"""Independent constant-volume comparison and upstream clipping audit."""
import json,re,sys
from pathlib import Path
import numpy as np
import cantera as ct
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from rde3d.native import read_field

def analyze(path):
    path=Path(path);ref=json.loads((path/'reference.json').read_text());names=ref['species']
    gas=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'));gas.TPX=ref['initial_temperature_K'],ref['initial_pressure_Pa'],'CH4:1.176,O2:2'
    reactor=ct.IdealGasReactor(gas,energy='on',clone=True);net=ct.ReactorNet([reactor]);net.rtol=1e-11;net.atol=1e-20
    folders=[]
    for p in path.iterdir():
        if p.is_dir():
            try:folders.append((float(p.name),p))
            except ValueError:pass
    rows=[]
    for t,p in sorted(folders):
        if t:net.advance(t)
        T=np.array(read_field(p/'T',8))[:,0];P=np.array(read_field(p/'p',8))[:,0];Y=np.array([np.array(read_field(p/s,8))[:,0] for s in names]).T
        rows.append(dict(time_s=t,T_K=float(T.mean()),p_Pa=float(P.mean()),temperature_relative_error=abs(float(T.mean())/reactor.T-1),species_max_error=float(np.max(abs(Y.mean(axis=0)-reactor.phase.Y))),min_species=float(Y.min()),species_sum_error=float(np.max(abs(Y.sum(axis=1)-1)))))
    log=next(path.glob('log.*.detonationFoam_V2.0')).read_text();audit=re.findall(r'SPECIES_AUDIT time=(\S+) preClipMin=(\S+) clippedMass=(\S+) inertMin=(\S+)',log)
    clipped=sum(float(x[2]) for x in audit)
    checks=dict(completion='\nEnd\n' in log and abs(rows[-1]['time_s']-5e-7)<1e-15,nonnegative=min(x['min_species'] for x in rows)>=0,species_sum=max(x['species_sum_error'] for x in rows)<1e-9,
        temperature=max(x['temperature_relative_error'] for x in rows)<.005,species=max(x['species_max_error'] for x in rows)<.005,measured_noninert_clipping=clipped<1e-18)
    result=dict(checks=checks,history=rows,noninert_clipped_mass_kg=clipped,minimum_preclip_inert=min(float(x[3]) for x in audit),scope='Short constant-volume methane control; 0.5% transient comparison tolerance. Does not validate detonation or mesh accuracy.')
    (path/'reactor_checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(checks=checks,max_temperature_error=max(x['temperature_relative_error'] for x in rows),max_species_error=max(x['species_max_error'] for x in rows),clipped_mass=clipped),indent=2))
    return result
if __name__=='__main__':analyze(sys.argv[1])
