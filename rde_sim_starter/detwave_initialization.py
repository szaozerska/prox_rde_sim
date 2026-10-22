"""Investigation-only finite periodic ZND charge. Reuses verified C2 profiles."""
import numpy as np
from controlled import conserved_state, formed_profile, profile_cell_average


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
    profile=formed_profile(c)
    if max(profile['verification']['jump_max_relative_error'])>1e-8:
        raise ValueError('formed profile jump invariants failed')
    edges=np.arange(solver.nx+1)*solver.dx
    along=periodic_charge_average(profile,edges,phase*width,charge,width)
    fraction=np.clip((height-np.arange(solver.ny)*solver.dy)/solver.dy,0.,1.)
    hot=conserved_state(c['p1']/(c['R']*temperature),0.,c['p1'],1.,c)
    solver.U[:,NG:-NG,NG:-NG]=(along[:,:,None]*fraction[None,None,:]
                                             +hot[:,None,None]*(1-fraction)[None,None,:])
    solver._check_state(solver.U,'formed engine initialization')
    # Independent whole-domain integral of the tabulated profile, then constants.
    integral=(profile['cumulative'][:,-1]+profile['burned']*(charge-profile['distance'][-1])
              +profile['fresh']*(width-charge))
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
        trailing_jump_m=(phase*width-charge)%width,
        lab_velocity='D_CJ minus shock-frame velocity; positive theta; zero axial velocity',
        initial_totals=actual.tolist(),expected_totals=expected.tolist(),
        initial_unspent_chemical_energy_J=float(c['q']*(actual[0]-actual[4])),
        inventory_max_scaled_error=error,interface_mixed_rows=int(np.sum((fraction>0)&(fraction<1))),
        qualification='finite formed charge with burned-to-fresh trailing jump and hot-product layer contact; not a steady periodic solution or a physical pre-detonator')
