"""Physical Run 937 references using optional Cantera and pinned SDToolbox.

Uses bounded minimization of SDToolbox CJ_calc and a checked solve_ivp driver
around its unmodified ZNDSys. CEA heat release is independently cross-checked
with GRI-Mech CJ-equilibrium products and 298.15 K formation enthalpies.
No CFD inputs are modified. Imports do not load Cantera, solve, or render.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import warnings
import platform
from importlib.metadata import version
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

HERE=Path(__file__).resolve().parent


def _write(path,data):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def _libraries():
    try:
        import cantera as ct
    except ImportError as error:
        raise RuntimeError('Physical reference needs requirements-reference.txt; the CFD environment can remain unchanged.') from error
    vendor=HERE/'vendor'; expected=vendor/'sdtoolbox'
    manifest=json.loads((vendor/'sdtoolbox_provenance.json').read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256((expected/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError(f'vendored SDToolbox changed: {name}')
    sys.path.insert(0,str(vendor))
    try:
        package=importlib.import_module('sdtoolbox')
        if Path(package.__file__).resolve().parent!=expected.resolve():
            raise RuntimeError('another sdtoolbox is already imported; use a fresh interpreter')
        post=importlib.import_module('sdtoolbox.postshock')
        znd=importlib.import_module('sdtoolbox.znd')
        thermo=importlib.import_module('sdtoolbox.thermo')
    finally:
        sys.path.remove(str(vendor))
    return ct,post,znd,thermo,manifest


def jump_residuals(upstream,downstream,speed):
    """Relative mass, momentum and total-enthalpy flux residuals in shock frame."""
    r1,r2=upstream['rho'],downstream['rho'];u2=speed*r1/r2
    momentum1=upstream['p']+r1*speed**2;momentum2=downstream['p']+r2*u2**2
    energy1=upstream['h']+.5*speed**2;energy2=downstream['h']+.5*u2**2
    return dict(mass=(r2*u2-r1*speed)/(r1*speed),momentum=(momentum2-momentum1)/momentum1,
                energy=(energy2-energy1)/max(abs(energy1),speed**2))


def _state(gas):
    return dict(T=float(gas.T),p=float(gas.P),rho=float(gas.density),h=float(gas.enthalpy_mass),
                gamma_frozen=float(gas.cp_mass/gas.cv_mass),MW=float(gas.mean_molecular_weight),
                Y=gas.Y.tolist())


def _cj(ct,post,thermo,pressure,temperature,phi,tolerance=1e-8,minimum_tolerance=1e-7,mechanism="gri30.yaml"):
    if not np.isfinite([pressure,temperature,phi]).all() or min(pressure,temperature,phi)<=0:
        raise ValueError('positive finite pressure, temperature and equivalence ratio required')
    composition={'CH4':float(phi),'O2':2.}
    initial=ct.Solution(mechanism,transport_model=None);initial.TPX=temperature,pressure,composition
    work=ct.Solution(mechanism,transport_model=None)
    def evaluate(ratio):
        work.TPX=temperature,pressure,composition
        result=post.CJ_calc(work,initial,tolerance,tolerance,ratio)
        if result is None or not np.isfinite(result[1]) or result[1]<=0:
            raise RuntimeError('SDToolbox CJ_calc did not converge')
        return float(result[1])
    bounds=(1.3,2.5)
    result=minimize_scalar(evaluate,bounds=bounds,method='bounded',
                           options={'xatol':minimum_tolerance,'maxiter':60})
    if not result.success or min(result.x-bounds[0],bounds[1]-result.x)<.01:
        raise RuntimeError('CJ speed minimum was not found inside the documented density-ratio bracket')
    speed=evaluate(result.x);cj=_state(work)
    residuals=jump_residuals(_state(initial),cj,speed)
    if max(abs(v) for v in residuals.values())>1e-6:
        raise RuntimeError(f'CJ jump residuals exceed tolerance: {residuals}')
    elements_initial=np.array([initial.elemental_mass_fraction(e) for e in initial.element_names])
    elements_cj=np.array([work.elemental_mass_fraction(e) for e in work.element_names])
    element_error=float(np.max(np.abs(elements_initial-elements_cj)))
    equilibrium_sound=float(thermo.soundspeed_eq(work))
    sonic_ratio=speed*initial.density/cj['rho']/equilibrium_sound
    if element_error>1e-8 or abs(sonic_ratio-1)>5e-3:
        raise RuntimeError('CJ element conservation or equilibrium sonic check failed')
    species_Y=np.array(cj['Y'])
    work.TP=298.15,ct.one_atm
    formation_enthalpies=work.standard_enthalpies_RT*ct.gas_constant*work.T/work.molecular_weights
    q=float(np.dot(initial.Y-species_Y,formation_enthalpies))
    if q<=0: raise RuntimeError('expected positive CJ equilibrium heat release')
    work.TPX=temperature,pressure,composition
    frozen=post.shk_calc(speed,work,initial,tolerance,tolerance)
    vn=_state(frozen);vn['u_shock_frame']=speed*initial.density/vn['rho']
    vn_residuals=jump_residuals(_state(initial),vn,speed)
    if max(abs(v) for v in vn_residuals.values())>1e-6:
        raise RuntimeError(f'frozen shock residuals exceed tolerance: {vn_residuals}')
    return dict(pressure_Pa=pressure,temperature_K=temperature,phi=phi,CJ_speed_mps=speed,
                CJ=cj,VN=vn,q_equilibrium_Jkg=q,initial=_state(initial),
                density_ratio=float(result.x),jump_relative_residuals=residuals,
                frozen_jump_relative_residuals=vn_residuals,CJ_equilibrium_sonic_ratio=float(sonic_ratio),
                element_mass_fraction_error=element_error,minimum_evaluations=int(result.nfev),
                tolerance=tolerance,minimum_tolerance=minimum_tolerance),initial,frozen,formation_enthalpies


def sampled_crossing(time,values,target):
    """First upward crossing; None when a target is not reached, no extrapolation."""
    time=np.asarray(time);values=np.asarray(values)
    if time.ndim!=1 or values.shape!=time.shape or len(time)<2 or not np.isfinite(time).all() or not np.isfinite(values).all() or np.any(np.diff(time)<=0):
        raise ValueError('finite matching increasing samples required')
    if not np.isfinite(target): raise ValueError('finite target required')
    if values[0]>=target: return float(time[0])
    indices=np.flatnonzero((values[:-1]<target)&(values[1:]>=target))
    if not indices.size:return None
    i=indices[0]
    return float(time[i]+(target-values[i])*(time[i+1]-time[i])/(values[i+1]-values[i]))


def _znd(ct,znd,thermo,reference,initial,working,hf,rtol,atol,max_step,end=2e-6):
    speed=reference['CJ_speed_mps'];rho1=initial.density
    y0=np.r_[working.P,working.density,0.,working.Y]
    system=znd.ZNDSys(working,speed,rho1)
    def sonic_event(t,y):
        working.DPY=y[1],y[0],y[3:]
        return .995-speed*rho1/working.density/thermo.soundspeed_fr(working)
    sonic_event.terminal=True;sonic_event.direction=-1
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter('always')
        solution=solve_ivp(system,(0.,end),y0,method='BDF',rtol=rtol,atol=atol,max_step=max_step,
                           dense_output=True,events=sonic_event)
    warning_messages=sorted({f'{type(w.message).__name__}: {w.message}' for w in recorded})
    for message in warning_messages:
        print('ZND numerical warning (recorded):',message,flush=True)
    if not solution.success:
        raise RuntimeError('ZND integration failed: '+solution.message)
    raw=solution.y;time=solution.t
    if len(time)<10 or not np.isfinite(raw).all() or raw[3:].min() < -100*atol or np.max(np.abs(raw[3:].sum(axis=0)-1))>1e-7:
        raise RuntimeError('ZND species or sample validity failed')
    # Cantera normalizes DPY; retain and validate the raw integrated species too.
    temperature=[];derivative=[];thermicity=[];enthalpy=[];gamma=[]
    def temperature_rate(t):
        state=solution.sol(t);working.DPY=state[1],state[0],state[3:]
        return float(znd.getTempDeriv(working,rho1,speed))
    for i in range(len(time)):
        working.DPY=raw[1,i],raw[0,i],raw[3:,i]
        temperature.append(working.T);enthalpy.append(working.enthalpy_mass)
        derivative.append(znd.getTempDeriv(working,rho1,speed))
        thermicity.append(znd.getThermicity(working));gamma.append(working.cp_mass/working.cv_mass)
    derivative=np.asarray(derivative);imax=int(derivative.argmax())
    if imax in (0,len(time)-1) or derivative[imax]<=0:
        raise RuntimeError('no interior positive maximum dT/dt; induction unresolved')
    peak=minimize_scalar(lambda t:-temperature_rate(t),bounds=(time[imax-1],time[imax+1]),
                         method='bounded',options={'xatol':1e-14,'maxiter':60})
    if not peak.success:raise RuntimeError('induction peak optimization failed')
    peak_time=float(peak.x);peak_distance=float(solution.sol(peak_time)[2])
    q_release=reference['initial']['Y']@hf-hf@raw[3:]
    heat_fraction=q_release/reference['q_equilibrium_Jkg']
    u=speed*rho1/raw[1];energy=np.asarray(enthalpy)+.5*u**2
    energy0=initial.enthalpy_mass+.5*speed**2
    momentum=raw[0]+raw[1]*u**2;momentum0=initial.P+rho1*speed**2
    errors=dict(energy=float(np.max(np.abs(energy-energy0))/max(abs(energy0),speed**2)),
                momentum=float(np.max(np.abs(momentum-momentum0))/momentum0))
    if max(errors.values())>1e-3:raise RuntimeError(f'ZND invariant drift exceeds 0.1%: {errors}')
    lengths={}
    for fraction in [.5,.9,.95]:
        cross=sampled_crossing(time,heat_fraction,fraction)
        lengths[str(fraction)]=None if cross is None else float(solution.sol(cross)[2])
    summary=dict(method='BDF on unmodified SDToolbox ZNDSys',rtol=rtol,atol=atol,max_step_s=max_step,
                 numerical_warnings=warning_messages,requested_end_s=end,actual_end_s=float(time[-1]),termination=solution.message,
                 stopped_at_sonic_event=bool(solution.t_events[0].size),samples=len(time),
                 raw_species_min=float(raw[3:].min()),raw_species_sum_max_error=float(np.max(np.abs(raw[3:].sum(axis=0)-1))),
                 invariant_relative_residuals=errors,induction_time_max_dTdt_s=peak_time,
                 induction_length_vn_velocity_m=reference['VN']['u_shock_frame']*peak_time,
                 distance_at_max_dTdt_m=peak_distance,
                 cell_size_factor29_proxy_m=29*reference['VN']['u_shock_frame']*peak_time,
                 peak_thermicity_time_s=float(time[np.argmax(thermicity)]),heat_fraction_lengths_m=lengths,
                 final_heat_fraction=float(heat_fraction[-1]))
    profile=dict(time_s=time,distance_m=raw[2],pressure_Pa=raw[0],temperature_K=np.asarray(temperature),
                 density_kg_m3=raw[1],velocity_mps=u,dTdt_K_s=derivative,thermicity_per_s=np.asarray(thermicity),
                 heat_fraction=heat_fraction,gamma=np.asarray(gamma),species_Y=raw[3:])
    return summary,profile


def validate_reference_inputs(config,calibration):
    """Reject mismatched mixture/state metadata without replacing the supplied fit."""
    from calibrate import calibrate
    expected=calibrate(config)
    for key in ['gamma','R','q','k','Ea','T1','p1','D_CJ','L_half']:
        if not np.isclose(calibration[key],expected[key],rtol=1e-9,atol=1e-12):
            raise ValueError(f'calibration {key} does not match the case')
    for key in ['p','T']:
        if not np.isclose(calibration['CJ'][key],expected['CJ'][key],rtol=1e-9,atol=1e-12):
            raise ValueError(f'calibration CJ {key} does not match the case')
    if not np.isfinite(calibration['p1']) or calibration['p1']<=0:
        raise ValueError('positive finite initial pressure required')


def compute_reference(config,calibration,directory):
    validate_reference_inputs(config,calibration)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    _write(directory/'inputs.json',dict(config=config,calibration=calibration,
           reference_state='CH4:phi, O2:2; p from Eq.4.1 fit; T from calibration; GRI-Mech 3.0 gri30.yaml',
           surrogate_source_sha256=hashlib.sha256((HERE/'calibrate.py').read_bytes()).hexdigest(),
           source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    try:
        ct,post,znd,thermo,manifest=_libraries()
        p,T,phi=calibration['p1'],calibration['T1'],config['operating_point']['phi']
        nominal,initial,working,hf=_cj(ct,post,thermo,p,T,phi)
        print('CJ reference:',nominal['CJ_speed_mps'],'m/s',flush=True)
        znd_summary,profile=_znd(ct,znd,thermo,nominal,initial,working,hf,1e-7,1e-11,2e-9)
        strict,initial,working,hf=_cj(ct,post,thermo,p,T,phi,tolerance=1e-9,minimum_tolerance=1e-8)
        strict_summary,strict_profile=_znd(ct,znd,thermo,strict,initial,working,hf,2e-8,2e-12,1e-9)
        differences=dict(CJ_speed_relative=abs(strict['CJ_speed_mps']/nominal['CJ_speed_mps']-1),
                         q_relative=abs(strict['q_equilibrium_Jkg']/nominal['q_equilibrium_Jkg']-1),
                         CJ_temperature_relative=abs(strict['CJ']['T']/nominal['CJ']['T']-1),
                         half_heat_length_relative=abs(strict_summary['heat_fraction_lengths_m']['0.5']/znd_summary['heat_fraction_lengths_m']['0.5']-1),
                         induction_time_relative=abs(strict_summary['induction_time_max_dTdt_s']/znd_summary['induction_time_max_dTdt_s']-1))
        if max(differences.values())>5e-3:raise RuntimeError(f'reference refinement difference exceeds 0.5%: {differences}')
        neighborhood=[nominal]
        for pcase,phicase in [(p,phi-.05),(p,phi+.05),(.9*p,phi),(1.1*p,phi)]:
            state,_,_,_=_cj(ct,post,thermo,pcase,T,phicase);neighborhood.append(state)
        mechanism=next(Path(folder)/'gri30.yaml' for folder in ct.get_data_directories() if (Path(folder)/'gri30.yaml').is_file())
        from calibrate import znd_profile
        surrogate=znd_profile(calibration,samples=500)
        np.savez_compressed(directory/'profiles.npz',**profile,
                            **{'strict_'+key:value for key,value in strict_profile.items()},
                            surrogate_distance_m=surrogate['distance'],surrogate_temperature_K=surrogate['temperature'],
                            surrogate_pressure_Pa=surrogate['pressure'],surrogate_heat_fraction=surrogate['progress'])
        summary=dict(status='completed',cantera_version=ct.__version__,mechanism=str(mechanism),
                     runtime=dict(python=platform.python_version(),platform=platform.platform(),
                                  packages={name:version(name) for name in ['numpy','scipy','cantera','ruamel.yaml','typing_extensions']}),
                     species_names=initial.species_names,
                     mechanism_sha256=hashlib.sha256(mechanism.read_bytes()).hexdigest(),sdtoolbox=manifest,
                     nominal=nominal,znd=znd_summary,strict=strict,strict_znd=strict_summary,
                     refinement_differences=differences,neighborhood=neighborhood,
                     CEA_status='Independent Cantera/GRI-Mech equilibrium cross-check; NASA CEA not executed.',
                     heat_release_definition='(Y_reactants - Y_CJ_products) dot species formation enthalpy per mass at 298.15 K; no LHV substitution',
                     induction_definition='ZND maximum dT/dt; paper-style length u_VN*t_ind; integrated distance reported separately; factor29 is a proxy',
                     CJ_algorithm='Bounded scalar minimum of upstream CJ_calc over density ratio [1.3,2.5], max 60 evaluations; jump/sonic/element checks',
                     surrogate=calibration)
        _write(directory/'summary.json',summary)
        return summary
    except Exception as error:
        _write(directory/'failure.json',dict(status='failed',error=str(error)))
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,default=HERE/'config.yaml')
    parser.add_argument('--calibration',type=Path,default=HERE/'calib.json')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    import yaml
    result=compute_reference(yaml.safe_load(args.case.read_text()),json.loads(args.calibration.read_text()),args.out)
    print(args.out,result['status'])


if __name__=='__main__':
    main()
