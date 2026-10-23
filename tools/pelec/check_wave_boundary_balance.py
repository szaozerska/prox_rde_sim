"""Independent snapshot boundary-flux balance for a first-order planar control.

This is not an exported solver flux ledger: temporal quadrature is checked and
reported. It cannot certify EB corrections or replace production boundary budgets.
"""
import argparse,json
from pathlib import Path
import numpy as np
import cantera as ct

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('reference',type=Path);a=p.parse_args()
    run=json.loads((a.run/'result.json').read_text());case=json.loads((a.run/'case.json').read_text());report=json.loads((a.run/'wave_checks.json').read_text())
    if run.get('reconstruction_order')!=1:raise ValueError('Boundary-cell flux interpretation restricted to first-order extrapolation control')
    data=np.load(a.run/'wave_profiles.npz');gas=ct.Solution(str(a.reference/'native_constants.yaml'));flux=[]
    for i in range(len(data['time_s'])):
        endpoints=[]
        for j in (0,-1):
            rho=data['density_kg_m3'][i,j];u=data['velocity_mps'][i,j]
            gas.TDY=data['temperature_K'][i,j],rho,data['species_Y'][i,j]
            endpoints.append(np.array([rho*u,rho*u*(gas.enthalpy_mass+.5*u*u)]))
        flux.append(endpoints[0]-endpoints[1])
    time=data['time_s'];flux=np.array(flux)
    if len(time)<5 or (len(time)-1)%2:raise ValueError('Need matching whole-interval snapshot quadratures')
    baseline=np.trapezoid(flux,time,axis=0);coarse=np.trapezoid(flux[::2],time[::2],axis=0)
    keys=['mass_per_area_kg_m2','total_energy_per_area_J_m2']
    actual=np.array([report['history'][-1][k]-report['history'][0][k] for k in keys]);scale=np.array([abs(report['history'][0][k]) for k in keys])
    if np.any(scale<1e-10):raise ValueError('Degenerate budget normalization')
    result=dict(native_integral_change=dict(zip(keys,map(float,actual))),snapshot_boundary_integral=dict(zip(keys,map(float,baseline))),
        relative_residual=dict(zip(keys,map(float,abs(actual-baseline)/scale))),
        temporal_quadrature_difference=dict(zip(keys,map(float,abs(coarse-baseline)/scale))),
        scope='Independent boundary-cell flux/snapshot quadrature diagnostic for this first-order planar case. Not an exact native flux ledger, EB repair budget, or gate waiver.')
    (a.run/'boundary_balance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
