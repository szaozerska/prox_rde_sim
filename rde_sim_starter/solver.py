"""2D reacting Euler solver for the unrolled RDE (plan D16-D24, D26).

Finite volume on a uniform grid, MUSCL-minmod on primitives, HLL flux, SSP-RK2,
one-step Arrhenius reaction (Mundt Eq. 1.11) with chemical energy stored in E.

Arrays: U[var, i, j] with NG ghost cells. Variables: rho, rho*u, rho*v, E, rho*xi.
x (index i) = around the circumference, y (index j) = along the axis.
"""
import numpy as np
from numba import njit, prange
from physics import cons_to_prim, prim_to_cons_cell, injector_flux, reaction_rate, state_error, total_energy

NG = 2
# boundary codes
PERIODIC, REFLECT, TRANSMIT = 0, 1, 2          # x-ends (left / right)
WALL, INJECTOR, OUTFLOW = 0, 1, 2              # y-ends (bottom / top)


@njit(cache=True, inline="always")
def minmod(a, b):
    if a * b <= 0.0:
        return 0.0
    return a if abs(a) < abs(b) else b


@njit(cache=True)
def fill_ghosts(W, bcl, bcr, bcb, bct, p_back, g):
    """Ghost cells on primitives. The injector face is handled as a flux, but its ghosts
    get a zero-gradient copy so the MUSCL slopes next to it are defined."""
    nxg, nyg = W.shape[1], W.shape[2]
    nx, ny = nxg - 2 * NG, nyg - 2 * NG
    for j in range(nyg):
        for k in range(NG):
            for v in range(5):
                if bcl == PERIODIC:
                    W[v, k, j] = W[v, nx + k, j]
                    W[v, nx + NG + k, j] = W[v, NG + k, j]
                else:
                    W[v, NG - 1 - k, j] = W[v, NG + k, j] if bcl == REFLECT else W[v, NG, j]
                    W[v, nx + NG + k, j] = W[v, nx + NG - 1 - k, j] if bcr == REFLECT else W[v, nx + NG - 1, j]
            if bcl == REFLECT:
                W[1, NG - 1 - k, j] = -W[1, NG + k, j]
            if bcr == REFLECT and bcl != PERIODIC:
                W[1, nx + NG + k, j] = -W[1, nx + NG - 1 - k, j]
    for i in range(nxg):
        for k in range(NG):
            for v in range(5):
                W[v, i, NG - 1 - k] = W[v, i, NG + min(k, ny - 1)] if bcb == WALL else W[v, i, NG]
                W[v, i, ny + NG + k] = W[v, i, ny + NG - 1 - min(k, ny - 1)] if bct == WALL else W[v, i, ny + NG - 1]
            if bcb == WALL:
                W[2, i, NG - 1 - k] = -W[2, i, NG + min(k, ny - 1)]
            if bct == WALL:
                W[2, i, ny + NG + k] = -W[2, i, ny + NG - 1 - min(k, ny - 1)]
            elif bct == OUTFLOW:
                # D26: subsonic outflow -> impose back pressure; supersonic -> extrapolate
                r = W[0, i, ny + NG - 1]; vv = W[2, i, ny + NG - 1]; pp = W[3, i, ny + NG - 1]
                a = np.sqrt(g * max(pp, 1e-9) / r)
                if vv < a:
                    W[3, i, ny + NG + k] = p_back


