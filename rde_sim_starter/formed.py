"""Conservative formed-wave profiles and periodic engine initialization. No flow on import."""
import numpy as np


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


def periodic_charge_average(profile, edges, shock, charge, circumference):
    """Cell averages of one +theta finite charge, including cells crossing its seam.

    Signed distance behind the shock is periodic. [0, charge] contains the ZND
    profile and its burned tail; the remaining circumference is stationary fresh
    gas. The return from burned to fresh at `charge` is a physical startup jump.
    """
    edges=np.asarray(edges,dtype=float)
    if (edges.ndim!=1 or len(edges)<2 or not np.isfinite(edges).all()
            or not np.isfinite([shock,charge,circumference]).all()
            or not profile['distance'][-1] <= charge < circumference
            or np.any(np.diff(edges)<=0) or np.any(np.diff(edges)>circumference)):
        raise ValueError('ordered finite cells and tail <= charge < circumference required')
    widths=np.diff(edges)
    lo=np.mod(shock-edges[1:],circumference)
    hi=lo+widths
    def segment(a,b):
        a=np.minimum(a,circumference);b=np.minimum(b,circumference)
        inner_lo=np.minimum(a,charge);inner_hi=np.minimum(b,charge)
        active=inner_hi>inner_lo
        result=profile['fresh'][:,None]*(b-a)[None,:]
        result[:,active]+=(profile_cell_average(profile,inner_lo[active],inner_hi[active])
                          -profile['fresh'][:,None])*(inner_hi-inner_lo)[None,active]
        return result
    return (segment(lo,hi)+segment(np.zeros_like(lo),np.maximum(hi-circumference,0)))/widths


def initialize_engine(solver,resolved,c):
    """Assign conservative volume averages, not primitive averages or added heat."""
    from solver import NG
    init=resolved['initialization'];width=resolved['width'];length=resolved['length']
    height=float(init['fill_height_mm'])*1e-3
    charge=float(init['charge_length_mm'])*1e-3
    phase=float(init['shock_fraction']);temperature=float(init['product_temperature_K'])
    if (not np.isfinite([height,charge,phase,temperature]).all()
            or not 0<height<=length or not 0<=phase<1 or temperature<=0
            or init.get('u_theta',0)!=0 or init.get('u_z',0)!=0):
        raise ValueError('formed initialization needs valid height, phase, temperature and no velocity override')
    direction=init.get('direction','+theta')
    if direction not in ('+theta','-theta'):
        raise ValueError('formed direction must be +theta or -theta')
    sign=1 if direction=='+theta' else -1
    profile=formed_profile(c)
    if max(profile['verification']['jump_max_relative_error'])>1e-8:
        raise ValueError('formed profile jump invariants failed')
    edges=np.arange(solver.nx+1)*solver.dx
    profile_phase=phase if sign==1 else (1-phase)%1
    along=periodic_charge_average(profile,edges,profile_phase*width,charge,width)
    if sign==-1:
        along=along[:,::-1].copy()
        along[1]*=-1
    fraction=np.clip((height-np.arange(solver.ny)*solver.dy)/solver.dy,0.,1.)
    hot=conserved_state(c['p1']/(c['R']*temperature),0.,c['p1'],1.,c)
    solver.U[:,NG:-NG,NG:-NG]=(along[:,:,None]*fraction[None,None,:]
                                             +hot[:,None,None]*(1-fraction)[None,None,:])
    solver._check_state(solver.U,'formed engine initialization')
    # Independent whole-domain integral of the tabulated profile, then constants.
    integral=(profile['cumulative'][:,-1]+profile['burned']*(charge-profile['distance'][-1])
              +profile['fresh']*(width-charge))
    integral[1]*=sign
    expected=(height*integral+(length-height)*width*hot)*resolved['gap']
    baseline=(height*width*profile['fresh']+(length-height)*width*hot)*resolved['gap']
    actual=solver.conserved_totals()*resolved['gap']
    scales=np.maximum(abs(expected),np.array([1e-6,1e-3,1e-3,1.,1e-6]))
    error=float(np.max(abs(actual-expected)/scales))
    if not np.isfinite(error) or error>1e-10:
        raise ValueError('formed initialization inventory check failed')
    resolved['initialization_energy_change_J']=float(actual[3]-baseline[3])
    resolved['formed_initialization']=dict(profile=profile['verification'],
        shock_m=phase*width,charge_length_m=charge,layer_height_m=height,
        trailing_jump_m=(phase*width-sign*charge)%width,
        direction=direction, imposed_wave_speed_mps=sign*c['D_CJ'],
        lab_velocity='signed (D_CJ minus shock-frame velocity); zero axial velocity',
        initialization_excess_totals=(actual-baseline).tolist(),
        continuous_tangential_forcing=False,
        initial_totals=actual.tolist(),expected_totals=expected.tolist(),
        initial_unspent_chemical_energy_J=float(c['q']*(actual[0]-actual[4])),
        inventory_max_scaled_error=error,interface_mixed_rows=int(np.sum((fraction>0)&(fraction<1))),
        qualification='finite formed charge with burned-to-fresh trailing jump and hot-product layer contact; not a steady periodic solution or a physical pre-detonator')
