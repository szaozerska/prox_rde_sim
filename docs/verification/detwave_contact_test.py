"""Targeted stationary-interface and formed-planar comparisons; no engine tuning."""
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'rde_sim_starter'))
from solver import Solver,PERIODIC,WALL
from controlled import formed_profile, formed_strip
from run import _fingerprint

root=Path(__file__).resolve().parents[2]
m=json.loads((root/'rde_sim_starter/runs/detwave_25fi5_high_flux_compact_seed/inputs.json').read_text())
gas=m['resolved']['gas'];c=m['calibration'];p=c['p1'];rho=p/(gas[2]*300)
result=dict(fingerprint=_fingerprint(),contacts=[],planar=[])
for flux in ['hll','hllc']:
    for hot in [1500,3000]:
        for reactive in [False,True]:
            g=gas.copy();g[3]=gas[3] if reactive else 0
            s=Solver(2,64,.000125,.000125,g,(PERIODIC,PERIODIC,WALL,WALL),source_cfl=.2,flux=flux)
            z=(np.arange(64)+.5)*s.dy;T=np.where(z<.004,300,hot)[None,:]
            xi=np.where(z<.004,0.,1.)[None,:]
            s.set_prim(p/(gas[2]*T),0,0,p,xi);initial=s.conserved_totals()
            while s.t<10e-6-1e-16:s.step(dt_max=10e-6-s.t)
            w=s.prim();burn=s.cumulative_source[4]/(2*s.dx*rho)*1000
            row=dict(flux=flux,hot_K=hot,reactive=reactive,burned_equivalent_mm=burn,
                mixed_cells=int(np.sum((w[4,0]>.001)&(w[4,0]<.999))),
                energy_relative_change=float((s.conserved_totals()[3]-initial[3])/initial[3]),
                invalid_states=s.invalid_state_count,steps=s.steps)
            result['contacts'].append(row);print(row,flush=True)
    profile=formed_profile(c)
    s,x=formed_strip(c,profile,dx=.000125,rows=2,length=.12,shock=.04,source_cfl=.2)
    s.flux=flux;s.flux_code=int(flux=='hllc')
    locations=[]
    for target in [5e-6,10e-6]:
        while s.t<target-1e-16:s.step(dt_max=target-s.t)
        w=s.prim();locations.append(float(x[np.flatnonzero(w[3,:,0]>2*p)[-1]]))
    row=dict(flux=flux,end_us=s.t*1e6,threshold_speed_mps=(locations[1]-locations[0])/5e-6,
             pressure_front_m=locations,invalid_states=s.invalid_state_count,steps=s.steps)
    result['planar'].append(row);print(row,flush=True)
with Path(sys.argv[1]).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
