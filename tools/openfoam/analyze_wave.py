"""Compare CPU propagation with the same CJ/ZND reference used for PeleC."""
import json,re,sys
from pathlib import Path
import numpy as np
import cantera as ct
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools/pelec'))
from rde3d.native import read_field

def crossing(x,y,level):
    hits=np.flatnonzero((y[:-1]>=level)&(y[1:]<level))
    if not len(hits):return None
    i=hits[-1];return float(x[i]+(level-y[i])/(y[i+1]-y[i])*(x[i+1]-x[i]))
def analyze(path):
    path=Path(path);c=json.loads((path/'wave_case.json').read_text());ref=json.loads((path/'reference.json').read_text());cj=ref['CJ'];nx=c['nx'];x=(np.arange(nx)+.5)*c['dx_m']
    gas=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'));gas.TP=298.15,ct.one_atm;hf=gas.standard_enthalpies_RT*ct.gas_constant*gas.T/gas.molecular_weights
    element_matrix=np.array([[gas.n_atoms(s,e)*gas.atomic_weight(e)/gas.molecular_weights[s] for e in range(gas.n_elements)] for s in range(gas.n_species)])
    y0=np.array(cj['initial']['Y']);elements0=y0@element_matrix
    folders=[]
    for p in path.iterdir():
        if p.is_dir():
            try:folders.append((float(p.name),p))
            except ValueError:pass
    rows=[];profiles=[];max_element=0;max_sum=0;min_y=0;maxchar=0;finite=True
    for t,p in sorted(folders):
        P=np.array(read_field(p/'p',nx))[:,0];T=np.array(read_field(p/'T',nx))[:,0];Y=np.array([np.array(read_field(p/s,nx))[:,0] for s in gas.species_names]).T
        U=np.array(read_field(p/'U',nx))[:,0]
        finite=finite and all(np.isfinite(v).all() for v in (P,T,Y,U))
        states=ct.SolutionArray(gas,nx);states.TPY=T,P,Y
        maxchar=max(maxchar,float(np.max(abs(U)+states.sound_speed)))
        q=(y0@hf-Y@hf)/cj['q_equilibrium_Jkg'];max_element=max(max_element,float(np.max(abs(Y@element_matrix-elements0))));max_sum=max(max_sum,float(np.max(abs(Y.sum(axis=1)-1))));min_y=min(min_y,float(Y.min()))
        pos=[crossing(x,P,cj['pressure_Pa']+f*(cj['VN']['p']-cj['pressure_Pa'])) for f in (.25,.5,.75)];heat=crossing(x,q,.5)
        rows.append(dict(time_s=t,shock_locations_m=pos,half_heat_distance_m=pos[1]-heat if pos[1] is not None and heat is not None else None,T_min_K=float(T.min()),T_max_K=float(T.max()),p_min_Pa=float(P.min()),p_max_Pa=float(P.max())))
        profiles.append(dict(pressure_Pa=P,temperature_K=T,heat_fraction=q,velocity_mps=U,species_Y=Y))
    late=[r for r in rows if r['time_s']>=.5*c['stop_s']];speeds=[float(np.polyfit([r['time_s'] for r in late],[r['shock_locations_m'][j] for r in late],1)[0]) if len(late)>1 and all(r['shock_locations_m'][j] is not None for r in late) else None for j in range(3)]
    log=next(path.glob('log.*.mpirun'),next(path.glob('log.*.detonationFoam_V2.0'),None)).read_text();audits=re.findall(r'SPECIES_AUDIT time=(\S+) preClipMin=(\S+) clippedMass=(\S+) inertMin=(\S+)',log)
    left_margin=c['shock_initial_m']-(maxchar-cj['CJ_speed_mps'])*c['stop_s']-2e-4
    right_margin=c['length_m']-c['shock_initial_m']-(maxchar+cj['CJ_speed_mps'])*c['stop_s']-8*c['dx_m']
    checks=dict(finite=bool(finite),positive_pressure=all(r['p_min_Pa']>0 for r in rows),thermo_range=all(200<=r['T_min_K'] and r['T_max_K']<=5000 for r in rows),boundary_cone_margin=min(left_margin,right_margin)>0,completion='\nEnd\n' in log and abs(rows[-1]['time_s']-c['stop_s'])<1e-15,nonnegative=min_y>=0,species_sum=max_sum<1e-8,elements=max_element<1e-8,
        short_wave_speed=all(v is not None and abs(v/cj['CJ_speed_mps']-1)<.05 for v in speeds))
    expected=ref['ZND']['heat_fraction_lengths_m']['0.5'];distances=[r['half_heat_distance_m'] for r in late]
    checks.update(shock_reaction_coupling=all(d is not None and 0<d<2*expected for d in distances),reaction_distance_accuracy=all(d is not None and abs(d/expected-1)<.2 for d in distances))
    report=dict(checks=checks,boundary_cone_margin_m=left_margin,right_boundary_cone_margin_m=right_margin,max_observed_characteristic_mps=maxchar,history=rows,speed_mps=speeds,reference_speed_mps=cj['CJ_speed_mps'],reference_half_heat_m=ref['ZND']['heat_fraction_lengths_m']['0.5'],max_element_error=max_element,max_species_sum_error=max_sum,
        max_global_step_clipped_mass_kg=max((float(a[2]) for a in audits),default=None),minimum_preclip_species=min((float(a[1]) for a in audits),default=None),physical_validation_passed=False,
        scope='Short planar control only; no engine result or long-time mean CJ-speed claim.')
    (path/'wave_checks.json').write_text(json.dumps(report,indent=2));np.savez_compressed(path/'wave_profiles.npz',time_s=[r['time_s'] for r in rows],x_m=x,**{k:np.array([p[k] for p in profiles]) for k in profiles[0]})
    print(json.dumps({k:v for k,v in report.items() if k!='history'},indent=2));return report
if __name__=='__main__':analyze(sys.argv[1])
