"""Integrate the independent steady profile farther; never extrapolate its tail."""
import argparse,json,sys,shutil
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'rde_sim_starter'))
from reference import _libraries,_znd

def extend(source,out,end=8e-6):
    source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    ct,post,znd,thermo,manifest=_libraries();r=json.loads((source/'reference.json').read_text());ref=r['CJ']
    shutil.copyfile(source/'native_constants.yaml',out/'native_constants.yaml');native=str((out/'native_constants.yaml').resolve())
    initial=ct.Solution(native);initial.TPY=ref['temperature_K'],ref['pressure_Pa'],ref['initial']['Y']
    working=ct.Solution(native);working.TP=298.15,ct.one_atm;hf=working.standard_enthalpies_RT*ct.gas_constant*working.T/working.molecular_weights
    working.TDY=ref['VN']['T'],ref['VN']['rho'],ref['VN']['Y']
    coarse,_=_znd(ct,znd,thermo,ref,initial,working,hf,1e-7,1e-11,4e-9,end=end)
    working.TDY=ref['VN']['T'],ref['VN']['rho'],ref['VN']['Y']
    strict,profile=_znd(ct,znd,thermo,ref,initial,working,hf,2e-8,1e-14,2e-9,end=end)
    differences={key:abs(strict[key]/coarse[key]-1) for key in ('induction_time_max_dTdt_s','distance_at_max_dTdt_m')}
    differences['half_heat_length_relative']=abs(strict['heat_fraction_lengths_m']['0.5']/coarse['heat_fraction_lengths_m']['0.5']-1)
    if max(differences.values())>.005:raise ValueError('Reference refinement fails')
    r.update(ZND=strict,coarse_ZND=coarse,refinement=differences,sdtoolbox=manifest,extension_note='Independent ZND integration extended in time; no constant-tail extrapolation.')
    (out/'reference.json').write_text(json.dumps(r,indent=2));np.savez_compressed(out/'znd.npz',**profile)
    print('Independent reference extends to',profile['distance_m'][-1],'m',strict,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--end',type=float,default=8e-6);a=p.parse_args();extend(**vars(a))
