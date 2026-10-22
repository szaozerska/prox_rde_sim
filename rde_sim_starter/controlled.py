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


def conserved_state(rho,u,p,xi,c):
    rho,u,p,xi=np.broadcast_arrays(rho,u,p,xi)
    return np.array([rho,rho*u,np.zeros_like(rho),
        p/(c['gamma']-1)+.5*rho*u*u+rho*c['q']*(1-xi),rho*xi])


def formed_profile(c,samples=2401):
    """Tabulated strong-branch ZND in laboratory coordinates, finite 1e-6 tail.

    Exact antiderivatives below conserve this piecewise-linear table. Increasing
    the table density is an independent check on interpolation of the steady ODE.
    """
    from scipy.integrate import quad,solve_ivp
    from calibrate import state,dx_dxi
    if not isinstance(samples,int) or samples<101:raise ValueError('at least 101 profile nodes required')
    eta=np.linspace(0,np.log(1e6),samples)
    xi=-np.expm1(-eta)
    vals=np.array([state(float(a),c) for a in xi])
    rho=vals[:,1]*c['p1']/(c['R']*vals[:,0]*c['T1']);u=c['D_CJ']-vals[:,3]
    U=conserved_state(rho,u,vals[:,1]*c['p1'],xi,c)
    def derivative(e,_):
        temperature,_,_,w=state(float(-np.expm1(-e)),c)
        return [w/c['k']*np.exp(c['Ea']/(c['R']*temperature*c['T1']))]
    distance_solution=solve_ivp(derivative,(0.,eta[-1]),[0.],t_eval=eta,
                                method='DOP853',rtol=1e-10,atol=1e-13)
    if not distance_solution.success:raise RuntimeError(distance_solution.message)
    dist=distance_solution.y[0]
    fresh=conserved_state(c['p1']/(c['R']*c['T1']),0.,c['p1'],0.,c)
    T,p,_,w=state(1.,c)
    burned=conserved_state(p*c['p1']/(c['R']*T*c['T1']),c['D_CJ']-w,p*c['p1'],1.,c)
    increments=.5*(U[:,1:]+U[:,:-1])*np.diff(dist)
    cumulative=np.column_stack((np.zeros(5),np.cumsum(increments,axis=1)))
    # Independent shock-frame flux/enthalpy identities, evaluated from saved U.
    joined=np.column_stack((U,burned));r=joined[0];vel=joined[1]/r;progress=joined[4]/r
    pressure=(c['gamma']-1)*(joined[3]-.5*r*vel**2-c['q']*(r-joined[4]))
    w=c['D_CJ']-vel; temp=pressure/(r*c['R']);rf=fresh[0]
    targets=np.array([rf*c['D_CJ'],c['p1']+rf*c['D_CJ']**2,
                     c['gamma']*c['R']*c['T1']/(c['gamma']-1)+.5*c['D_CJ']**2+c['q']])
    invariants=np.array([r*w,pressure+r*w*w,
        c['gamma']*c['R']*temp/(c['gamma']-1)+.5*w*w+c['q']*(1-progress)])
    lengths={str(a):quad(dx_dxi,0,a,args=(c['k'],c),epsabs=1e-12)[0] for a in (.5,.9,.95)}
    return dict(distance=dist,U=U,cumulative=cumulative,fresh=fresh,burned=burned,
        verification=dict(samples=samples,tail_progress=float(xi[-1]),tail_distance_m=float(dist[-1]),
            tail_pressure_relative_jump=float(abs(burned[0]*c['R']*T*c['T1']/pressure[-2]-1)),
            jump_max_relative_error=np.max(np.abs(invariants/targets[:,None]-1),axis=1).tolist(),
            length_m=lengths,table_length_relative_error={str(a):float(np.interp(a,xi,dist)/lengths[str(a)]-1) for a in (.5,.9,.95)}))


