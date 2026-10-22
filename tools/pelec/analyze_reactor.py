"""Independent native closed-reactor checks, including a no-op chemistry guard."""
import argparse
import json
from pathlib import Path
import cantera as ct
import numpy as np
from validation import native_log_errors


def analyze(run,mechanism,native_constants=False):
    def make_phase():
        if native_constants:
            from native_lidryer_reference import make_reference
            return make_reference(mechanism)
        return ct.Solution(str(mechanism)),{'kind':'nominal_yaml'}
    import yt
    yt.set_log_level(40)
    status=json.loads((run/'result.json').read_text())
    phase,reference_metadata=make_phase()
    phase.TPY=1001.,101325.,{'H2':.06,'O2':.5,'N2':.44}
    reference=ct.IdealGasReactor(phase,energy='on',clone=True)
    network=ct.ReactorNet([reference]);network.rtol=1e-11;network.atol=1e-20
    u0=phase.int_energy_mass;scale=max(abs(u0),phase.cv_mass*phase.T)
    initial_elements=np.array([phase.elemental_mass_fraction(e) for e in phase.element_names])
    # Cheap native reductions cover every step; full fields cover endpoints,
    # regular checkpoints and the fastest heating interval.
    history=np.genfromtxt(run/'datlog',names=True)
    if len(history)<2 or not np.isfinite(history.tolist()).all():
        raise ValueError('Missing/nonfinite native history')
    history_gas,_=make_phase()
    history_gas.TPY=1001.,101325.,{'H2':.06,'O2':.5,'N2':.44}
    history_reactor=ct.IdealGasReactor(history_gas,energy='on',clone=True)
    history_net=ct.ReactorNet([history_reactor]);history_net.rtol=1e-11;history_net.atol=1e-20
    history_temperature_errors=[]
    for t,temperature in zip(history['time'],history['temp']):
        if t>0: history_net.advance(float(t))
        history_temperature_errors.append(abs(float(temperature)/history_reactor.T-1))
    plots=sorted(run.glob('plt[0-9]*'))
    times=[]
    for plot in plots:
        header=(plot/'Header').read_text().splitlines()
        times.append(float(header[3+int(header[1])]))
    peak=int(np.argmax(np.diff(history['temp'])/np.diff(history['time'])))
    peak_time=float(history['time'][peak])
    peak_plot=int(np.argmin(abs(np.array(times)-peak_time)))
    chosen=set(np.linspace(0,len(plots)-1,11,dtype=int))
    chosen.update(range(max(0,peak_plot-2),min(len(plots),peak_plot+4)))
    rows=[];energy0=None;rho0=None
    for index in sorted(chosen):
        plot=plots[index]
        ds=yt.load(str(plot));t=float(ds.current_time)
        if not np.isclose(float(np.prod(ds.domain_width)),1.,rtol=0,atol=1e-14):
            raise ValueError('This upstream reactor history assumes a 1 cm3 box')
        if ds.index.max_level!=0: raise ValueError('Expected uniform zeroD control')
        ad=ds.all_data()
        names=['density','Temp','pressure','rho_E']+['Y('+s+')' for s in phase.species_names]
        fields={name:np.asarray(ad['boxlib',name]) for name in names}
        if not all(np.isfinite(v).all() for v in fields.values()):
            raise ValueError('Nonfinite native reactor field')
        vals={name:float(v.mean()) for name,v in fields.items()}
        nonuniform=max(float(np.ptp(v))/max(float(np.max(abs(v))),1e-30) for v in fields.values())
        y=np.array([vals['Y('+s+')'] for s in phase.species_names])
        T=vals['Temp'];rho=vals['density']*1000.;pressure=vals['pressure']*.1
        if t>0: network.advance(t)
        truth=reference.phase
        phase.TDY=T,rho,y
        elems=np.array([phase.elemental_mass_fraction(e) for e in phase.element_names])
        energy=vals['rho_E']*.1  # erg/cm3 -> J/m3
        if energy0 is None: energy0=energy;rho0=rho
        rows.append({'time':t,'temperature_K':T,'pressure_Pa':pressure,'Y':y.tolist(),
                     'reference_temperature_K':truth.T,
                     'temperature_relative_error':abs(T/truth.T-1),
                     'pressure_relative_error':abs(pressure/truth.P-1),
                     'species_max_absolute_error':float(np.max(abs(y-truth.Y))),
                     'max_element_error':float(np.max(abs(elems-initial_elements))),
                     'relative_native_energy_error':abs(energy-energy0)/max(abs(energy0),rho0*scale),
                     'relative_thermo_energy_error':abs(phase.int_energy_mass-u0)/scale,
                     'relative_density_error':abs(rho-rho0)/rho0,
                     'mass_fraction_sum_error':abs(float(y.sum())-1),
                     'minimum_mass_fraction':float(y.min()),'relative_nonuniformity':nonuniform})
    if len(rows)<2: raise ValueError('Initial and final reactor fields required')
    metric_names=[k for k in rows[0] if k.endswith('error') or k=='relative_nonuniformity']
    maxima={k:max(row[k] for row in rows) for k in metric_names}
    log=(run/'solver.log').read_text()
    checks={'no_solver_errors':not native_log_errors(log),
            'all_step_temperature_reference':max(history_temperature_errors)<2e-5,
            'all_step_mass_budget':float(np.max(abs(history['mass']/history['mass'][0]-1)))<1e-12,
            'all_step_energy_budget':float(np.max(abs(history['rho_E']/history['rho_E'][0]-1)))<1e-10,
            'completed':bool(status['completion_passed']),
            'initial_and_final_time':abs(rows[0]['time'])<1e-14 and abs(rows[-1]['time']-.001)<1e-13,
            'active_cvode':'Initializing CVODE:' in log and 'WARNING: turning on reactions while using ReactorNull' not in log,
            'temperature_changes':rows[-1]['temperature_K']>rows[0]['temperature_K']+100.,
            'positive_temperature_pressure':all(r['temperature_K']>0 and r['pressure_Pa']>0 for r in rows),
            'reference_temperature':maxima['temperature_relative_error']<2e-5,
            'reference_pressure':maxima['pressure_relative_error']<2e-5,
            'reference_species':maxima['species_max_absolute_error']<2e-6,
            'native_energy':maxima['relative_native_energy_error']<1e-10,
            'thermo_energy':maxima['relative_thermo_energy_error']<1e-8,
            'elements':maxima['max_element_error']<1e-9,
            'density':maxima['relative_density_error']<1e-12,
            'species_sum':maxima['mass_fraction_sum_error']<1e-11,
            'species_nonnegative':min(r['minimum_mass_fraction'] for r in rows)>-1e-12,
            'uniformity':maxima['relative_nonuniformity']<1e-8}
    return {'passed':all(checks.values()),'reference':reference_metadata,'checks':checks,'maxima':maxima,
            'species':phase.species_names,'records':rows,
            'history_samples':len(history),'max_history_temperature_relative_error':max(history_temperature_errors),
            'field_samples':len(chosen),'available_field_samples':len(plots),
            'sampling_scope':'All-step native mass/energy/temperature reductions; full-cell fields at endpoints, 11 regular samples and heating-peak neighbors',
            'scope':'LiDryer closed-reactor numerical control at explicitly declared 1001 K; methane/engine validation pending'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('mechanism',type=Path)
    parser.add_argument('--native-constants',action='store_true',help='Separate diagnostic; does not replace nominal YAML checks')
    args=parser.parse_args();report=analyze(args.run,args.mechanism,args.native_constants)
    (args.run/('reactor_checks_native_constants.json' if args.native_constants else 'reactor_checks.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
    raise SystemExit(0 if report['passed'] else 1)
