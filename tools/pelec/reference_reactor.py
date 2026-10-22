"""Independent constant-volume Cantera control for the upstream LiDryer zeroD case."""
import argparse
import hashlib
import json
from pathlib import Path
import cantera as ct
import numpy as np


def solve(mechanism, rtol, atol, temperature):
    gas=ct.Solution(str(mechanism))
    gas.TPY=temperature,101325.0,{'H2':.06,'O2':.5,'N2':.44}
    reactor=ct.IdealGasReactor(gas,energy='on',clone=True)
    net=ct.ReactorNet([reactor]);net.rtol=rtol;net.atol=atol
    phase=reactor.phase
    u0=phase.int_energy_mass
    scale=max(abs(u0),phase.cv_mass*phase.T)
    elems=np.array([phase.elemental_mass_fraction(e) for e in phase.element_names])
    density=phase.density
    records=[]
    for t in np.linspace(0,.001,101):
        if t>0: net.advance(float(t))
        current=np.array([phase.elemental_mass_fraction(e) for e in phase.element_names])
        records.append({'time_s':float(t),'temperature_K':phase.T,'pressure_Pa':phase.P,
                        'density_kg_m3':phase.density,'mass_fractions':phase.Y.tolist(),
                        'relative_energy_error':abs(phase.int_energy_mass-u0)/scale,
                        'max_element_error':float(np.max(abs(current-elems))),
                        'relative_density_error':abs(phase.density-density)/density})
    return records,gas.species_names,gas.element_names


def reference(mechanism, temperature=1001.):
    normal,species,elements=solve(mechanism,1e-10,1e-18,temperature)
    tight,_,_=solve(mechanism,1e-11,1e-20,temperature)
    terr=max(abs(a['temperature_K']/b['temperature_K']-1) for a,b in zip(normal,tight))
    yerr=max(float(np.max(abs(np.array(a['mass_fractions'])-b['mass_fractions']))) for a,b in zip(normal,tight))
    metrics={key:max(row[key] for row in normal+tight) for key in
             ('relative_energy_error','max_element_error','relative_density_error')}
    checks={'energy':metrics['relative_energy_error']<1e-8,
            'elements':metrics['max_element_error']<5e-11,
            'density':metrics['relative_density_error']<1e-12,
            'tolerance_temperature':terr<1e-6,'tolerance_species':yerr<1e-7,
            'finite_states':all(np.isfinite(row['temperature_K']) and row['temperature_K']>0
                                and np.isfinite(row['mass_fractions']).all()
                                for row in normal+tight)}
    return {'passed':all(checks.values()),'checks':checks,'metrics':metrics,
            'tolerance_temperature_relative':terr,'tolerance_species_absolute':yerr,
            'mechanism_sha256':hashlib.sha256(mechanism.read_bytes()).hexdigest(),
            'cantera_version':ct.__version__,'species':species,'elements':elements,
            'input':{'temperature_K':temperature,'pressure_Pa':101325.,
                     'mass_fractions':{'H2':.06,'O2':.5,'N2':.44}},
            'scope':'Independent upstream hydrogen reactor control; not CH4/O2 validation',
            'records':tight}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mechanism',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--temperature',type=float,default=1001.)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    report=reference(args.mechanism,args.temperature)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
    raise SystemExit(0 if report['passed'] else 1)