def profile_integral(profile,position):
    """Integral of conserved density from the shock to signed distance behind it."""
    x=np.asarray(position,dtype=float)
    if x.ndim!=1 or not np.isfinite(x).all():raise ValueError('finite one-dimensional positions required')
    d=profile['distance'];U=profile['U'];idx=np.clip(np.searchsorted(d,x,side='right')-1,0,len(d)-2)
    h=np.clip(x,0,d[-1])-d[idx]
    result=profile['cumulative'][:,idx]+U[:,idx]*h+.5*(U[:,idx+1]-U[:,idx])/np.diff(d)[idx]*h*h
    left=x<0;right=x>d[-1]
    result[:,left]=profile['fresh'][:,None]*x[left]
    result[:,right]=profile['cumulative'][:,-1,None]+profile['burned'][:,None]*(x[right]-d[-1])
    return result


def profile_cell_average(profile,lo,hi):
    """Split constant fresh/burned regions before subtraction to avoid cancellation.

    This preserves exactly reacted cells without clipping conserved progress.
    """
    lo=np.asarray(lo,dtype=float);hi=np.asarray(hi,dtype=float)
    if lo.shape!=hi.shape or lo.ndim!=1 or not np.isfinite([lo,hi]).all() or np.any(hi<=lo):
        raise ValueError('finite ordered cell intervals required')
    tail=profile['distance'][-1]
    fresh_width=np.maximum(np.minimum(hi,0)-lo,0)
    burned_width=np.maximum(hi-np.maximum(lo,tail),0)
    inner_lo=np.clip(lo,0,tail);inner_hi=np.clip(hi,0,tail)
    integral=profile_integral(profile,inner_hi)-profile_integral(profile,inner_lo)
    integral+=profile['fresh'][:,None]*fresh_width+profile['burned'][:,None]*burned_width
    return integral/(hi-lo)


def formed_strip(c,profile,dx=.5e-3,rows=8,length=.45,shock=.16,source_cfl=.05):
    if (not np.isfinite([dx,length,shock]).all() or not 0<dx<=1e-3 or not isinstance(rows,int)
            or rows<2 or not profile['distance'][-1]<shock<length):
        raise ValueError('valid spacing, rows and shock separated from domain ends required')
    nx=round(length/dx);dx=length/nx;x=(np.arange(nx)+.5)*dx
    avg=profile_cell_average(profile,shock-(x+dx/2),shock-(x-dx/2))
    s=Solver(nx,rows,dx,dx,tuple(c[k] for k in ('gamma','q','R','k','Ea')),
             (TRANSMIT,TRANSMIT,WALL,WALL),source_cfl=source_cfl)
    from solver import NG
    s.U[:,NG:-NG,NG:-NG]=avg[:,:,None]
    s._check_state(s.U,'formed profile initialization')
    return s,x


