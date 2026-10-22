"""Small 1D propagation experiment and compatibility solver-test entry point.

With --out, save a bounded detonation check using the production solver. With
no arguments, run tests/test_solver.py as before. Imports never advance flow.
"""
import argparse
import json
from pathlib import Path
import time
import unittest
import numpy as np
from solver import Solver, InvalidStateError, REFLECT, TRANSMIT, WALL, NG


def detonation_case(calibration, source_cfl=.05, dx=.25e-3):
    c=calibration
    gas=tuple(c[key] for key in ['gamma','q','R','k','Ea'])
    n=round(.25/dx)
    if n<100:
        raise ValueError('1D check needs at least 100 cells over 250 mm')
    dx=.25/n
    s=Solver(n,1,dx,dx,gas,(REFLECT,TRANSMIT,WALL,WALL),source_cfl=source_cfl)
    x=(np.arange(n)+.5)*dx
    p=np.full((n,1),c['p1']); rho=p/(c['R']*c['T1']); xi=np.zeros((n,1))
    hot=x<.01
    p[hot]=2*c['CJ']['p']; rho[hot]=p[hot]/(c['R']*c['CJ']['T']); xi[hot]=1.
    s.set_prim(rho,0.,0.,p,xi)
    return s,x


def run_detonation(calibration, directory, source_cfl=.05, end=95e-6):
    """Save pressure/progress fronts; no engine or experimental validation implied."""
    from run import _write_json, _write_npz, _fingerprint
    if not 40e-6<end<=95e-6:
        raise ValueError('propagation check must end after 40 and at most 95 microseconds')
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    s,x=detonation_case(calibration,source_cfl)
    initial=s.conserved_totals()
    inputs=dict(case='1D one-step ignition/propagation',calibration=calibration,
                dx=s.dx,nx=s.nx,end_s=end,source_cfl=source_cfl,cfl=s.cfl,
                hot_patch_m=.01,pressure_multiplier=2.,speed_fit_start_s=40e-6,
                front_operator='last cell above 2*p1; half-reaction front is last xi>=0.5 cell behind it',
                implementation=_fingerprint())
    _write_json(directory/'inputs.json',inputs)
    times=[0.]; fields=[s.prim()[:,:,0].copy()]; history=[]; tick=1; status='completed'; error=None
    started=time.monotonic()
    try:
        while s.t<end:
            s.step(dt_max=min(end,tick*5e-6)-s.t)
            W=s.prim()[:,:,0]
            front=np.flatnonzero(W[3]>2*calibration['p1'])
            shock=x[front[-1]] if front.size else np.nan
            reacted=np.flatnonzero((W[4]>=.5)&(x<=shock))
            half=x[reacted[-1]] if reacted.size else np.nan
            history.append([s.t,shock,half,float(W[3].max())])
            if s.t>=tick*5e-6:
                times.append(s.t); fields.append(W.copy()); tick+=1
    except InvalidStateError as caught:
        status='failed'; error=str(caught)
    if times[-1]!=s.t:
        times.append(s.t); fields.append(s.prim()[:,:,0].copy())
    h=np.asarray(history).reshape(-1,4)
    usable=(h[:,0]>40e-6)&np.isfinite(h[:,1])
    speed=float(np.polyfit(h[usable,0],h[usable,1],1)[0]) if usable.sum()>20 else None
    from analyze import conservation_budget
    budget=conservation_budget(s.conserved_totals(),initial,s.cumulative_boundary,s.cumulative_source,1.,1.)
    summary=dict(status=status,error=error,t=s.t,steps=s.steps,wall_seconds=time.monotonic()-started,
                 speed_mps=speed,speed_relative_error=None if speed is None else speed/calibration['D_CJ']-1,
                 final_front_separation_m=None if not h.size or not np.isfinite(h[-1,1:3]).all() else float(h[-1,1]-h[-1,2]),
                 invalid_state_count=s.invalid_state_count,last_failure=s.last_failure,
                 progress_roundoff_max=s.progress_roundoff_max,
                 max_inventory_scaled_residual=float(np.max(np.abs(budget['residual'])/np.maximum(np.abs(initial),1.))),
                 budget=budget)
    _write_npz(directory/'fields.npz',x=x,times=np.asarray(times),primitive=np.asarray(fields),history=h)
    _write_json(directory/'summary.json',summary)
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,help='new saved 1D experiment directory')
    parser.add_argument('--source-cfl',type=float,default=.05)
    parser.add_argument('--calibration',type=Path,default=Path(__file__).with_name('calib.json'))
    args=parser.parse_args(argv)
    if args.out:
        result=run_detonation(json.loads(args.calibration.read_text()),args.out,args.source_cfl)
        print(json.dumps({k:v for k,v in result.items() if k!='budget'},indent=2))
        return 0 if result['status']=='completed' else 2
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).with_name('tests')),pattern='test_solver.py')
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__=='__main__':
    raise SystemExit(main())
