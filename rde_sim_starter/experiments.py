"""Bounded contact and 1D spatial-refinement experiments using the frozen solver.

These are diagnostic runs, not new engine defaults. Rendering is in plot.py.
All integrated contact quantities are per unit transverse area (J/m², kg/m²).
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from analyze import conservation_budget
from physics import source_step_limit
from run import _write_json, _write_npz, _fingerprint
from solver import Solver, InvalidStateError, TRANSMIT, WALL


def contact_exact(x, dx, time_s, contact_m, velocity, pressure, cold_T, hot_T, R):
    """Exact frozen advected contact, averaged in conservative variables per cell.

    Hot fully reacted gas is on the left, cold fresh gas on the right. The hot
    volume fraction is not the mass-based reaction progress. No diffusion exists
    in this inviscid reference. Pressure and velocity remain uniform.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim!=1 or not np.isfinite(x).all() or not np.isfinite([dx,time_s,contact_m,velocity,pressure,cold_T,hot_T,R]).all() or min(dx,pressure,cold_T,hot_T,R)<=0 or time_s<0:
        raise ValueError('finite contact inputs with positive thermodynamic quantities required')
    fraction = np.clip((contact_m+velocity*time_s-(x-dx/2))/dx, 0., 1.)
    hot_rho, cold_rho = pressure/(R*hot_T), pressure/(R*cold_T)
    density = fraction*hot_rho+(1-fraction)*cold_rho
    return density, fraction*hot_rho/density