def run_formed(c,directory,dx=.5e-3,end=40e-6,source_cfl=.05,profile=None):
    """C2 fully filled propagation, with a predeclared 4000 m/s axial cone bound."""
    if not np.isfinite(end) or not 0<end<=40e-6:raise ValueError('0<end<=40 us required')
    profile=formed_profile(c) if profile is None else profile
    if max(profile['verification']['jump_max_relative_error'])>1e-8:raise ValueError('steady jump check failed')
    length=.45;shock=.16;s,x=formed_strip(c,profile,dx=dx,source_cfl=source_cfl)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    bound=4000.;roi=.03
    _write_json(directory/'inputs.json',dict(kind='formed',calibration=c,dx_m=s.dx,
        rows=s.ny,length_m=length,shock_initial_m=shock,end_s=end,source_cfl=source_cfl,
        axial_characteristic_bound_mps=bound,reaction_roi_behind_front_m=roi,
        profile_verification=profile['verification'],implementation=_fingerprint(),
        driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policy='unforced formed wave; uniform transverse state; no imposed driver; fixed chemistry'))
    initial=s.conserved_totals();history=[];fields=[];times=[];status='completed';error=None
    rho1=c['p1']/(c['R']*c['T1']);volume=length*s.ny*s.dy
    scale=np.maximum(abs(initial),np.array([rho1,rho1*c['D_CJ'],rho1*c['D_CJ'],c['p1']/(c['gamma']-1)+rho1*c['q'],rho1])*volume)
    observed=0.;started=time.monotonic()
    def save():
        w=s.prim().copy();p=w[3,:,0];xi=w[4,:,0];T=p/(c['R']*w[0,:,0])
        rate=c['k']*(1-xi)*np.exp(-c['Ea']/(c['R']*T))
        ii=np.flatnonzero(p>2*c['p1']);front=float(x[ii[-1]]) if ii.size else None
        region=(x>=front-roi)&(x<=front) if front is not None else np.zeros(x.size,dtype=bool)
        peak=int(np.argmax(np.where(region,rate,-1))) if region.any() else None
        # Local fresh state ahead of the pressure front; no assumed lab Mach.
        ahead=(x>front+2*s.dx)&(x<front+roi) if front is not None else np.zeros(x.size,dtype=bool)
        budget=conservation_budget(s.conserved_totals(),initial,s.cumulative_boundary,s.cumulative_source,1.,1.)
        history.append(dict(time_s=s.t,front_m=front,pressure_max_Pa=float(p.max()),
            reaction_peak_m=float(x[peak]) if peak is not None else None,
            front_rate_peak_separation_m=float(front-x[peak]) if peak is not None else None,
            reaction_max_per_s=float(rate[peak]) if peak is not None else None,
            upstream_u_mps=float(w[1,:,0][ahead].mean()) if ahead.any() else None,
            upstream_sound_mps=float(np.sqrt(c['gamma']*p[ahead]/w[0,:,0][ahead]).mean()) if ahead.any() else None,
            converted_J_per_m_depth=float(c['q']*s.cumulative_source[4]),
            budget_scaled_residual=float(np.max(abs(budget['residual'])/scale)),
            left_causal_margin_m=float(front-roi-bound*s.t) if front is not None else None,
            right_causal_margin_m=float(length-front-bound*s.t) if front is not None else None,
            transverse_max_scaled=float(np.max(abs(w-w[:,:,:1])/np.array([rho1,c['D_CJ'],c['D_CJ'],c['CJ']['p'],1.])[:,None,None]))))
        fields.append(w[:,:,0]);times.append(s.t)
    save();tick=1
    from solver import NG
    try:
        while s.t<end:
            target=min(end,tick*2e-6);s.step(dt_max=target-s.t)
            # Include the retained intermediate RK state and final accepted state.
            for w in (s.W[:,NG:-NG,NG:-NG].copy(),s.prim()):
                observed=max(observed,float(np.max(abs(w[1])+np.sqrt(c['gamma']*w[3]/w[0]))))
            if observed>bound:raise RuntimeError('predeclared axial characteristic bound exceeded')
            if s.t>=target:
                save();tick+=1
                if min(history[-1]['left_causal_margin_m'],history[-1]['right_causal_margin_m'])<=0:
                    raise RuntimeError('remote-boundary causal cone reaches measurement region')
    except (InvalidStateError,RuntimeError) as caught:status='failed';error=str(caught)
    if times[-1]!=s.t:save()
    fits={}
    for start in (10e-6,20e-6,30e-6):
        hh=[h for h in history if h['time_s']>=start and h['front_m'] is not None]
        fits[str(start)]=float(np.polyfit([h['time_s'] for h in hh],[h['front_m'] for h in hh],1)[0]) if len(hh)>=3 else None
    summary=dict(kind='formed',status=status,error=error,time_s=s.t,steps=s.steps,
        wall_seconds=time.monotonic()-started,dx_m=s.dx,source_cfl=source_cfl,
        observed_axial_characteristic_max_mps=observed,speed_from_time_mps=fits,
        invalid_state_count=s.invalid_state_count,max_budget_scaled_residual=max(h['budget_scaled_residual'] for h in history),
        initial_conserved_per_m_depth=initial.tolist(),final_conserved_per_m_depth=s.conserved_totals().tolist(),
        cumulative_boundary=s.cumulative_boundary.tolist(),cumulative_source=s.cumulative_source.tolist(),
        profile_verification=profile['verification'],history=history,
        interpretation='finite-window formed-wave propagation; inspect pressure, reaction and causality together; no automatic detonation label')
    _write_npz(directory/'fields.npz',x=x,times=np.array(times),primitive=np.array(fields))
    _write_json(directory/'summary.json',summary)
    return summary


