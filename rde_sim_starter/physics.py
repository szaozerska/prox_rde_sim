"""Constant-gamma reactive Euler physics used by the starter.

Total energy includes unspent chemical energy rho*q*(1-xi). Reaction changes
rho*xi, with no additional total-energy source. No clipping or state repair.
The injector is the inherited equivalent premixed, no-backflow model; its
physical reduction and momentum convention still require separate validation.
"""
import numpy as np
from numba import njit


@njit(cache=True, inline="always")
def total_energy(rho, u, v, pressure, progress, gamma, q):
    return pressure / (gamma - 1.0) + 0.5 * rho * (u*u + v*v) + rho*q*(1.0-progress)


@njit(cache=True, inline="always")
def reaction_rate(progress, temperature, R, k, Ea):
    """One-step progress rate [1/s]; caller supplies a valid physical state."""
    return k * (1.0 - progress) * np.exp(-Ea / (R * temperature))


@njit(cache=True)
def state_error(U, gamma, q, ng, rho_min, p_min):
    """First invalid interior cell: (code, i, j, component, value).

    Codes: 1 nonfinite conserved value, 2 density, 3 progress, 4 pressure.
    Ghost storage is intentionally excluded. Indices include the ghost offset.
    """
    for i in range(ng, U.shape[1] - ng):
        for j in range(ng, U.shape[2] - ng):
            for component in range(5):
                if not np.isfinite(U[component, i, j]):
                    return 1, i, j, component, U[component, i, j]
            rho = U[0, i, j]
            if rho <= 0.0 or rho < rho_min:
                return 2, i, j, 0, rho
            xi = U[4, i, j] / rho
            if not np.isfinite(xi) or xi < 0.0 or xi > 1.0:
                return 3, i, j, 4, xi
            u, v = U[1, i, j] / rho, U[2, i, j] / rho
            pressure = (gamma-1.0) * (U[3, i, j] - 0.5*rho*(u*u+v*v) - rho*q*(1.0-xi))
            if not np.isfinite(pressure) or pressure <= 0.0 or pressure < p_min:
                return 4, i, j, 3, pressure
    return 0, -1, -1, -1, 0.0


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
def injector_flux(pw, p0, T0, R, g, q, sigma, Cd, F):
    """D24: micro-nozzle injector face flux (no backflow). Returns flux into the domain (+y)."""
    pcr = p0 * (2.0 / (g + 1.0)) ** (g / (g - 1.0))
    cp = g * R / (g - 1.0)
    if pw >= p0:                                     # blocked (region F, Fig. 1.10)
        F[0] = 0.0; F[1] = 0.0; F[2] = pw; F[3] = 0.0; F[4] = 0.0
        return 0.0
    if pw < pcr:                                     # choked (Eq. 2.1 form)
        G = Cd * p0 * np.sqrt(g / (R * T0)) * (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0)))
    else:                                            # subsonic orifice
        rr = pw / p0
        rho0 = p0 / (R * T0)
        G = Cd * np.sqrt(2.0 * g / (g - 1.0) * p0 * rho0 * (rr ** (2.0 / g) - rr ** ((g + 1.0) / g)))
    uj = np.sqrt(max(2.0 * cp * T0 * (1.0 - (pw / p0) ** ((g - 1.0) / g)), 0.0))
    m = sigma * G
    F[0] = m; F[1] = 0.0; F[2] = m * uj + pw; F[3] = m * (cp * T0 + q); F[4] = 0.0
    return m
