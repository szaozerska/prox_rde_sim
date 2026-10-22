"""Opt-in C5 quarter-length sensitivity; baseline chemistry/solver stay unchanged."""
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path
import time
import numpy as np
from scipy.integrate import solve_ivp
from controlled import formed_profile, run_formed, run_layer
from experiments import run_contact
from physics import source_step_limit
from run import _write_json, _fingerprint
from solver import Solver, PERIODIC, WALL


def short_calibration(baseline):
    c=copy.deepcopy(baseline)
    if not np.isclose(c['L_half'],.001,rtol=1e-10,atol=0):
        raise ValueError('this experiment requires the inherited 1 mm baseline')
    c['k']*=4
    c['L_half']/=4
    return c


def fingerprint():
    result=_fingerprint()
    return dict(solver=result,drivers={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                     for name in ('short_reaction.py','controlled.py','experiments.py')})


def reactor_check(c,T0,xi0,end,fraction):
    g,q,R,k,Ea=(c[key] for key in ('gamma','q','R','k','Ea'))
    A=(g-1)*q/R
    def rhs(t,y):return [(1-y[0])*k*np.exp(-Ea/(R*(T0+A*(y[0]-xi0))))]
    reference=solve_ivp(rhs,(0,end),[xi0],method='DOP853',rtol=2e-12,atol=2e-14,dense_output=True)
    tighter=solve_ivp(rhs,(0,end),[xi0],method='DOP853',rtol=2e-13,atol=2e-15,dense_output=True)
    if not reference.success or not tighter.success:raise RuntimeError('independent reactor solve failed')
    s=Solver(4,1,1.,1.,(g,q,R,k,Ea),(PERIODIC,PERIODIC,WALL,WALL),source_cfl=fraction)
    s.set_prim(1.,0.,0.,R*T0,xi0)
    initial=s.conserved_totals();error=0.;reference_error=0.
    while s.t<end:
        s.step(dt_max=end-s.t)
        expected=float(reference.sol(s.t)[0])
        error=max(error,abs(float(s.prim()[4,0,0])-expected))
        reference_error=max(reference_error,abs(float(tighter.sol(s.t)[0])-expected))
    energy_error=float(np.max(abs(s.conserved_totals()[:4]-initial[:4])/np.maximum(abs(initial[:4]),1.)))
    return dict(T0_K=T0,xi0=xi0,end_s=end,source_cfl=fraction,steps=s.steps,
        max_progress_error=error,reference_tolerance_difference=reference_error,
        conserved_relative_error=energy_error,invalid_state_count=s.invalid_state_count)


def require_run(result):
    if result['status']!='completed' or result['invalid_state_count'] or result['max_budget_scaled_residual']>1e-10:
        raise RuntimeError('state/budget gate failed; inspect saved case')


def contact_boundary_check(c,directory):
    """Compare far fields to homogeneous chemistry, not a frozen fresh state."""
    directory=Path(directory)
    inputs=json.loads((directory/'inputs.json').read_text())
    with np.load(directory/'fields.npz') as a:
        times=a['times'];w=a['primitive']
    A=(c['gamma']-1)*c['q']/c['R']
    if inputs['reactive']:
        ode=solve_ivp(lambda t,y:[(1-y[0])*c['k']*np.exp(-c['Ea']/(c['R']*(c['T1']+A*y[0])))],
                      (0,float(times[-1])),[0.],t_eval=times,method='DOP853',rtol=2e-12,atol=2e-14)
        if not ode.success:raise RuntimeError('background reactor reference failed')
        xi=ode.y[0]
    else:xi=np.zeros(len(times))
    cold=np.array([np.full(len(times),c['p1']/(c['R']*c['T1'])),
                   np.full(len(times),inputs['velocity_mps']),np.zeros(len(times)),
                   c['p1']*(1+A*xi/c['T1']),xi]).T
    hot=cold.copy();hot[:,0]=c['p1']/(c['R']*inputs['hot_temperature_K']);hot[:,3]=c['p1'];hot[:,4]=1.
    scales=np.array([cold[0,0],max(abs(inputs['velocity_mps']),1.),c['a1'],c['p1'],1.])
    error=max(float(np.max(abs(w[:,:,:4]-hot[:,:,None])/scales[None,:,None])),
              float(np.max(abs(w[:,:,-4:]-cold[:,:,None])/scales[None,:,None])))
    return dict(homogeneous_boundary_scaled_error=error,
                cold_background_pressure_relative_change=float(A*xi[-1]/c['T1']))


