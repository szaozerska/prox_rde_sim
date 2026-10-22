"""Opt-in gap-averaged annular wall closure; no evolved radial momentum.

Uniform T and velocity across the gap, quasi-steady radial force balance.
Coefficients and wall temperatures are assumptions supplied by the case, not fits.
"""
import math
import numpy as np
from numba import njit


def resolve_radial(model, ri, ro):
    """Strict SI closure contract. Reject ignored or misspelled physics options."""
    if model['walls'] != 'annular_closure':
        if 'radial' in model:
            raise ValueError('radial options require annular_closure walls')
        return None
    if model.get('wall_cf', 0.) != 0:
        raise ValueError('annular_closure uses separate inner/outer cf, not wall_cf')
    spec = model.get('radial', {})
    if not isinstance(spec,dict) or set(spec) != {'centrifugal', 'inner', 'outer', 'analogy_factor', 'recovery_factor'}:
        raise ValueError('radial requires centrifugal, inner, outer, analogy_factor, recovery_factor only')
    if type(spec['centrifugal']) is not bool:
        raise ValueError('centrifugal must be a boolean')
    def number(value, name, low, high=math.inf):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('invalid radial ' + name)
        return float(value)
    walls = []
    for name in ['inner', 'outer']:
        wall = spec[name]
        if not isinstance(wall, dict) or set(wall) != {'cf', 'temperature_K'}:
            raise ValueError(name + ' requires cf and temperature_K only')
        walls.extend([number(wall['cf'], name+' cf', 0),
                      number(wall['temperature_K'], name+' temperature_K', np.finfo(float).tiny)])
    return [ri, ro, float(spec['centrifugal']), *walls,
            number(spec['analogy_factor'], 'analogy_factor', 0),
            number(spec['recovery_factor'], 'recovery_factor', 0, 1)]


@njit(cache=True)
def pressure_ratios(beta, ri, ro):
    """Inner/outer p / volume-mean p for p(r) proportional to r**beta.

    Scaled exponential form avoids overflow; zero swirl returns exact unity.
    Underflow/nonfinite states are rejected, never clipped into a plausible wall.
    """
    if beta == 0.:
        return 1., 1.
    d = np.log(ro/ri)
    outer = .5*(beta+2.)*(-np.expm1(-2*d))/(-np.expm1(-(beta+2.)*d))
    inner = outer*np.exp(-beta*d)
    if not np.isfinite(inner+outer) or inner <= 0 or outer <= 0:
        raise ValueError('radial equilibrium cannot represent positive finite wall states')
    return inner, outer


@njit(cache=True)
def wall_pressures(W, params):
    """Reconstructed pressure on gas side of each wall, not a resolved wall field."""
    pi = np.empty(W.shape[1:]); po = np.empty_like(pi)
    for i in range(W.shape[1]):
        for j in range(W.shape[2]):
            beta = W[0,i,j]*W[1,i,j]**2/W[3,i,j] if params[2] else 0.
            a,b = pressure_ratios(beta, params[0], params[1])
            pi[i,j],po[i,j] = a*W[3,i,j],b*W[3,i,j]
    return pi,po


@njit(cache=True)
def annular_rhs(W, out, params, gamma, R, ng, cell_area):
    """Return per-wall integrated (theta, axial, E) RHS and a source rate cap.

    Integrals are per mean-radius radial depth, like the finite-volume solver.
    Area factors convert actual cylindrical wall areas to annulus volume.
    The cap resolves drag, thermal relaxation and cooling depletion; it is not an
    error estimator. RK stages still undergo strict physical-state checks.
    """
    ri,ro,centrifugal,cfi,Twi,cfo,Two,analogy,recovery = params
    area = np.array([2*ri/(ro*ro-ri*ri), 2*ro/(ro*ro-ri*ri)])
    cf = np.array([cfi,cfo]); Tw = np.array([Twi,Two])
    integrals = np.zeros((2,3)); rate_max = 0.
    cp = gamma*R/(gamma-1.)
    for i in range(ng,W.shape[1]-ng):
        for j in range(ng,W.shape[2]-ng):
            rho,u,v,p = W[0,i,j],W[1,i,j],W[2,i,j],W[3,i,j]
            speed = np.sqrt(u*u+v*v); T = p/(rho*R)
            beta = rho*u*u/p if centrifugal else 0.
            fi,fo = pressure_ratios(beta,ri,ro)
            drag_rate, heat_rate, cooling = 0.,0.,0.
            for w in range(2):
                rate = area[w]*(fi if w == 0 else fo)*.5*cf[w]*speed
                st_rate = rate*analogy
                theta,axial = -rho*rate*u,-rho*rate*v
                heat = -rho*st_rate*cp*(T+recovery*speed*speed/(2*cp)-Tw[w])
                out[1,i,j] += theta; out[2,i,j] += axial; out[3,i,j] += heat
                integrals[w,0] += theta*cell_area
                integrals[w,1] += axial*cell_area
                integrals[w,2] += heat*cell_area
                drag_rate += rate; heat_rate += gamma*st_rate
                cooling += max(-heat,0.)
            rate_max = max(rate_max,drag_rate,heat_rate,cooling/(p/(gamma-1.)))
    return integrals,rate_max
