"""Compare saved native thermo operators with independent Cantera states."""
import argparse
import json
import math
from pathlib import Path


def analyze(evidence):
    summaries=[]
    for case in evidence['cases']:
        if len(case['states'])!=len(case['values_cgs']):
            raise ValueError('Incomplete native operator records')
        rows=[]
        for state,value in zip(case['states'],case['values_cgs']):
            if len(value) not in (5,10) or not all(math.isfinite(x) for x in value):
                raise ValueError('Invalid native thermodynamic output')
            u,cv,T,ur,status=value[:5]
            rows.append({'T_input':state['temperature_K'],'condition':state['condition'],
                'native_temperature_error_K':T-state['temperature_K'],
                'native_cv_positive':cv>0,'native_inversion_status':int(status),
                'native_energy_round_trip_relative_error':abs(ur-u)/max(abs(u),cv*state['temperature_K']),
                'forward_energy_relative_error':abs(u*1e-4-state['reference_u_J_kg'])/max(abs(state['reference_u_J_kg']),state['reference_cv_J_kg_K']*state['temperature_K']),
                'forward_cv_relative_error':abs(cv*1e-4/state['reference_cv_J_kg_K']-1),
                'mass_fraction_outside_thermo_fit_range':state['mass_fraction_outside_thermo_fit_range']})
            if len(value)==10:
                h,cp,ht,hr,hs=value[5:]
                rows[-1].update(enthalpy_temperature_error_K=ht-state['temperature_K'],
                    enthalpy_round_trip_relative_error=abs(hr-h)/max(abs(h),cp*state['temperature_K']),
                    enthalpy_inversion_status=int(hs),native_cp_positive=cp>0)
        checks={'temperature_round_trip':all(abs(x['native_temperature_error_K'])<1e-5 for x in rows),
                'energy_round_trip':all(x['native_energy_round_trip_relative_error']<1e-8 for x in rows),
                'forward_energy':all(x['forward_energy_relative_error']<1e-10 for x in rows),
                'forward_cv':all(x['forward_cv_relative_error']<1e-10 for x in rows),
                'positive_cv':all(x['native_cv_positive'] for x in rows),
                'no_native_extrapolation':all(x['native_inversion_status']==0 for x in rows),
                'inside_thermo_fits':all(x['mass_fraction_outside_thermo_fit_range']<1e-12 for x in rows)}
        if all('enthalpy_temperature_error_K' in x for x in rows):
            checks.update(enthalpy_temperature_round_trip=all(abs(x['enthalpy_temperature_error_K'])<1e-5 for x in rows),
                enthalpy_round_trip=all(x['enthalpy_round_trip_relative_error']<1e-8 for x in rows),
                enthalpy_no_native_extrapolation=all(x['enthalpy_inversion_status']==0 for x in rows),
                positive_cp=all(x['native_cp_positive'] for x in rows))
        summaries.append({'mechanism':case['mechanism'],'species_count':len(case['species']),
                          'reactions':case['reactions'],'inversion_upper_bound_K':case['native_inversion_upper_bound_K'],
                          'effective_inversion_upper_bound_K':case.get('effective_inversion_upper_bound_K',case['native_inversion_upper_bound_K']),
                          'diagnostic_patch':case.get('diagnostic_patch'),
                          'numerical_consistency_passed':all(v for k,v in checks.items() if k!='inside_thermo_fits'),
                          'operator_preflight_passed':all(checks.values()),'checks':checks,'rows':rows})
    return {'scope':'Native thermodynamic operator screen only; no kinetics, CFD or experimental acceptance',
            'initial_temperature_guess_K':evidence['initial_temperature_guess_K'],
            'criteria':'Inverse temperature <1e-5 K; energy round trip <1e-8; forward u/cv <1e-10; positive cv; no extrapolation/fit-range violation',
            'cases':summaries}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();report=analyze(json.loads(args.evidence.read_text()))
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in c.items() if k!='rows'} for c in report['cases']],indent=2))