def formed_layer(c,profile,layer_height,dx=.5e-3,length=.45,shock=.16,buffer=.13,align_interface=False):
    """Conservative area average: formed wave below h, static hot products above."""
    if not np.isfinite([layer_height,buffer]).all() or not 0<layer_height<=.03 or buffer<=0:
        raise ValueError('0<h<=30 mm and positive product buffer required')
    s0,x=formed_strip(c,profile,dx=dx,length=length,shock=shock,rows=2)
    if align_interface:
        # Nested transverse meshes place h exactly on a face. The small extra
        # product buffer is constant across the permitted refinement levels.
        refinement=.5e-3/s0.dx
        if not np.isclose(refinement,round(refinement)) or refinement<1:
            raise ValueError('aligned interface requires 0.5 mm divided by an integer')
        refinement=round(refinement);base_rows=int(np.ceil(layer_height/.5e-3))
        base_dy=layer_height/base_rows;buffer_rows=int(np.ceil(buffer/base_dy))
        ny=(base_rows+buffer_rows)*refinement;dy=base_dy/refinement;height=ny*dy
        fraction=(np.arange(ny)<base_rows*refinement).astype(float)
    else:
        height=layer_height+buffer;ny=round(height/s0.dx);dy=height/ny
        fraction=np.clip((layer_height-np.arange(ny)*dy)/dy,0,1)
    if ny<2:raise ValueError('layer domain needs at least two rows')
    hot=conserved_state(c['p1']/(c['R']*1500.),0.,c['p1'],1.,c)
    from solver import NG
    s=Solver(s0.nx,ny,s0.dx,dy,tuple(c[k] for k in ('gamma','q','R','k','Ea')),
             (TRANSMIT,TRANSMIT,WALL,WALL),source_cfl=.05)
    s.U[:,NG:-NG,NG:-NG]=s0.U[:,NG:-NG,NG][:,:,None]*fraction+hot[:,None,None]*(1-fraction)
    s._check_state(s.U,'conservative layer initialization')
    baseline=(profile['fresh']*layer_height+hot*(height-layer_height))*length
    info=dict(layer_height_m=layer_height,height_m=height,dx_m=s.dx,dy_m=s.dy,
        product_temperature_K=1500.,interface_aligned=bool(align_interface),initial_layer_volume_m2=float(fraction.sum()*dy*length),
        interface_mixed_row_count=int(np.count_nonzero((fraction>0)&(fraction<1))),
        initial_conserved_per_m_depth=s.conserved_totals().tolist(),
        initial_excess_over_unignited_layer=(s.conserved_totals()-baseline).tolist())
    return s,x,(np.arange(ny)+.5)*dy,info


