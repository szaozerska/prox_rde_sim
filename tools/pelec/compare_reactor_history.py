"""Fast all-step ignition check before expensive full-field analysis."""
import argparse
import json
from pathlib import Path
import cantera as ct
import numpy as np
from native_generated_reference import make_reference


def compare(run, mechanism, native_constants=False):
    history=np.genfromtxt(run/'datlog',names=True)
    if len(history)<2 or not np.isfinite(history.tolist()).all():
        raise ValueError('Missing/nonfinite native reactor history')
    if native_constants:
        gas,metadata=make_reference(mechanism)
    else:
        gas=ct.Solution(str(mechanism));metadata={'kind':'nominal_yaml'}
    case_path=run/'reactor_case.json'
    case=json.loads(case_path.read_text()) if case_path.exists() else {}
    gas.TPY=case.get('temperature_K',1001.),case.get('pressure_Pa',101325.),case.get('Y',{'H2':.06,'O2':.5,'N2':.44})
    reactor=ct.IdealGasReactor(gas,energy='on',clone=True)
    network=ct.ReactorNet([reactor]);network.rtol=case.get('reference_rtol',1e-12);network.atol=case.get('reference_atol',1e-22)
    truth=[]
    for t in history['time']:
        if t>0: network.advance(float(t))
        truth.append(reactor.T)
    errors=abs(history['temp']/np.array(truth)-1)
    index=int(np.argmax(errors))
    return {'run':str(run),'reference':metadata,'samples':len(history),
            'final_time':float(history['time'][-1]),
            'max_temperature_relative_error':float(errors[index]),
            'time_of_max_error':float(history['time'][index]),
            'temperature_comparison_passed':bool(max(errors)<2e-5),
            'criteria':'Maximum all-step temperature relative error <2e-5. This diagnostic alone is not a chemistry gate pass.',
            'time_s':history['time'].tolist(),'native_temperature_K':history['temp'].tolist(),
            'reference_temperature_K':truth}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('mechanism',type=Path)
    parser.add_argument('--native-constants',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.run,args.mechanism,args.native_constants)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('time_s','native_temperature_K','reference_temperature_K')},indent=2))
    raise SystemExit(0 if result['temperature_comparison_passed'] else 1)