def verify(c,directory,reuse=None):
    if reuse is not None:
        reuse=Path(reuse)
        prior=json.loads((reuse/'verification.json').read_text())
        current=fingerprint()
        if prior.get('calibration')!=c or prior['fingerprint']['solver']!=current['solver'] or any(
            prior['fingerprint']['drivers'][n]!=current['drivers'][n] for n in ('controlled.py','experiments.py')):
            raise ValueError('reused flow cases must have identical chemistry and simulation code')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    def case(name,runner,**kwargs):
        if reuse is not None and (reuse/name/'summary.json').exists():
            inputs=json.loads((reuse/name/'inputs.json').read_text())
            if inputs['calibration']!=c or inputs['end_s']!=kwargs['end'] or inputs['dx_m']!=kwargs['dx'] or inputs['source_cfl']!=kwargs.get('source_cfl',.05):
                raise ValueError('reused case inputs differ')
            if 'reactive' in kwargs and inputs['reactive']!=kwargs['reactive']:raise ValueError('reactivity mismatch')
            result=json.loads((reuse/name/'summary.json').read_text());require_run(result)
            shutil.copytree(reuse/name,directory/name)
            return result
        return runner(c,directory/name,**kwargs)
    report=dict(status='running',calibration=c,fingerprint=fingerprint(),reactors=[],formed=[],contacts=[],
                interpretation='verification of a declared surrogate, not physical validation',
                reused_verification=str(reuse.resolve()) if reuse is not None else None)
    _write_json(directory/'verification.json',report)
    started=time.monotonic()
    try:
        p=formed_profile(c);report['profile']=p['verification']
        if max(p['verification']['jump_max_relative_error'])>1e-8:raise RuntimeError('profile jump gate failed')
        if abs(p['verification']['length_m']['0.5']/.00025-1)>1e-8:raise RuntimeError('reaction length gate failed')
        for T,xi,end in ((300.,0.,2.5e-6),(1000.,0.,7.5e-6),(c['VN']['T'],.35,1.5e-6)):
            pair=[reactor_check(c,T,xi,end,f) for f in (.05,.025)]
            report['reactors'].extend(pair)
            for r in pair:
                if r['max_progress_error']>2e-4 or r['reference_tolerance_difference']>1e-8 or r['conserved_relative_error']>2e-14 or r['invalid_state_count']:
                    raise RuntimeError('reactor accuracy/conservation gate failed')
            if pair[0]['max_progress_error']>1e-10 and pair[0]['max_progress_error']/pair[1]['max_progress_error']<3.5:
                raise RuntimeError('reactor temporal refinement gate failed')
        _write_json(directory/'verification.json',report)
        for dx,f in ((.125e-3,.05),(.0625e-3,.05),(.125e-3,.025)):
            name=f'formed_{dx*1e3:g}_{f:g}'
            r=case(name,run_formed,dx=dx,end=10e-6,source_cfl=f,profile=p,domain_scale=.25)
            report['formed'].append(dict(case=name,summary=r));require_run(r)
            late=[h for h in r['history'] if h['time_s']>=5e-6]
            speed=float(np.polyfit([h['time_s'] for h in late],[h['front_m'] for h in late],1)[0])
            report['formed'][-1]['late_speed_mps']=speed
            if abs(speed/c['D_CJ']-1)>.02:raise RuntimeError('planar speed gate failed')
            if any(min(h['left_causal_margin_m'],h['right_causal_margin_m'])<=0 for h in r['history']):
                raise RuntimeError('planar causal margin failed')
            if any(h['reaction_max_per_s']<1e5 or h['front_rate_peak_separation_m']>.002 for h in late):
                raise RuntimeError('planar shock/reaction association failed')
            _write_json(directory/'verification.json',report)
        if abs(report['formed'][2]['late_speed_mps']-report['formed'][0]['late_speed_mps'])/c['D_CJ']>.01:
            raise RuntimeError('planar source-step gate failed')
        for dx in (.125e-3,.0625e-3):
            for reactive in (False,True):
                name=f'contact_{dx*1e3:g}_{reactive}'
                r=case(name,run_contact,dx=dx,end=5e-6,reactive=reactive)
                report['contacts'].append(dict(case=name,summary=r));require_run(r)
                boundary=contact_boundary_check(c,directory/name)
                report['contacts'][-1]['boundary_reference']=boundary
                if boundary['homogeneous_boundary_scaled_error']>1e-9:raise RuntimeError('contact boundary gate failed')
                if not reactive and (abs(r['final']['conversion_J_m2'])>1e-12 or r['final']['pressure_departure']>1e-10):
                    raise RuntimeError('frozen contact gate failed')
                _write_json(directory/'verification.json',report)
        report['status']='passed'
    except Exception as exc:
        report['status']='failed';report['error']=str(exc)
        raise
    finally:
        report['wall_seconds']=time.monotonic()-started
        _write_json(directory/'verification.json',report)
    return report


def checked_verification(c,directory):
    path=Path(directory)/'verification.json'
    report=json.loads(path.read_text())
    if report.get('status')!='passed' or report.get('calibration')!=c or report.get('fingerprint')!=fingerprint():
        raise ValueError('successful matching verification required before layer runs')
    return dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def layer_pair(c,directory,verification):
    provenance=checked_verification(c,verification)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    _write_json(directory/'experiment.json',dict(calibration=c,verification=provenance,fingerprint=fingerprint(),
        end_s=10e-6,layer_height_m=.0038,dx_m=[.000125,.0000625],domain_scale=.25,
        interpretation='10 us finite-layer sensitivity; no engine or critical-height claim'))
    p=formed_profile(c)
    results=[]
    for dx in (.125e-3,.0625e-3):
        r=run_layer(c,directory/f'layer_{dx*1e3:g}',.0038,dx=dx,end=10e-6,profile=p,
                    domain_scale=.25,transverse_bound=3200.)
        results.append(r)
        _write_json(directory/'summary.json',dict(cases=results))
        require_run(r)
    return results


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('verify','layer'))
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--verification',type=Path)
    parser.add_argument('--reuse',type=Path,help='reuse matching completed verification flow cases after a diagnostic-only correction')
    args=parser.parse_args(argv)
    if args.stage=='layer' and args.verification is None:parser.error('layer requires --verification')
    c=short_calibration(json.loads(Path(__file__).with_name('calib.json').read_text()))
    if args.stage=='layer' and args.reuse is not None:parser.error('--reuse applies only to verify')
    if args.stage=='verify':verify(c,args.out,reuse=args.reuse)
    else:layer_pair(c,args.out,args.verification)
    print(args.out)


if __name__=='__main__':main()