@njit(cache=True, inline="always")
def hll(rL, uL, vL, pL, xL, rR, uR, vR, pR, xR, nxd, g, q, F):
    """HLL flux normal to a face. nxd=1: x-face (normal velocity u), nxd=0: y-face (v)."""
    unL = uL if nxd == 1 else vL
    unR = uR if nxd == 1 else vR
    aL = np.sqrt(g * pL / rL); aR = np.sqrt(g * pR / rR)
    EL = total_energy(rL, uL, vL, pL, xL, g, q)
    ER = total_energy(rR, uR, vR, pR, xR, g, q)
    sL = min(unL - aL, unR - aR)
    sR = max(unL + aL, unR + aR)
    # physical fluxes
    fL0 = rL * unL; fR0 = rR * unR
    fL1 = rL * uL * unL; fR1 = rR * uR * unR
    fL2 = rL * vL * unL; fR2 = rR * vR * unR
    if nxd == 1:
        fL1 += pL; fR1 += pR
    else:
        fL2 += pL; fR2 += pR
    fL3 = (EL + pL) * unL; fR3 = (ER + pR) * unR
    fL4 = rL * xL * unL; fR4 = rR * xR * unR
    if sL >= 0.0:
        F[0] = fL0; F[1] = fL1; F[2] = fL2; F[3] = fL3; F[4] = fL4
    elif sR <= 0.0:
        F[0] = fR0; F[1] = fR1; F[2] = fR2; F[3] = fR3; F[4] = fR4
    else:
        inv = 1.0 / (sR - sL)
        F[0] = (sR * fL0 - sL * fR0 + sL * sR * (rR - rL)) * inv
        F[1] = (sR * fL1 - sL * fR1 + sL * sR * (rR * uR - rL * uL)) * inv
        F[2] = (sR * fL2 - sL * fR2 + sL * sR * (rR * vR - rL * vL)) * inv
        F[3] = (sR * fL3 - sL * fR3 + sL * sR * (ER - EL)) * inv
        F[4] = (sR * fL4 - sL * fR4 + sL * sR * (rR * xR - rL * xL)) * inv


@njit(cache=True, parallel=True)
def rhs(W, dUdt, Fb, dx, dy, g, q, R, k, Ea, bcb, inj):
    """Spatial operator + reaction source. inj = (p0, T0, sigma, Cd). Fb stores the bottom
    face flux per column (for diagnostics)."""
    nxg, nyg = W.shape[1], W.shape[2]
    nx, ny = nxg - 2 * NG, nyg - 2 * NG
    for i in prange(NG, nx + NG):
        F = np.empty(5); Fm = np.empty(5); Gp = np.empty(5); Gm = np.empty(5)
        L = np.empty(5); Rr = np.empty(5)
        for j in range(NG, ny + NG):
            # x-faces i-1/2 and i+1/2
            for side in range(2):
                ia = i - 1 + side          # left cell of the face
                for v in range(5):
                    L[v] = W[v, ia, j] + 0.5 * minmod(W[v, ia, j] - W[v, ia - 1, j], W[v, ia + 1, j] - W[v, ia, j])
                    Rr[v] = W[v, ia + 1, j] - 0.5 * minmod(W[v, ia + 1, j] - W[v, ia, j], W[v, ia + 2, j] - W[v, ia + 1, j])
                if side == 0:
                    hll(L[0], L[1], L[2], L[3], L[4], Rr[0], Rr[1], Rr[2], Rr[3], Rr[4], 1, g, q, Fm)
                else:
                    hll(L[0], L[1], L[2], L[3], L[4], Rr[0], Rr[1], Rr[2], Rr[3], Rr[4], 1, g, q, F)
            # y-faces j-1/2 and j+1/2
            for side in range(2):
                ja = j - 1 + side
                if side == 0 and j == NG and bcb == INJECTOR:
                    Fb[i - NG] = injector_flux(W[3, i, NG], inj[0], inj[1], R, g, q, inj[2], inj[3], Gm)
                    continue
                for v in range(5):
                    L[v] = W[v, i, ja] + 0.5 * minmod(W[v, i, ja] - W[v, i, ja - 1], W[v, i, ja + 1] - W[v, i, ja])
                    Rr[v] = W[v, i, ja + 1] - 0.5 * minmod(W[v, i, ja + 1] - W[v, i, ja], W[v, i, ja + 2] - W[v, i, ja + 1])
                if side == 0:
                    hll(L[0], L[1], L[2], L[3], L[4], Rr[0], Rr[1], Rr[2], Rr[3], Rr[4], 0, g, q, Gm)
                else:
                    hll(L[0], L[1], L[2], L[3], L[4], Rr[0], Rr[1], Rr[2], Rr[3], Rr[4], 0, g, q, Gp)
            for v in range(5):
                dUdt[v, i, j] = -(F[v] - Fm[v]) / dx - (Gp[v] - Gm[v]) / dy
            # D12: one-step reaction source on rho*xi (Eq. 1.11)
            r = W[0, i, j]; xi = W[4, i, j]
            T = W[3, i, j] / (r * R)
            dUdt[4, i, j] += r * reaction_rate(xi, T, R, k, Ea)


