"""Independent methane model screening; no solver launch or experimental claim."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'rde_sim_starter'))
from reference import _libraries, _cj, _znd


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def thermo_states(ct, path, pressure, temperatures):
    gas = ct.Solution(str(path))
    states = []
    for temperature in temperatures:
        for condition in ('fresh', 'TP_equilibrium'):
            gas.TPX = temperature, pressure, 'CH4:1.176,O2:2'
            if condition == 'TP_equilibrium':
                gas.equilibrate('TP')
            states.append(dict(temperature_K=float(gas.T), pressure_Pa=float(gas.P),
                condition=condition, Y=gas.Y.tolist(), reference_u_J_kg=gas.int_energy_mass,
                reference_cv_J_kg_K=gas.cv_mass,
                mass_fraction_outside_thermo_fit_range=float(sum(y for y, species in zip(gas.Y, gas.species())
                    if gas.T < species.thermo.min_temp - 1e-8 or gas.T > species.thermo.max_temp + 1e-8))))
    return dict(mechanism=path.parent.name, species=gas.species_names, reactions=gas.n_reactions,
        mechanism_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        native_inversion_upper_bound_K=5000. if path.parent.name == 'FFCM1_Red' else 3000., states=states)


def polynomial_cv_check(ct, path):
    """Check each NASA7 cv polynomial at extrema as well as endpoints, 300–5000 K.

    Positivity/monotonic energy are mathematical checks, not validation outside fits.
    """
    import numpy as np
    gas = ct.Solution(str(path))
    results = []
    for species in gas.species():
        c = species.thermo.coeffs
        if len(c) != 15:
            raise ValueError('This check is specifically for two-interval NASA7')
        candidates = []
        for lo, hi, coefficients in ((300., min(float(c[0]), 5000.), c[8:13]),
                                     (max(300., float(c[0])), 5000., c[1:6])):
            polynomial = np.polynomial.Polynomial(coefficients) - 1.
            points = [lo, hi] + [float(x.real) for x in polynomial.deriv().roots()
                if abs(x.imag) < 1e-8 and lo < x.real < hi]
            candidates += [(float(polynomial(x)), x) for x in points]
        minimum, temperature = min(candidates)
        results.append(dict(species=species.name, minimum_cv_over_R=minimum,
                            temperature_K=temperature, positive=minimum > 0))
    return dict(scope='Polynomial extrema only; fit validity is unchanged',
                temperature_interval_K=[300, 5000], all_positive=all(r['positive'] for r in results), species=results)


def ignition(ct, path, temperature, pressure, rtol, atol, max_step):
    started = time.monotonic()
    gas = ct.Solution(str(path)); gas.TPX = temperature, pressure, 'CH4:1.176,O2:2'
    reactor = ct.IdealGasReactor(gas, clone=True)
    net = ct.ReactorNet([reactor]); net.rtol = rtol; net.atol = atol
    net.max_time_step = max_step
    target = temperature + 400.; horizon = .002
    energy0 = reactor.phase.int_energy_mass
    energy_scale = max(abs(energy0), reactor.phase.cv_mass * temperature)
    density0 = reactor.density
    elements0 = [reactor.phase.elemental_mass_fraction(e) for e in gas.element_names]
    errors = dict(energy=0., density=0., elements=0., species_sum=0.)
    previous = (0., temperature); crossing = None; steps = 0
    while net.time < horizon and reactor.T < target:
        previous = (net.time, reactor.T)
        net.max_time_step = min(max_step, horizon-net.time)
        net.step(); steps += 1
        if steps > 100000:
            raise RuntimeError('Independent ignition reference exceeded step cap')
        phase = reactor.phase
        errors['energy'] = max(errors['energy'], abs(phase.int_energy_mass-energy0)/energy_scale)
        errors['density'] = max(errors['density'], abs(reactor.density/density0-1))
        errors['elements'] = max(errors['elements'], max(abs(phase.elemental_mass_fraction(e)-v)
            for e,v in zip(gas.element_names,elements0)))
        errors['species_sum'] = max(errors['species_sum'], abs(float(sum(phase.Y))-1))
        if reactor.T >= target:
            crossing = previous[0] + (target-previous[1])*(net.time-previous[0])/(reactor.T-previous[1])
    return dict(mechanism=path.parent.name, initial_temperature_K=temperature, pressure_Pa=pressure,
        target_temperature_K=target, time_to_400K_rise_s=crossing,
        event_bracket_s=[previous[0], net.time], event_bracket_temperature_K=[previous[1], reactor.T],
        requested_horizon_s=horizon, rtol=rtol, atol=atol, max_step_s=max_step,
        steps=steps, invariant_errors=errors, wall_seconds=time.monotonic()-started,
        scope='Independent homogeneous constant-volume mechanism sensitivity; not experimental ignition/extinction')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--znd', action='store_true', help='Also compute baseline/strict ZND for each candidate')
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    ct, post, znd, thermo, manifest = _libraries()
    mechanisms = ROOT / '.tooling/PeleC/Submodules/PelePhysics/Mechanisms'
    paths = {name: mechanisms/name/'mechanism.yaml' for name in ('grimech30','FFCM1_Red','drm19')}
    pressure=377916.97229176015
    save(args.output/'provenance.json', dict(cantera=ct.__version__, sdtoolbox=manifest,
        mechanism_sha256={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in paths.items()},
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        pressure_basis='Run 937 Eq.4.1 inferred prefill pressure, distinct from 1-atm sensitivity',
        phi=1.176, temperature_K=300.))
    references = {}
    for name in ('grimech30','FFCM1_Red'):
        path=paths[name]
        reference, initial, work, hf = _cj(ct,post,thermo,pressure,300.,1.176,mechanism=str(path))
        references[name]=reference;save(args.output/f'{name}_cj.json',reference)
        print(name,'CJ',reference['CJ_speed_mps'],flush=True)
        if args.znd:
            import numpy as np
            for label, tolerances in [('baseline',(1e-7,1e-11,2e-9)),('strict',(2e-8,2e-12,1e-9))]:
                # ZNDSys mutates its Cantera phase; each refinement starts at VN.
                work.TDY = reference['VN']['T'], reference['VN']['rho'], reference['VN']['Y']
                summary, profile = _znd(ct,znd,thermo,reference,initial,work,hf,*tolerances)
                save(args.output/f'{name}_znd_{label}.json', summary)
                np.savez_compressed(args.output/f'{name}_znd_{label}.npz', **profile)
        save(args.output/f'{name}_polynomial_cv.json', polynomial_cv_check(ct,path))
    one_atm,*_=_cj(ct,post,thermo,101325.,300.,1.176,mechanism=str(paths['grimech30']))
    save(args.output/'grimech30_one_atm_cj.json',one_atm)
    cj=references['grimech30']
    states=[thermo_states(ct,path,cj['CJ']['p'],(300.,1001.,1800.,3000.,3500.,cj['CJ']['T'],4500.,5000.))
            for path in paths.values()]
    save(args.output/'thermo_states.json',states)
    rows=[]
    for temperature in (1001.,1500.,cj['VN']['T']):
        for p in (pressure,cj['VN']['p']):
            for name in ('grimech30','FFCM1_Red'):
                for rtol,atol,dt in ((1e-10,1e-20,2e-6),(1e-11,1e-22,1e-6)):
                    rows.append(ignition(ct,paths[name],temperature,p,rtol,atol,dt))
                    print(name,temperature,p,rtol,rows[-1]['time_to_400K_rise_s'],flush=True)
    save(args.output/'ignition_screen.json',rows)


if __name__=='__main__':
    main()
