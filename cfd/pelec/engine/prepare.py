"""Finite directional launch for a premixed unwrapped engine preview."""

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def prepare(reference, mechanism, case_id, out, nx=512, ny=192, uniform=False):
    import cantera as ct

    catalog = json.loads((Path(__file__).parent / "cases.json").read_text())
    case = next(c for c in catalog["cases"] if c["id"] == case_id)
    common = catalog["common_assumptions"]
    ref = json.loads((reference / "reference.json").read_text())
    z = np.load(reference / "znd.npz")
    gas = ct.Solution(str(mechanism))
    if hashlib.sha256(mechanism.read_bytes()).hexdigest() != ref["mechanism_sha256"]:
        raise ValueError("Reference mechanism mismatch")
    if nx < 32 or ny < 8 or nx % 8 or ny % 8:
        raise ValueError("Grid must be positive multiples of eight")
    length = np.pi * (case["outer_diameter_m"] - case["gap_m"])
    dx = length / nx
    dy = case["length_m"] / ny
    D = ref["CJ"]["CJ_speed_mps"]
    shock = min(0.03, length / 4)
    distance = z["distance_m"].copy()
    rows = []
    for rho, T, y, u in zip(
        z["density_kg_m3"], z["temperature_K"], z["species_Y"].T, D - z["velocity_mps"]
    ):
        gas.TDY = T, rho, y
        rows.append(
            np.r_[rho, rho * u, rho * (gas.int_energy_mass + 0.5 * u * u), rho * gas.Y]
        )
    rows = np.array(rows)
    c = ref["CJ"]["CJ"]
    gas.TPY = c["T"], c["p"], c["Y"]
    u = D * (1 - ref["CJ"]["initial"]["rho"] / gas.density)
    tail = np.r_[
        gas.density,
        gas.density * u,
        gas.density * (gas.int_energy_mass + 0.5 * u * u),
        gas.density * gas.Y,
    ]
    if distance[-1] < shock:
        distance = np.r_[distance, shock]
        rows = np.vstack([rows, tail])
    h = np.diff(distance)
    slopes = np.diff(rows, axis=0) / h[:, None]
    prefix = np.vstack(
        [
            np.zeros(rows.shape[1]),
            np.cumsum(0.5 * (rows[:-1] + rows[1:]) * h[:, None], axis=0),
        ]
    )

    def integral(x):
        k = np.clip(
            np.searchsorted(distance, x, side="right") - 1, 0, len(distance) - 2
        )
        d = x - distance[k]
        return prefix[k] + rows[k] * d[:, None] + 0.5 * slopes[k] * d[:, None] ** 2

    gas.TPY = 300.0, ref["CJ"]["pressure_Pa"], ref["CJ"]["initial"]["Y"]
    freshY = gas.Y.copy()
    R = ct.gas_constant / gas.mean_molecular_weight
    gamma = gas.cp_mass / gas.cv_mass
    fresh = np.r_[
        gas.density, 0.0, gas.density * gas.int_energy_mass, gas.density * freshY
    ]
    lo = np.arange(nx) * dx
    hi = lo + dx
    table = (
        integral(np.maximum(shock - lo, 0))
        - integral(np.maximum(shock - hi, 0))
        + np.maximum(hi - np.maximum(lo, shock), 0)[:, None] * fresh
    ) / dx
    # Only floating-point noise is permitted at reference species zeros.
    if table[:, 3:].min() < -1e-12:
        raise ValueError("Invalid reference species")
    table[:, 3:] = np.maximum(table[:, 3:], 0.0)
    table[:, 0] *= 0.001
    table[:, 1] *= 0.1
    table[:, 2] *= 10
    table[:, 3:] *= 0.001
    if uniform:
        bgT = 300.0
        pback = ref["CJ"]["pressure_Pa"]
        bgY = freshY.copy()
        p0 = pback
    else:
        bgT = 1500.0
        pback = common["back_pressure_Pa"]
        p0 = common["equivalent_plenum_Pa"]
        gas.TPY = bgT, pback, freshY
        gas.equilibrate("TP")
        bgY = gas.Y.copy()
    coeff = [
        [
            gas.n_atoms(k, e) * gas.atomic_weights[e] / gas.molecular_weights[k]
            for e in range(gas.n_elements)
        ]
        for k in range(gas.n_species)
    ]
    out.mkdir(parents=True, exist_ok=False)
    profile = out / "profile.dat"
    np.savetxt(
        profile,
        table,
        fmt="%.17e",
        header=f"{nx} {table.shape[1]} {dx * 100:.17e}",
        comments="",
    )
    data = dict(
        case,
        **dict(
            nx=nx,
            ny=ny,
            circumference_m=length,
            dx_m=dx,
            dy_m=dy,
            final_time_s=1e-3,
            plot_interval_s=5e-6,
            fill_m=0.0038,
            launch_length_m=shock,
            p0_Pa=p0,
            T0_K=300.0,
            pback_Pa=pback,
            area_ratio_effective=case["opening_area_ratio"] * 0.76,
            freshY=freshY.tolist(),
            bgY=bgY.tolist(),
            bg_T=bgT,
            R_JkgK=R,
            gamma=gamma,
            species=gas.species_names,
            element_weights=np.array(coeff).ravel().tolist(),
            elements=(freshY @ np.array(coeff)).tolist(),
            uniform_control=uniform,
            profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),
            mechanism_sha256=ref["mechanism_sha256"],
            interpretation="Exploratory premixed 2D engine; finite formed wave, no forced rotation. No resolved radial motion or discrete impinging jets. Mesh/mechanism/engine validation remains separate.",
        ),
    )
    (out / "case.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("reference", type=Path)
    p.add_argument("mechanism", type=Path)
    p.add_argument("case_id")
    p.add_argument("output", type=Path)
    p.add_argument("--nx", type=int, default=512)
    p.add_argument("--ny", type=int, default=192)
    p.add_argument("--uniform", action="store_true")
    a = p.parse_args()
    prepare(a.reference, a.mechanism, a.case_id, a.output, a.nx, a.ny, a.uniform)
