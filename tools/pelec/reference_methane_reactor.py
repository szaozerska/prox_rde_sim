"""Prepare and independently verify a short GRI postshock closed-reactor control."""
import argparse
import hashlib
import json
from pathlib import Path
import cantera as ct
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cj',type=Path);parser.add_argument('mechanism',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    cj=json.loads(args.cj.read_text()); histories=[]
    times=np.linspace(0,5e-7,1001)
    for rtol,atol in ((1e-11,1e-22),(1e-12,1e-23)):
        gas=ct.Solution(str(args.mechanism));gas.TPY=cj['VN']['T'],cj['VN']['p'],cj['VN']['Y']
        energy0=gas.int_energy_mass; scale=max(abs(energy0),gas.cv_mass*gas.T)
        density=gas.density; elements=[gas.elemental_mass_fraction(e) for e in gas.element_names]
        reactor=ct.IdealGasReactor(gas,clone=True);net=ct.ReactorNet([reactor]);net.rtol=rtol;net.atol=atol
        net.max_time_step=2.5e-10
        rows=[];errors=dict(energy=0.,elements=0.,density=0.,species_sum=0.)
        for t in times:
            if t: net.advance(float(t))
            phase=reactor.phase
            rows.append([reactor.T,phase.P,*phase.Y.tolist()])
            errors['energy']=max(errors['energy'],abs(phase.int_energy_mass-energy0)/scale)
            errors['elements']=max(errors['elements'],max(abs(phase.elemental_mass_fraction(e)-v) for e,v in zip(gas.element_names,elements)))
            errors['density']=max(errors['density'],abs(phase.density/density-1))
            errors['species_sum']=max(errors['species_sum'],abs(float(sum(phase.Y))-1))
        histories.append(dict(rtol=rtol,atol=atol,errors=errors,rows=rows))
    a,b=[np.array(h['rows']) for h in histories]
    differences=dict(temperature_relative=float(max(abs(a[:,0]/b[:,0]-1))),
        pressure_relative=float(max(abs(a[:,1]/b[:,1]-1))),species_absolute=float(np.max(abs(a[:,2:]-b[:,2:]))))
    checks=dict(reference_refinement=max(differences.values())<1e-6,
        energy=max(h['errors']['energy'] for h in histories)<1e-8,
        elements=max(h['errors']['elements'] for h in histories)<1e-9,
        density=max(h['errors']['density'] for h in histories)<1e-12,
        species_sum=max(h['errors']['species_sum'] for h in histories)<1e-11,
        positive_species=float(min(a[:,2:].min(),b[:,2:].min()))>-1e-12,
        within_declared_polynomial_interval=bool(np.min(b[:,0])>=300 and np.max(b[:,0])<=5000),
        finite=bool(np.isfinite(a).all() and np.isfinite(b).all()),
        reaction_occurs=bool(b[-1,0]>b[0,0]+100))
    report=dict(checks=checks,passed=all(checks.values()),differences=differences,
        max_temperature_K=float(max(b[:,0])),reference_errors=[h['errors'] for h in histories],
        scope='Numerical closed-reactor law control, including explicit outside-fit polynomial extrapolation; not physical validation')
    (args.output/'reference_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez_compressed(args.output/'reference_histories.npz',time_s=times,baseline=a,strict=b)
    config=dict(temperature_K=cj['VN']['T'],pressure_Pa=cj['VN']['p'],Y=cj['VN']['Y'],
        species=gas.species_names,species_count=gas.n_species,final_time_s=float(times[-1]),
        independent_reference_checked=report['passed'],reference_rtol=1e-12,reference_atol=1e-23,
        mechanism_sha256=hashlib.sha256(args.mechanism.read_bytes()).hexdigest(),
        reference_state='Frozen postshock Run937 model state; homogeneous constant volume, no flow',
        thermo_fit_validity='Unresolved above source fit limits; no engine claim')
    (args.output/'reactor_case.json').write_text(json.dumps(config,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