@njit(cache=True, parallel=True)
def max_speed(W, g):
    nxg, nyg = W.shape[1], W.shape[2]
    sx = np.zeros(nxg); sy = np.zeros(nxg)
    for i in prange(NG, nxg - NG):
        for j in range(NG, nyg - NG):
            a = np.sqrt(g * W[3, i, j] / W[0, i, j])
            sx[i] = max(sx[i], abs(W[1, i, j]) + a)
            sy[i] = max(sy[i], abs(W[2, i, j]) + a)
    return sx.max(), sy.max()


class InvalidStateError(ValueError):
    """A rejected state, with the stage and offending interior cell recorded."""

    def __init__(self, stage, reason, cell, component, value):
        self.stage, self.reason, self.cell = stage, reason, cell
        self.component, self.value = component, float(value)
        super().__init__(f"{stage}: {reason} at cell {cell}, component {component}: {value!r}")


class Solver:
    def __init__(self, nx, ny, dx, dy, gas, bc, inj=(0.0, 300.0, 0.0, 1.0), p_back=1e5, cfl=0.4):
        if not isinstance(nx, (int, np.integer)) or not isinstance(ny, (int, np.integer)) or nx < NG or ny < 1:
            raise ValueError("nx must be an integer >= 2 and ny an integer >= 1")
        if not np.all(np.isfinite([dx, dy, p_back, cfl])) or dx <= 0 or dy <= 0 or p_back <= 0 or not 0 < cfl <= 1:
            raise ValueError("positive finite spacing/back pressure and 0 < CFL <= 1 required")
        if len(gas) != 5 or not np.all(np.isfinite(gas)):
            raise ValueError("gas must contain finite gamma, q, R, k, Ea")
        self.g, self.q, self.R, self.k, self.Ea = gas
        if self.g <= 1 or self.R <= 0 or min(self.q, self.k, self.Ea) < 0:
            raise ValueError("gamma > 1, R > 0, and nonnegative q/k/Ea required")
        if len(bc) != 4 or any(b not in (PERIODIC, REFLECT, TRANSMIT) for b in bc[:2]) or bc[2] not in (WALL, INJECTOR, OUTFLOW) or bc[3] not in (WALL, OUTFLOW):
            raise ValueError("unsupported boundary codes")
        if (bc[0] == PERIODIC) != (bc[1] == PERIODIC):
            raise ValueError("periodic x boundaries must be paired")
        if len(inj) != 4 or not np.all(np.isfinite(inj)) or inj[0] < 0 or inj[1] <= 0 or not 0 <= inj[2] <= 1 or inj[3] < 0:
            raise ValueError("invalid injector p0, T0, area ratio or discharge coefficient")
        if bc[2] == INJECTOR and inj[0] <= 0:
            raise ValueError("an injector needs positive plenum pressure")
        self.nx, self.ny, self.dx, self.dy = nx, ny, dx, dy
        self.bc, self.inj = tuple(bc), np.array(inj, dtype=np.float64)
        self.p_back, self.cfl = p_back, cfl
        shape = (5, nx + 2 * NG, ny + 2 * NG)
        self.U = np.zeros(shape); self.W = np.zeros(shape)
        self.k1 = np.zeros(shape); self.U1 = np.zeros(shape)
        self.Fb = np.zeros(nx)
        self.rho_min, self.p_min = 1e-6, 1.0
        # Compatibility field for the legacy runner: repairs are now disabled.
        self.floor_hits = 0
        self.invalid_state_count = 0
        self.last_failure = None
        self.t = 0.0

    def _check_state(self, U, stage):
        if not np.all(np.isfinite([self.rho_min, self.p_min])) or min(self.rho_min, self.p_min) < 0:
            raise ValueError("state thresholds must be finite and nonnegative")
        code, i, j, component, value = state_error(U, self.g, self.q, NG, self.rho_min, self.p_min)
        if code:
            reason = {1: "nonfinite conserved value", 2: "invalid density", 3: "progress outside [0, 1]", 4: "invalid pressure"}[code]
            error = InvalidStateError(stage, reason, (i-NG, j-NG), component, value)
            self.invalid_state_count += 1
            self.last_failure = dict(stage=stage, reason=reason, cell=[i-NG, j-NG], component=component, value=float(value), time=self.t)
            raise error

    def set_prim(self, r, u, v, p, xi):
        """Set finite physical primitives (scalars or arrays broadcastable to nx,ny).

        Failed initialization leaves the previous accepted conserved state intact.
        Set nondimensional validity thresholds before calling this method.
        """
        values = [np.broadcast_to(np.asarray(a, dtype=float), (self.nx, self.ny)) for a in (r,u,v,p,xi)]
        for component, a in enumerate(values):
            bad = ~np.isfinite(a)
            if component == 0:
                bad |= (a <= 0) | (a < self.rho_min)
            elif component == 3:
                bad |= (a <= 0) | (a < self.p_min)
            elif component == 4:
                bad |= (a < 0) | (a > 1)
            if np.any(bad):
                i,j = np.argwhere(bad)[0]
                self.invalid_state_count += 1
                self.last_failure = dict(stage="initialization", reason="invalid primitive", cell=[int(i),int(j)], component=component, value=float(a[i,j]), time=self.t)
                raise InvalidStateError("initialization", "invalid primitive", (int(i),int(j)), component, a[i,j])
        r,u,v,p,xi = values
        interior = (slice(NG,-NG), slice(NG,-NG))
        self.U1[0][interior] = r
        self.U1[1][interior] = r*u
        self.U1[2][interior] = r*v
        self.U1[3][interior] = total_energy(r,u,v,p,xi,self.g,self.q)
        self.U1[4][interior] = r*xi
        self._check_state(self.U1, "initialization")
        self.U[:] = self.U1

    def _L(self, U, out, stage):
        self._check_state(U, stage)
        cons_to_prim(U, self.W, self.g, self.q, NG)
        fill_ghosts(self.W, *self.bc, self.p_back, self.g)
        rhs(self.W, out, self.Fb, self.dx, self.dy, self.g, self.q, self.R, self.k, self.Ea,
            self.bc[2], self.inj)

    def step(self, dt_max=None):
        """One SSP-RK2 step; invalid stages are rejected without advancing U or t.

        dt_max caps the step for exact test end times. General reactive-source
        accuracy control remains follow-on work; flow CFL alone is not enough.
        """
        if dt_max is not None and (not np.isfinite(dt_max) or dt_max <= 0):
            raise ValueError("dt_max must be finite and positive")
        self._L(self.U, self.k1, "step input")
        sx, sy = max_speed(self.W, self.g)
        dt = self.cfl / (sx / self.dx + sy / self.dy)
        if dt_max is not None:
            dt = min(dt, dt_max)
        if not np.isfinite(dt) or dt <= 0 or self.t + dt == self.t:
            raise ValueError("time step must be finite, positive, and advance the clock")
        self.U1[:] = self.U + dt*self.k1
        self._L(self.U1, self.k1, "RK stage 1")
        self.U1[:] = 0.5*self.U + 0.5*(self.U1 + dt*self.k1)
        self._check_state(self.U1, "RK final")
        self.U[:] = self.U1
        self.t += dt
        return dt

    def prim(self):
        self._check_state(self.U, "primitive read")
        cons_to_prim(self.U, self.W, self.g, self.q, NG)
        return self.W[:, NG:-NG, NG:-NG]
