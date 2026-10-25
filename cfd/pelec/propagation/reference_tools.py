"""Existing CJ procedure generalized to an explicitly selected mechanism."""

import numpy as np
from scipy.optimize import minimize_scalar
from reference import _state, jump_residuals


def _cj(
    ct,
    post,
    thermo,
    pressure,
    temperature,
    phi,
    tolerance=1e-8,
    minimum_tolerance=1e-7,
    mechanism=None,
):
    if (
        not np.isfinite([pressure, temperature, phi]).all()
        or min(pressure, temperature, phi) <= 0
    ):
        raise ValueError(
            "positive finite pressure, temperature and equivalence ratio required"
        )
    composition = {"CH4": float(phi), "O2": 2.0}
    initial = ct.Solution(mechanism, transport_model=None)
    initial.TPX = temperature, pressure, composition
    work = ct.Solution(mechanism, transport_model=None)

    def evaluate(ratio):
        work.TPX = temperature, pressure, composition
        result = post.CJ_calc(work, initial, tolerance, tolerance, ratio)
        if result is None or not np.isfinite(result[1]) or result[1] <= 0:
            raise RuntimeError("SDToolbox CJ_calc did not converge")
        return float(result[1])

    bounds = (1.3, 2.5)
    result = minimize_scalar(
        evaluate,
        bounds=bounds,
        method="bounded",
        options={"xatol": minimum_tolerance, "maxiter": 60},
    )
    if not result.success or min(result.x - bounds[0], bounds[1] - result.x) < 0.01:
        raise RuntimeError(
            "CJ speed minimum was not found inside the documented density-ratio bracket"
        )
    speed = evaluate(result.x)
    cj = _state(work)
    residuals = jump_residuals(_state(initial), cj, speed)
    if max(abs(v) for v in residuals.values()) > 1e-6:
        raise RuntimeError(f"CJ jump residuals exceed tolerance: {residuals}")
    elements_initial = np.array(
        [initial.elemental_mass_fraction(e) for e in initial.element_names]
    )
    elements_cj = np.array(
        [work.elemental_mass_fraction(e) for e in work.element_names]
    )
    element_error = float(np.max(np.abs(elements_initial - elements_cj)))
    equilibrium_sound = float(thermo.soundspeed_eq(work))
    sonic_ratio = speed * initial.density / cj["rho"] / equilibrium_sound
    if element_error > 1e-8 or abs(sonic_ratio - 1) > 5e-3:
        raise RuntimeError("CJ element conservation or equilibrium sonic check failed")
    species_Y = np.array(cj["Y"])
    work.TP = 298.15, ct.one_atm
    formation_enthalpies = (
        work.standard_enthalpies_RT * ct.gas_constant * work.T / work.molecular_weights
    )
    q = float(np.dot(initial.Y - species_Y, formation_enthalpies))
    if q <= 0:
        raise RuntimeError("expected positive CJ equilibrium heat release")
    work.TPX = temperature, pressure, composition
    frozen = post.shk_calc(speed, work, initial, tolerance, tolerance)
    vn = _state(frozen)
    vn["u_shock_frame"] = speed * initial.density / vn["rho"]
    vn_residuals = jump_residuals(_state(initial), vn, speed)
    if max(abs(v) for v in vn_residuals.values()) > 1e-6:
        raise RuntimeError(f"frozen shock residuals exceed tolerance: {vn_residuals}")
    return (
        dict(
            pressure_Pa=pressure,
            temperature_K=temperature,
            phi=phi,
            CJ_speed_mps=speed,
            CJ=cj,
            VN=vn,
            q_equilibrium_Jkg=q,
            initial=_state(initial),
            density_ratio=float(result.x),
            jump_relative_residuals=residuals,
            frozen_jump_relative_residuals=vn_residuals,
            CJ_equilibrium_sonic_ratio=float(sonic_ratio),
            element_mass_fraction_error=element_error,
            minimum_evaluations=int(result.nfev),
            tolerance=tolerance,
            minimum_tolerance=minimum_tolerance,
        ),
        initial,
        frozen,
        formation_enthalpies,
    )
