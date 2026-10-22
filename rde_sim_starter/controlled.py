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
from formed import conserved_state, formed_profile, profile_integral, profile_cell_average
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


def run_formed(c,directory,dx=.5e-3,end=40e-6,source_cfl=.05,profile=None,domain_scale=1.):
    """C2 fully filled propagation, with a predeclared 4000 m/s axial cone bound."""
    if not np.isfinite(end) or not 0<end<=40e-6:raise ValueError('0<end<=40 us required')
    if not np.isfinite(domain_scale) or not 0<domain_scale<=1 or end>40e-6*domain_scale:
        raise ValueError('domain scale in (0,1] and end<=40 us times scale required')
    profile=formed_profile(c) if profile is None else profile
    if max(profile['verification']['jump_max_relative_error'])>1e-8:raise ValueError('steady jump check failed')
    length=.45*domain_scale;shock=.16*domain_scale
    s,x=formed_strip(c,profile,dx=dx,length=length,shock=shock,source_cfl=source_cfl)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    bound=4000.;roi=.03*domain_scale
    _write_json(directory/'inputs.json',dict(kind='formed',calibration=c,dx_m=s.dx,
        rows=s.ny,length_m=length,shock_initial_m=shock,end_s=end,source_cfl=source_cfl,domain_scale=domain_scale,
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
            target=min(end,tick*2e-6*domain_scale);s.step(dt_max=target-s.t)
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
    for start in np.array((10e-6,20e-6,30e-6))*domain_scale:
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
        start='formed',product_temperature_K=1500.,interface_aligned=bool(align_interface),initial_layer_volume_m2=float(fraction.sum()*dy*length),
        interface_mixed_row_count=int(np.count_nonzero((fraction>0)&(fraction<1))),
        initial_conserved_per_m_depth=s.conserved_totals().tolist(),
        initial_excess_over_unignited_layer=(s.conserved_totals()-baseline).tolist())
    return s,x,(np.arange(ny)+.5)*dy,info


def blast_layer(c,profile,layer_height,dx=.5e-3,length=.45,shock=.16,buffer=.13,align_interface=False):
    """C4 comparator: original 10 mm hot patch and 20 mm product strip, at rest.

    Geometry is integrated conservatively. This intentionally differs in energy,
    momentum and reacted inventory from a formed wave; it is not an equal-energy
    or experimentally reconstructed pre-detonator.
    """
    if shock<.03:raise ValueError('blast and product strips must fit inside the domain')
    s,x,z,info=formed_layer(c,profile,layer_height,dx,length,shock,buffer,align_interface)
    fraction=(z<layer_height).astype(float) if align_interface else np.clip((layer_height-(z-s.dy/2))/s.dy,0,1)
    def overlap(left,right):
        return np.clip((np.minimum(x+s.dx/2,right)-np.maximum(x-s.dx/2,left))/s.dx,0,1)
    patch=overlap(shock-.01,shock);behind=overlap(shock-.03,shock-.01)
    hot=conserved_state(c['p1']/(c['R']*1500.),0.,c['p1'],1.,c)
    pressure=2*c['CJ']['p'];ignition=conserved_state(pressure/(c['R']*c['CJ']['T']),0.,pressure,1.,c)
    avg=profile['fresh'][:,None]+(hot-profile['fresh'])[:,None]*behind+(ignition-profile['fresh'])[:,None]*patch
    from solver import NG
    s.U[:,NG:-NG,NG:-NG]=avg[:,:,None]*fraction+hot[:,None,None]*(1-fraction)
    s._check_state(s.U,'conservative blast comparator initialization')
    baseline=(profile['fresh']*layer_height+hot*(s.ny*s.dy-layer_height))*length
    info.update(start='blast',patch_width_m=.01,products_behind_width_m=.02,
        patch_pressure_Pa=pressure,patch_temperature_K=c['CJ']['T'],initial_velocity_mps=[0.,0.],
        initial_conserved_per_m_depth=s.conserved_totals().tolist(),
        initial_excess_over_unignited_layer=(s.conserved_totals()-baseline).tolist())
    return s,x,z,info


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


def restore_layer(directory,c):
    """Restore a valid bounded layer run; legacy float64 fields are audited.

    New runs save exact conserved state. Older C3 runs require EOS inversion
    from float64 primitives; the inventory error is explicitly checked/reported.
    """
    from solver import NG
    from physics import total_energy
    directory=Path(directory);inp=json.loads((directory/'inputs.json').read_text())
    report=json.loads((directory/'summary.json').read_text())
    if (inp['kind']!='layer' or inp['calibration']!=c or report['invalid_state_count']
            or report['error'] not in (None,'predeclared characteristic bound exceeded')
            or inp['implementation']!=_fingerprint()):
        raise ValueError('continuation requires unchanged calibration/numerics and a valid layer state')
    with np.load(directory/'fields.npz',allow_pickle=False) as data:
        x=data['x'].copy();z=data['z'].copy();times=data['times'].copy();fields=data['primitive'].copy()
    if fields.dtype!=np.float64 or fields.shape!=(len(times),5,len(x),len(z)) or times[-1]!=report['time_s']:
        raise ValueError('complete float64 layer snapshots required')
    info=report['initialization'];dx=info['dx_m'];dy=info['dy_m']
    if not (np.allclose(x,(np.arange(len(x))+.5)*dx,rtol=0,atol=1e-13)
            and np.allclose(z,(np.arange(len(z))+.5)*dy,rtol=0,atol=1e-13)):
        raise ValueError('saved geometry does not match its coordinates')
    s=Solver(len(x),len(z),dx,dy,tuple(c[k] for k in ('gamma','q','R','k','Ea')),
             (TRANSMIT,TRANSMIT,WALL,WALL),source_cfl=inp['source_cfl'])
    state_path=directory/'state.npz'
    if state_path.exists():
        with np.load(state_path,allow_pickle=False) as a:
            if float(a['time_s'])!=report['time_s'] or int(a['steps'])!=report['steps']:
                raise ValueError('saved conserved state and report disagree')
            s.U[:,NG:-NG,NG:-NG]=a['conserved']
        storage='exact conserved state'
    else:
        rho,u,v,p,xi=fields[-1]
        s.U[:,NG:-NG,NG:-NG]=np.array([rho,rho*u,rho*v,total_energy(rho,u,v,p,xi,c['gamma'],c['q']),rho*xi])
        storage='legacy float64 primitives, conserved state reconstructed without clipping'
    s._check_state(s.U,'layer continuation')
    delta=s.conserved_totals()-np.asarray(report['final_conserved_per_m_depth'])
    scaled=float(np.max(abs(delta)/np.maximum(abs(np.asarray(report['final_conserved_per_m_depth'])),1e-12)))
    if scaled>1e-11:raise ValueError('continuation inventory differs from saved state')
    s.t=report['time_s'];s.steps=report['steps']
    s.cumulative_boundary[:]=report['cumulative_boundary'];s.cumulative_source[:]=report['cumulative_source']
    audit=dict(parent_directory=str(directory.resolve()),parent_inputs_sha256=hashlib.sha256((directory/'inputs.json').read_bytes()).hexdigest(),
        parent_fields_sha256=hashlib.sha256((directory/'fields.npz').read_bytes()).hexdigest(),
        state_storage=storage,inventory_difference=delta.tolist(),max_relative_inventory_difference=scaled,
        continued_from_time_s=s.t,continued_from_steps=s.steps)
    return s,x,z,inp,report,list(times),list(fields),audit


def run_layer(c,directory,layer_height,dx=.5e-3,end=40e-6,profile=None,align_interface=False,start='formed',resume=None,transverse_bound=None,domain_scale=1.):
    """C3 finite-layer control; finite physical causal bounds and native budgets."""
    if not np.isfinite(end) or not 0<end<=40e-6:raise ValueError('0<end<=40 us required')
    if not np.isfinite(domain_scale) or not 0<domain_scale<=1 or end>40e-6*domain_scale:
        raise ValueError('domain scale in (0,1] and end<=40 us times scale required')
    if start not in ('formed','blast'):raise ValueError('layer start must be formed or blast')
    if resume is None:
        profile=formed_profile(c) if profile is None else profile
        if max(profile['verification']['jump_max_relative_error'])>1e-8:raise ValueError('steady jump check failed')
    initialize=formed_layer if start=='formed' else blast_layer
    # The hotter blast can drive faster expansion: predeclare larger remote
    # margins rather than interpreting a violated travel bound as extinction.
    length,shock,buffer,bx,bz=((.45,.16,.13,4000.,3000.) if start=='formed'
                              else (.55,.20,.15,5000.,3500.))
    length*=domain_scale;shock*=domain_scale;buffer*=domain_scale
    if resume is None:
        s,x,z,init=initialize(c,profile,layer_height,dx=dx,length=length,shock=shock,
                             buffer=buffer,align_interface=align_interface)
        initial=s.conserved_totals();history=[];times=[];fields=[];observed=np.zeros(2);restart=None
        verification=profile['verification']
        indexes=sorted(set([0,int(np.argmin(abs(z-layer_height/2))),max(0,int(layer_height/s.dy)-1)]))
    else:
        s,x,z,old,previous,times,fields,restart=restore_layer(resume,c);init=previous['initialization']
        if domain_scale!=old.get('domain_scale',1.):raise ValueError('continuation must preserve domain scale')
        if (init.get('start','formed')!=start or init.get('interface_aligned',False)!=align_interface
                or init['layer_height_m']!=layer_height or not np.isclose(s.dx,dx,rtol=1e-12,atol=0) or end<=s.t):
            raise ValueError('continuation must preserve the case and extend its physical time')
        length=old['length_m'];shock=old['shock_initial_m'];bx=old['axial_characteristic_bound_mps'];bz=old['transverse_characteristic_bound_mps']
        initial=np.asarray(previous['initial_conserved_per_m_depth']);history=previous['history']
        observed=np.asarray(previous['observed_characteristic_max_mps']);verification=old['profile_verification']
        indexes=old['diagnostic_row_indexes']
    height=s.ny*s.dy;roi=.03*domain_scale
    if transverse_bound is not None:bz=float(transverse_bound)
    if not np.isfinite(bz) or bz<=0 or observed[0]>bx or observed[1]>bz or height-layer_height-bz*end<=0:
        raise ValueError('declared characteristic bounds must cover observed speeds and retain an endpoint top margin')
    for row in history:row['top_causal_margin_m']=height-layer_height-bz*row['time_s']
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    _write_json(directory/'inputs.json',dict(kind='layer',calibration=c,end_s=end,source_cfl=.05,domain_scale=domain_scale,
        length_m=length,shock_initial_m=shock,axial_characteristic_bound_mps=bx,
        transverse_characteristic_bound_mps=bz,reaction_roi_behind_front_m=roi,
        diagnostic_row_indexes=indexes,diagnostic_row_z_m=z[indexes].tolist(),
        profile_verification=verification,initialization=init,restart=restart,
        implementation=_fingerprint(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policy='layer propagation under hot products; explicit formed/blast start and conserved inventory; no injection or imposed driver'))
    status='completed';error=None
    rho1=c['p1']/(c['R']*c['T1']);volume=length*height
    scale=np.maximum(abs(initial),np.array([rho1,rho1*c['D_CJ'],rho1*c['D_CJ'],c['p1']/(c['gamma']-1)+rho1*c['q'],rho1])*volume)
    started=time.monotonic();layer_rows=z<layer_height
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
    if not history:save()
    tick=int(np.floor(s.t/(4e-6*domain_scale)))+1
    from solver import NG
    try:
        while s.t<end:
            target=min(end,tick*4e-6*domain_scale);s.step(dt_max=target-s.t)
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
    summary=dict(kind='layer',status=status,error=error,time_s=s.t,steps=s.steps,wall_seconds=time.monotonic()-started,restart=restart,
        observed_characteristic_max_mps=observed.tolist(),invalid_state_count=s.invalid_state_count,
        initialization=init,initial_conserved_per_m_depth=initial.tolist(),
        final_conserved_per_m_depth=s.conserved_totals().tolist(),
        cumulative_boundary=s.cumulative_boundary.tolist(),cumulative_source=s.cumulative_source.tolist(),
        max_budget_scaled_residual=max(h['budget_scaled_residual'] for h in history),history=history,
        interpretation='bounded response only: combine spatial pressure/reaction association, relief, causality and mesh evidence')
    _write_npz(directory/'state.npz',conserved=s.U[:,NG:-NG,NG:-NG],time_s=np.array(s.t),steps=np.array(s.steps))
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
    parser.add_argument('--start',choices=['formed','blast'],default='formed')
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--transverse-bound',type=float)
    args=parser.parse_args(argv)
    c=json.loads(args.calibration.read_text())
    if (args.align_interface or args.start!='formed' or args.resume or args.transverse_bound is not None) and args.experiment!='layer':parser.error('layer-specific options require layer')
    if args.experiment=='strip':
        if args.source_cfl!=.05:parser.error('strip fixes source-cfl=0.05')
        result=run_strip(c,args.out,dx=args.dx_mm*1e-3)
    elif args.experiment=='formed':result=run_formed(c,args.out,dx=args.dx_mm*1e-3,source_cfl=args.source_cfl)
    else:
        if args.height_mm is None or args.source_cfl!=.05:parser.error('layer needs --height-mm and fixes source-cfl=0.05')
        result=run_layer(c,args.out,args.height_mm*1e-3,dx=args.dx_mm*1e-3,align_interface=args.align_interface,start=args.start,resume=args.resume,transverse_bound=args.transverse_bound)
    print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2))
    return 0 if result.get('control_passed',result['status']=='completed') else 2


if __name__=='__main__':
    raise SystemExit(main())
