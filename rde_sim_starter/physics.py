"""Constant-gamma reactive Euler physics used by the starter.

Total energy includes unspent chemical energy rho*q*(1-xi). Reaction changes
rho*xi, with no additional total-energy source. No clipping or state repair. Progress checks allow only float64 roundoff.
The injector is an equivalent premixed, no-backflow converging opening. It uses
one consistent plane state and includes pressure on open and closed face areas.
Its reduction from separate experimental feeds remains a modeling assumption.
"""
import numpy as np
from numba import njit

# Dimensionless, about 1.42e-14: accepted values are never written back/clipped.
PROGRESS_TOL = 64 * np.finfo(np.float64).eps


@njit(cache=True, inline="always")
def total_energy(rho, u, v, pressure, progress, gamma, q):
    return pressure / (gamma - 1.0) + 0.5 * rho * (u*u + v*v) + rho*q*(1.0-progress)


@njit(cache=True, inline="always")
def reaction_rate(progress, temperature, R, k, Ea):
    """One-step progress rate [1/s]; caller supplies a valid physical state."""
    return k * np.maximum(0.0, 1.0 - progress) * np.exp(-Ea / (R * temperature))


@njit(cache=True)
def state_error(U, gamma, q, ng, rho_min, p_min):
    """First invalid cell plus maximum observed roundoff excursion.

    Returns (code, i, j, component, value, roundoff). Conserved data are unchanged.

    Codes: 1 nonfinite conserved value, 2 density, 3 progress, 4 pressure.
    Ghost storage is intentionally excluded. Indices include the ghost offset.
    """
    roundoff = 0.0
    for i in range(ng, U.shape[1] - ng):
        for j in range(ng, U.shape[2] - ng):
            for component in range(5):
                if not np.isfinite(U[component, i, j]):
                    return 1, i, j, component, U[component, i, j], roundoff
            rho = U[0, i, j]
            if rho <= 0.0 or rho < rho_min:
                return 2, i, j, 0, rho, roundoff
            xi = U[4, i, j] / rho
            if not np.isfinite(xi) or xi < -PROGRESS_TOL or xi > 1.0 + PROGRESS_TOL:
                return 3, i, j, 4, xi, roundoff
            roundoff = max(roundoff, -xi, xi - 1.0)
            u, v = U[1, i, j] / rho, U[2, i, j] / rho
            pressure = (gamma-1.0) * (U[3, i, j] - 0.5*rho*(u*u+v*v) - rho*q*(1.0-xi))
            if not np.isfinite(pressure) or pressure <= 0.0 or pressure < p_min:
                return 4, i, j, 3, pressure, roundoff
    return 0, -1, -1, -1, 0.0, roundoff


@njit(cache=True)
def cons_to_prim(U, W, gamma, q, ng=2):
    """Convert validated interior cells only; the solver fills primitive ghosts."""
    for i in range(ng, U.shape[1] - ng):
        for j in range(ng, U.shape[2] - ng):
            rho = U[0, i, j]
            u, v = U[1, i, j] / rho, U[2, i, j] / rho
            xi = U[4, i, j] / rho
            pressure = (gamma-1.0) * (U[3, i, j] - 0.5*rho*(u*u+v*v) - rho*q*(1.0-xi))
            W[0, i, j], W[1, i, j], W[2, i, j] = rho, u, v
            W[3, i, j], W[4, i, j] = pressure, xi


@njit(cache=True)
def prim_to_cons_cell(r, u, v, p, xi, g, q, out):
    out[0] = r; out[1] = r * u; out[2] = r * v
    out[3] = total_energy(r, u, v, p, xi, g, q)
    out[4] = r * xi


@njit(cache=True)
def injector_state(pw, p0, T0, R, g):
    """Ideal opening-plane p, T, normal speed; sonic at/below critical pressure.

    A converging opening cannot expand internally past Mach 1. Further jet
    expansion/mixing is unresolved by this equivalent premixed boundary.
    """
    pcr = p0 * (2.0 / (g + 1.0)) ** (g / (g - 1.0))
    if pw >= p0:
        return pw, T0, 0.0
    pj = max(pw, pcr)
    Tj = T0 * (pj / p0) ** ((g - 1.0) / g)
    uj = np.sqrt(2.0 * g * R / (g - 1.0) * (T0 - Tj))
    return pj, Tj, uj


@njit(cache=True)
def injector_flux(pw, p0, T0, R, g, q, sigma, Cd, F):
    """Effective opening flux into +z, averaged over the entire injector face.

    Cd scales transmitted mass/momentum/enthalpy. Pressure uses nominal open
    fraction sigma and chamber pressure on the remaining closed fraction.
    This is a declared effective closure, not a resolved jet or measured Cd fit.
    """
    cp = g * R / (g - 1.0)
    if pw >= p0:                                     # blocked (region F, Fig. 1.10)
        F[0] = 0.0; F[1] = 0.0; F[2] = pw; F[3] = 0.0; F[4] = 0.0
        return 0.0
    pj, Tj, uj = injector_state(pw, p0, T0, R, g)
    m = sigma * Cd * pj / (R * Tj) * uj
    F[0] = m; F[1] = 0.0; F[2] = m * uj + sigma*pj + (1-sigma)*pw
    F[3] = m * (cp * T0 + q); F[4] = 0.0
    return m


def source_step_limit(gamma, q, R, k, Ea, fraction):
    """Sufficient global source-resolution cap for the one-step model [s].

    At fixed density and total energy T=T0+A*(xi-xi0), A=(gamma-1)*q/R.
    f=(1-xi)*k*exp(-B/T), B=Ea/R. For 0<=xi<=1 and T>0,
    |df/dxi| <= k*(1+4*exp(-2)*A/B); maximize exp(-B/T)*B/T**2 at T=B/2.
    Ea=0 gives |df/dxi|=k exactly. This conservative bound covers heating
    and remaining-reactant depletion without retuning physical k/Ea/q.
    A time-step convergence check is still required; this is not an error estimator.
    None disables the cap only for explicit baseline/failure experiments.
    """
    if fraction is None or k == 0:
        return np.inf
    if not np.isfinite(fraction) or not 0 < fraction <= .25:
        raise ValueError('source_cfl must be in (0, 0.25], or None for an explicit baseline')
    gain = 0. if Ea == 0 else 4*np.exp(-2)*(gamma-1)*q/Ea*(1+PROGRESS_TOL)
    return fraction / (k*(1+gain))