def run_contact(calibration, directory, dx=.5e-3, reactive=True, end=20e-6,
                velocity=300., hot_temperature=1500., source_cfl=.05):
    """One moving pressure-balanced contact with open, distant boundaries.

    Frozen controls set k=0; all cases share the reactive model's source step cap.
    This avoids changing temporal resolution when turning the source off.
    """
    if not np.isfinite([dx,end,velocity,hot_temperature]).all() or not 0<dx<=1e-3 or not 0<end<=20e-6 or hot_temperature<=0 or abs(velocity)>500:
        raise ValueError('bounded contact requires dx<=1 mm, end<=20 us and |u|<=500 m/s')
    c=calibration; length=.16; n=round(length/dx); dx=length/n
    cap=source_step_limit(c['gamma'],c['q'],c['R'],c['k'],c['Ea'],source_cfl)
    if not np.isfinite(cap): raise ValueError('a finite common reactive source cap is required')
    gas=tuple(c[key] for key in ['gamma','q','R','k','Ea'])
    if not reactive: gas=gas[:3]+(0.,gas[4])
    s=Solver(n,1,dx,1.,gas,(TRANSMIT,TRANSMIT,WALL,WALL),source_cfl=source_cfl)
    x=(np.arange(n)+.5)*dx
    rho,xi=contact_exact(x,dx,0.,length/2,velocity,c['p1'],c['T1'],hot_temperature,c['R'])
    s.set_prim(rho[:,None],velocity,0.,c['p1'],xi[:,None])
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    inputs=dict(kind='contact',reactive=bool(reactive),calibration=c,dx_m=dx,length_m=length,
                initial_contact_m=length/2,velocity_mps=velocity,hot_temperature_K=hot_temperature,
                cold_temperature_K=c['T1'],pressure_Pa=c['p1'],end_s=end,source_cfl=source_cfl,
                common_max_step_s=cap,transverse_extent_m=s.dy,
                source_control='k unchanged for reactive; k=0 for frozen control',
                implementation=_fingerprint(),experiment_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    _write_json(directory/'inputs.json',inputs)
    initial=s.conserved_totals();history=[];times=[];fields=[];tick=0;error=None;status='completed'
    def save():
        W=s.prim()[:,:,0].copy(); T=W[3]/(c['R']*W[0])
        rho_ref,xi_ref=contact_exact(x,dx,s.t,length/2,velocity,c['p1'],c['T1'],hot_temperature,c['R'])
        budget=conservation_budget(s.conserved_totals(),initial,s.cumulative_boundary,s.cumulative_source,1.,1.)
        scaled=np.abs(budget['residual'])/np.maximum(np.maximum(np.abs(initial),np.abs(budget['storage'])),1e-12)
        # The open boundaries should remain in their initial uniform states.
        edges=np.r_[0:4,n-4:n]
        boundary_error=max(float(np.max(np.abs(W[3,edges]/c['p1']-1))),
                           float(np.max(np.abs(W[0,edges]/rho_ref[edges]-1))))
        row=dict(time_s=s.t,conversion_J_m2=c['q']*s.cumulative_source[4]/s.dy,
                 fresh_mass_kg_m2=float(np.sum(W[0]*(1-W[4]))*dx),
                 pressure_max_Pa=float(W[3].max()),pressure_departure=float(np.max(np.abs(W[3]/c['p1']-1))),
                 temperature_max_K=float(T.max()),frozen_density_L1_kg_m3=float(np.mean(np.abs(W[0]-rho_ref))),
                 partial_progress_width_m=float(np.count_nonzero((W[4]>.01)&(W[4]<.99))*dx),
                 budget_scaled_max=float(np.max(scaled)),boundary_state_relative_error=boundary_error)
        history.append(row);times.append(s.t);fields.append(W)
    save();tick=1;started=time.monotonic()
    try:
        while s.t<end:
            target=min(end,tick*1e-6)
            s.step(dt_max=min(cap,target-s.t))
            if s.t>=target:
                save();tick+=1
    except InvalidStateError as caught:
        status='failed';error=str(caught)
    if times[-1]!=s.t: save()
    summary=dict(kind='contact',status=status,error=error,reactive=bool(reactive),dx_m=dx,
                 end_s=s.t,steps=s.steps,wall_seconds=time.monotonic()-started,
                 invalid_state_count=s.invalid_state_count,progress_roundoff_max=s.progress_roundoff_max,
                 final=history[-1],max_budget_scaled_residual=max(row['budget_scaled_max'] for row in history),
                 max_boundary_state_relative_error=max(row['boundary_state_relative_error'] for row in history),
                 history=history)
    _write_npz(directory/'fields.npz',x=x,times=np.asarray(times),primitive=np.asarray(fields))
    _write_json(directory/'summary.json',summary)
    return summary


def run_suite(calibration, directory, experiment, spacings=(.5e-3,.25e-3,.125e-3)):
    spacings=tuple(float(dx) for dx in spacings)
    if experiment not in ('contact','refinement') or len(spacings)<2 or len(set(spacings))!=len(spacings) or not np.isfinite(spacings).all() or min(spacings)<=0 or max(spacings)>1e-3:
        raise ValueError('contact/refinement and at least two distinct positive spacings <=1 mm required')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    _write_json(directory/'inputs.json',dict(kind=experiment,calibration=calibration,spacings_m=spacings,
        implementation=_fingerprint(),experiment_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        tube_driver_sha256=hashlib.sha256(Path(__file__).with_name('test_1d.py').read_bytes()).hexdigest(),
        policy='chemistry fixed across spacings; no engine run or calibration retuning'))
    cases=[]
    for dx in spacings:
        for reactive in ((False,True) if experiment=='contact' else (True,)):
            name=f'dx_{dx*1e3:g}mm'+(('_reactive' if reactive else '_frozen') if experiment=='contact' else '')
            if experiment=='contact':
                result=run_contact(calibration,directory/name,dx=dx,reactive=reactive)
            else:
                from test_1d import run_detonation
                result=run_detonation(calibration,directory/name,dx=dx)
            cases.append(dict(directory=name,dx_m=dx,reactive=reactive,summary=result))
            _write_json(directory/'summary.json',dict(kind=experiment,status='in_progress',cases=cases))
            print(name,result['status'],flush=True)
    result=dict(kind=experiment,status='completed' if all(c['summary']['status']=='completed' for c in cases) else 'failed',cases=cases)
    _write_json(directory/'summary.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment',choices=['contact','refinement'])
    parser.add_argument('--calibration',type=Path,default=Path(__file__).with_name('calib.json'))
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    result=run_suite(json.loads(args.calibration.read_text()),args.out,args.experiment)
    return 0 if result['status']=='completed' else 2


if __name__=='__main__':
    raise SystemExit(main())