def row_front_metrics(w,x,c,roi=.03):
    """Pressure and reaction association in one row, without a detonation label."""
    p=w[3];T=p/(c['R']*w[0]);rate=c['k']*np.maximum(0,1-w[4])*np.exp(-c['Ea']/(c['R']*T))
    ii=np.flatnonzero(p>2*c['p1']);front=float(x[ii[-1]]) if ii.size else None
    region=(x>=front-roi)&(x<=front) if front is not None else np.zeros(x.size,dtype=bool)
    peak=int(np.argmax(np.where(region,rate,-1))) if region.any() else None
    ahead=(x>front+2*(x[1]-x[0]))&(x<front+roi) if front is not None else np.zeros(x.size,dtype=bool)
    reacted=np.flatnonzero(region&(w[4]>=.5))
    return dict(front_m=front,pressure_max_Pa=float(p.max()),
        rate_peak_m=float(x[peak]) if peak is not None else None,
        rate_peak_per_s=float(rate[peak]) if peak is not None else None,
        peak_progress=float(w[4,peak]) if peak is not None else None,
        front_rate_separation_m=float(front-x[peak]) if peak is not None else None,
        front_half_reaction_separation_m=float(front-x[reacted[-1]]) if reacted.size else None,
        upstream_u_mps=float(w[1,ahead].mean()) if ahead.any() else None,
        upstream_sound_mps=float(np.sqrt(c['gamma']*p[ahead]/w[0,ahead]).mean()) if ahead.any() else None,
        near_front_heat_W_per_m2=float(np.sum(c['q']*w[0,region]*rate[region])*(x[1]-x[0])))


