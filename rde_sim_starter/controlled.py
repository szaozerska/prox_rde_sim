"""Small controlled 2D diagnostics; imports never advance flow or render.

C1 uses matched reflecting walls for exact coordinate/row comparisons, plus the
original open-ended 1D case as a separate boundary control. No engine defaults
or chemistry parameters are changed. All runs require a new output directory.
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
from solver import Solver, InvalidStateError, REFLECT, TRANSMIT, WALL


def blast_strip(c, dx=.5e-3, rows=8, direction='x', length=.25, open_end=False):
    if (not np.isfinite([dx,length]).all() or not 0 < dx <= 1e-3 or length < .05
            or not isinstance(rows,int) or rows < 1 or direction not in ('x','z')
            or (direction=='z' and (rows<2 or open_end))):
        raise ValueError('valid spacing/length, integer rows and supported direction required')
    n=round(length/dx); ds=length/n
    gas=tuple(c[k] for k in ('gamma','q','R','k','Ea'))
    bc=(REFLECT,TRANSMIT if open_end else REFLECT,WALL,WALL)
    shape=(n,rows) if direction=='x' else (rows,n)
    s=Solver(*shape,ds,ds,gas,bc,source_cfl=.05)
    along=(np.arange(n)+.5)*ds
    patch=(along<.01)[:,None] if direction=='x' else (along<.01)[None,:]
    p=np.where(patch,2*c['CJ']['p'],c['p1'])
    temp=np.where(patch,c['CJ']['T'],c['T1'])
    s.set_prim(p/(c['R']*temp),0.,0.,p,patch.astype(float))
    return s,along


def canonical_fields(s,direction):
    w=s.prim().copy()
    return w if direction=='x' else w[[0,2,1,3,4]].transpose(0,2,1)


def comparison_metrics(solvers,directions,c):
    fields=[canonical_fields(s,d) for s,d in zip(solvers,directions)]
    scales=np.array([c['p1']/(c['R']*c['T1']),c['D_CJ'],c['D_CJ'],c['CJ']['p'],1.])[:,None,None]
    reference=fields[0]
    return dict(max_scaled_difference=[float(np.max(np.abs(w-reference)/scales)) for w in fields],
                max_transverse_variation=[float(np.max(np.abs(w-w[:,:,:1])/scales)) for w in fields])


def run_strip(c,directory,dx=.5e-3,rows=8,end=95e-6,length=.25):
    if not np.isfinite(end) or not 0 < end <= 95e-6 or rows<2:
        raise ValueError('strip control needs >=2 transverse rows and 0<end<=95 us')
    specs=[('closed_1d',1,'x',False),('strip_x',rows,'x',False),
           ('strip_z',rows,'z',False),('original_open_1d',1,'x',True)]
    built=[blast_strip(c,dx,r,d,length,op) for _,r,d,op in specs]
    solvers=[v[0] for v in built]; x=built[0][1]; directions=[v[2] for v in specs]
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    cap=source_step_limit(c['gamma'],c['q'],c['R'],c['k'],c['Ea'],.05)
    _write_json(directory/'inputs.json',dict(kind='strip',calibration=c,dx_m=solvers[0].dx,
        rows=rows,length_m=length,end_s=end,common_source_cap_s=cap,
        cases=[dict(name=n,rows=r,direction=d,open_end=op) for n,r,d,op in specs],
        implementation=_fingerprint(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policy='identical chemistry and timestep; matched reflecting walls plus original 1D outlet control'))
    initial=[s.conserved_totals() for s in solvers]
    history=[];times=[];fields=[];status='completed';error=None;tick=1;started=time.monotonic()
    def save():
        met=comparison_metrics(solvers,directions,c); fronts=[];separations=[];budget_errors=[]
        for s,d,tot in zip(solvers,directions,initial):
            w=canonical_fields(s,d)[:,:,0]
            ii=np.flatnonzero(w[3]>2*c['p1']);front=float(x[ii[-1]]) if ii.size else None
            jj=np.flatnonzero((w[4]>=.5)&(x <= (front if front is not None else -1)))
            fronts.append(front);separations.append(float(front-x[jj[-1]]) if jj.size else None)
            budget=conservation_budget(s.conserved_totals(),tot,s.cumulative_boundary,s.cumulative_source,1.,1.)
            rho1=c['p1']/(c['R']*c['T1']);volume=s.nx*s.dx*s.ny*s.dy
            scale=np.maximum(np.abs(tot),np.array([rho1,rho1*c['D_CJ'],rho1*c['D_CJ'],c['p1']/(c['gamma']-1)+rho1*c['q'],rho1])*volume)
            budget_errors.append(float(np.max(np.abs(budget['residual'])/scale)))
        history.append(dict(time_s=solvers[0].t,front_m=fronts,front_half_reaction_separation_m=separations,
                            budget_scaled_residual=budget_errors,**met))
        times.append(solvers[0].t)
        fields.append(np.stack([canonical_fields(s,d)[:,:,0] for s,d in zip(solvers,directions)]))
    save()
    try:
        while solvers[0].t < end:
            target=min(end,tick*5e-6);dt=min(cap,target-solvers[0].t)
            actual=[s.step(dt_max=dt) for s in solvers]
            if max(actual)!=min(actual):raise RuntimeError('C1 requires equal accepted timesteps')
            if solvers[0].t>=target:save();tick+=1
    except (InvalidStateError,RuntimeError) as caught:
        status='failed';error=str(caught)
    if times[-1]!=solvers[0].t:save()
    speeds=[]
    for i in range(len(specs)):
        valid=[h for h in history if h['time_s']>=40e-6 and h['front_m'][i] is not None]
        speeds.append(float(np.polyfit([h['time_s'] for h in valid],[h['front_m'][i] for h in valid],1)[0]) if len(valid)>=3 else None)
    errors=np.array([h['max_scaled_difference'] for h in history]);trans=np.array([h['max_transverse_variation'] for h in history])
    passed=(status=='completed' and np.max(errors[:,:3])<1e-10 and np.max(trans)<1e-10)
    result=dict(kind='strip',status=status,error=error,control_passed=bool(passed),
        cases=[v[0] for v in specs],time_s=solvers[0].t,steps=solvers[0].steps,
        wall_seconds=time.monotonic()-started,max_scaled_difference=errors.max(axis=0).tolist(),
        max_transverse_variation=trans.max(axis=0).tolist(),speed_40us_to_end_mps=speeds,
        max_budget_scaled_residual=float(np.max([h['budget_scaled_residual'] for h in history])),
        invalid_state_count=[s.invalid_state_count for s in solvers],history=history,
        interpretation='row/direction verification; pressure tracks are not detonation classification')
    _write_npz(directory/'fields.npz',x=x,times=np.asarray(times),primitive=np.asarray(fields))
    _write_json(directory/'summary.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment',choices=['strip'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--calibration',type=Path,default=Path(__file__).with_name('calib.json'))
    args=parser.parse_args(argv)
    result=run_strip(json.loads(args.calibration.read_text()),args.out)
    print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2))
    return 0 if result['control_passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
