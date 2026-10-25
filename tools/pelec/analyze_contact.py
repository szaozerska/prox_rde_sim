"""Equal-pressure material transport control: measure spurious pressure and velocity."""
import sys,json
from pathlib import Path
import numpy as np
import cantera as ct
from analyze_sod import load_fields
from wave_history import audit_history
ROOT=Path(__file__).resolve().parents[2]
def analyze(run):
    run=Path(run);c=json.loads((run/'case.json').read_text());g=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'))
    rows=[];names=('pressure','x_velocity','density','Temp')+tuple('Y('+s+')' for s in g.species_names)
    for p in sorted(run.glob('plt[0-9]*')):
        t,f,dx,lo=load_fields(p,names);Y=np.stack([f['Y('+s+')'] for s in g.species_names],axis=-1)
        rows.append(dict(time_s=t,pressure_relative_error=float(np.max(abs(f['pressure']/10/c['diagnostic']['pressure_Pa']-1))),velocity_error_mps=float(np.max(abs(f['x_velocity']/100-c['diagnostic']['velocity_mps']))),min_species=float(Y.min()),species_sum_error=float(np.max(abs(Y.sum(axis=-1)-1))),temperature_minmax_K=[float(f['Temp'].min()),float(f['Temp'].max())],finite=all(bool(np.isfinite(v).all()) for v in f.values())))
    history=audit_history((run/'solver.log').read_text(),c['stop'],c['dt'],temperature_bounds=(200,5000))
    r=dict(rows=rows,every_step_history=history,scope='Nonreacting translating contact. Pressure/velocity errors measure mixture-interface artifacts; no engine validation.')
    (run/'contact_checks.json').write_text(json.dumps(r,indent=2));return r
if __name__=='__main__':analyze(sys.argv[1])