def run_layer(c,directory,layer_height,dx=.5e-3,end=40e-6,profile=None,align_interface=False):
    """C3 finite-layer control; finite physical causal bounds and native budgets."""
    if not np.isfinite(end) or not 0<end<=40e-6:raise ValueError('0<end<=40 us required')
    profile=formed_profile(c) if profile is None else profile
    if max(profile['verification']['jump_max_relative_error'])>1e-8:raise ValueError('steady jump check failed')
    s,x,z,init=formed_layer(c,profile,layer_height,dx=dx,align_interface=align_interface)
    length=s.nx*s.dx;height=s.ny*s.dy;bx=4000.;bz=3000.;roi=.03
    # Bottom, middle and last completely fresh/profile row; full fields retain the interface.
    indexes=sorted(set([0,int(np.argmin(abs(z-layer_height/2))),max(0,int(layer_height/s.dy)-1)]))
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    _write_json(directory/'inputs.json',dict(kind='layer',calibration=c,end_s=end,source_cfl=.05,
        length_m=length,shock_initial_m=.16,axial_characteristic_bound_mps=bx,
        transverse_characteristic_bound_mps=bz,reaction_roi_behind_front_m=roi,
        diagnostic_row_indexes=indexes,diagnostic_row_z_m=z[indexes].tolist(),
        profile_verification=profile['verification'],initialization=init,
        implementation=_fingerprint(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policy='formed-wave propagation under hot products; exact conservative layer fractions; no injection or driver'))
    initial=s.conserved_totals();history=[];times=[];fields=[];status='completed';error=None
    rho1=c['p1']/(c['R']*c['T1']);volume=length*height
    scale=np.maximum(abs(initial),np.array([rho1,rho1*c['D_CJ'],rho1*c['D_CJ'],c['p1']/(c['gamma']-1)+rho1*c['q'],rho1])*volume)
    observed=np.zeros(2);started=time.monotonic();layer_rows=z<layer_height
    def save():
        w=s.prim().copy();rows=[row_front_metrics(w[:,:,j],x,c,roi) for j in indexes]
        T=w[3]/(c['R']*w[0]);rate=c['k']*np.maximum(0,1-w[4])*np.exp(-c['Ea']/(c['R']*T))
        heat=c['q']*w[0]*rate
        fronts=[row['front_m'] for row in rows if row['front_m'] is not None]
        budget=conservation_budget(s.conserved_totals(),initial,s.cumulative_boundary,s.cumulative_source,1.,1.)
        history.append(dict(time_s=s.t,rows=rows,pressure_max_Pa=float(w[3].max()),
            max_rate_per_s=float(rate.max()),total_heat_W_per_m_depth=float(heat.sum()*s.dx*s.dy),
            layer_heat_W_per_m_depth=float(heat[:,layer_rows].sum()*s.dx*s.dy),
            converted_J_per_m_depth=float(c['q']*s.cumulative_source[4]),
            budget_scaled_residual=float(np.max(abs(budget['residual'])/scale)),
            left_causal_margin_m=float(min(fronts)-roi-bx*s.t) if fronts else None,
            right_causal_margin_m=float(length-max(fronts)-bx*s.t) if fronts else None,
            top_causal_margin_m=float(height-layer_height-bz*s.t)))
        times.append(s.t);fields.append(w)
        _write_json(directory/'progress.json',dict(time_s=s.t,steps=s.steps,wall_seconds=time.monotonic()-started,
            observed_characteristic_max_mps=observed.tolist(),latest=history[-1]))
    save();tick=1
    from solver import NG
    try:
        while s.t<end:
            target=min(end,tick*4e-6);s.step(dt_max=target-s.t)
            from solver import max_speed
            observed=np.maximum(observed,max_speed(s.W,s.g))
            s.prim()
            observed=np.maximum(observed,max_speed(s.W,s.g))
            if observed[0]>bx or observed[1]>bz:raise RuntimeError('predeclared characteristic bound exceeded')
            if s.t>=target:
                save();tick+=1;h=history[-1]
                if h['left_causal_margin_m'] is None:raise RuntimeError('no tracked pressure front; inspect decay before continuing')
                if min(h['left_causal_margin_m'],h['right_causal_margin_m'],h['top_causal_margin_m'])<=0:
                    raise RuntimeError('remote-boundary causal cone reaches measurement region')
    except (InvalidStateError,RuntimeError) as caught:status='stopped';error=str(caught)
    if times[-1]!=s.t:save()
    summary=dict(kind='layer',status=status,error=error,time_s=s.t,steps=s.steps,wall_seconds=time.monotonic()-started,
        observed_characteristic_max_mps=observed.tolist(),invalid_state_count=s.invalid_state_count,
        initialization=init,initial_conserved_per_m_depth=initial.tolist(),
        final_conserved_per_m_depth=s.conserved_totals().tolist(),
        cumulative_boundary=s.cumulative_boundary.tolist(),cumulative_source=s.cumulative_source.tolist(),
        max_budget_scaled_residual=max(h['budget_scaled_residual'] for h in history),history=history,
        interpretation='bounded response only: combine spatial pressure/reaction association, relief, causality and mesh evidence')
    _write_npz(directory/'fields.npz',x=x,z=z,times=np.array(times),primitive=np.array(fields))
    _write_json(directory/'summary.json',summary)
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment',choices=['strip','formed','layer'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--calibration',type=Path,default=Path(__file__).with_name('calib.json'))
    parser.add_argument('--dx-mm',type=float,default=.5)
    parser.add_argument('--source-cfl',type=float,default=.05)
    parser.add_argument('--height-mm',type=float)
    parser.add_argument('--align-interface',action='store_true')
    args=parser.parse_args(argv)
    c=json.loads(args.calibration.read_text())
    if args.align_interface and args.experiment!='layer':parser.error('--align-interface requires layer')
    if args.experiment=='strip':
        if args.source_cfl!=.05:parser.error('strip fixes source-cfl=0.05')
        result=run_strip(c,args.out,dx=args.dx_mm*1e-3)
    elif args.experiment=='formed':result=run_formed(c,args.out,dx=args.dx_mm*1e-3,source_cfl=args.source_cfl)
    else:
        if args.height_mm is None or args.source_cfl!=.05:parser.error('layer needs --height-mm and fixes source-cfl=0.05')
        result=run_layer(c,args.out,args.height_mm*1e-3,dx=args.dx_mm*1e-3,align_interface=args.align_interface)
    print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2))
    return 0 if result.get('control_passed',result['status']=='completed') else 2


if __name__=='__main__':
    raise SystemExit(main())
