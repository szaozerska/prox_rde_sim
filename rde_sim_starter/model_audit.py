"""Saved-reference algebra for C5; never changes calibration or advances CFD.

Two matched distances are calibration constraints, not physical validation.
The third heat-fraction distance is held out. Source step counts describe the
current sufficient global cap, not an intrinsic chemical timescale or benchmark.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq

from calibrate import dx_dxi
from physics import source_step_limit


def reaction_scale_audit(calibration, reference, quadrature_rtol=1e-10):
    c=copy.deepcopy(calibration)
    keys=('0.5','0.9','0.95')
    physical=np.array([reference['znd']['heat_fraction_lengths_m'][key] for key in keys])
    if not np.all(np.isfinite(physical)) or not np.all(physical>0) or not np.all(np.diff(physical)>0):
        raise ValueError('positive ordered physical heat-fraction distances required')
    def lengths(gas,k):
        return np.array([quad(dx_dxi,0,float(key),args=(k,gas),epsabs=0,epsrel=quadrature_rtol,limit=200)[0] for key in keys])
    current=lengths(c,c['k'])
    target=physical[2]/physical[0]
    def shape(e):
        gas=copy.deepcopy(c);gas['Ea']=e*c['R']*c['T1'];values=lengths(gas,1.)
        return gas,values
    # Bounded algebraic solve only; fail explicitly if this family cannot fit it.
    activation=brentq(lambda e:shape(e)[1][2]/shape(e)[1][0]-target,0.,200.,xtol=1e-10)
    fit,unit=shape(activation);fit['k']=unit[0]/physical[0]
    fitted=lengths(fit,fit['k'])
    if np.max(abs(fitted[[0,2]]/physical[[0,2]]-1))>1e-8:
        raise RuntimeError('two-distance calibration residual exceeded')
    dt=source_step_limit(fit['gamma'],fit['q'],fit['R'],fit['k'],fit['Ea'],.05)
    base_dt=source_step_limit(c['gamma'],c['q'],c['R'],c['k'],c['Ea'],.05)
    return dict(
        policy='Algebraic feasibility only; candidate NOT adopted; production calibration unchanged.',
        quadrature_rtol=quadrature_rtol,heat_fractions=list(map(float,keys)),
        physical_length_m=physical.tolist(),current_length_m=current.tolist(),
        stretch_factors=(current/physical).tolist(),
        physical_cells_at_current_0_5mm=(physical/.0005).tolist(),
        rate_only_match_half=dict(k_multiplier=float(current[0]/physical[0]),predicted_length_m=(current/current[0]*physical[0]).tolist()),
        rate_only_match_95=dict(k_multiplier=float(current[2]/physical[2]),predicted_length_m=(current/current[2]*physical[2]).tolist()),
        two_distance_candidate_not_adopted=dict(Ea_over_RT1=float(activation),k_per_s=float(fit['k']),
            predicted_length_m=fitted.tolist(),held_out_90_relative_error=float(fitted[1]/physical[1]-1),
            source_cfl=.05,global_source_cap_s=float(dt),
            steps_for_three_reference_intervals_lower_bound=float((3/15840)/dt),
            source_step_work_multiplier=float(base_dt/dt)),
        thermodynamics_unchanged=dict(CJ_speed_mps=c['D_CJ'],CJ_temperature_K=c['CJ']['T'],
            physical_CJ_speed_mps=reference['nominal']['CJ_speed_mps'],physical_CJ_temperature_K=reference['nominal']['CJ']['T']),
        interpretation='Matching 50% and 95% distances leaves a held-out 90% error and unchanged thermodynamic mismatch. Resolve the source/mesh/reference gate before engine use; no steady-wave prediction follows.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,required=True,help='saved d3_metrics.json with reference and calibration')
    p.add_argument('--out',type=Path,required=True,help='new JSON output')
    args=p.parse_args(argv)
    evidence=json.loads(args.evidence.read_text());c=evidence['reference_inputs']['calibration'];reference=evidence['reference']
    result=reaction_scale_audit(c,reference)
    strict=reaction_scale_audit(c,reference,quadrature_rtol=1e-12)
    a=result['two_distance_candidate_not_adopted'];b=strict['two_distance_candidate_not_adopted']
    result['strict_quadrature_relative_changes']={key:float(b[key]/a[key]-1) for key in ('Ea_over_RT1','k_per_s','global_source_cap_s')}
    if max(abs(v) for v in result['strict_quadrature_relative_changes'].values())>1e-8:
        raise RuntimeError('quadrature sensitivity exceeds audit tolerance')
    result['provenance']=dict(evidence_sha256=hashlib.sha256(args.evidence.read_bytes()).hexdigest(),
        source_sha256={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('model_audit.py','calibrate.py','physics.py')})
    with args.out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(args.out)


if __name__=='__main__':main()
