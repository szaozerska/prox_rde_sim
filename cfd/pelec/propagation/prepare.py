"""Independent finite ZND launch and initial states for the propagation gate."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "rde_sim_starter"))
from reference import _libraries, _znd  # noqa: E402
from reference_tools import _cj  # noqa: E402


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    p.add_argument("--mechanism", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    ct, post, znd, thermo, manifest = _libraries()
    mechanism = a.mechanism.resolve()
    ref, initial, working, hf = _cj(
        ct, post, thermo, 377916.972, 300.0, 1.176, mechanism=str(mechanism)
    )
    print("CJ speed", ref["CJ_speed_mps"], "temperature", ref["CJ"]["T"], flush=True)
    coarse, _ = _znd(ct, znd, thermo, ref, initial, working, hf, 1e-7, 1e-12, 1e-9)
    working.TDY = ref["VN"]["T"], ref["VN"]["rho"], ref["VN"]["Y"]
    strict, profile = _znd(
        ct, znd, thermo, ref, initial, working, hf, 2e-8, 1e-14, 5e-10
    )
    difference = abs(
        strict["heat_fraction_lengths_m"]["0.5"]
        / coarse["heat_fraction_lengths_m"]["0.5"]
        - 1
    )
    if difference > 0.005:
        raise ValueError("ZND reference refinement failed")
    np.savez_compressed(a.output / "znd.npz", **profile)
    gas = ct.Solution(str(mechanism))
    distance = profile["distance_m"]
    Y = profile["species_Y"]
    if Y.min() < -1e-12:
        raise ValueError("Negative reference species")
    cleaned = np.maximum(Y, 0)
    cleaned /= cleaned.sum(axis=0)
    if np.max(abs(cleaned - Y)) > 1e-10:
        raise ValueError("Excessive roundoff cleanup")
    D = ref["CJ_speed_mps"]
    rows = []
    for rho, T, y, u in zip(
        profile["density_kg_m3"],
        profile["temperature_K"],
        cleaned.T,
        D - profile["velocity_mps"],
    ):
        gas.TDY = T, rho, y
        rows.append(
            np.r_[rho, rho * u, rho * (gas.int_energy_mass + 0.5 * u * u), rho * y]
        )
    rows = np.array(rows)
    gas.TPY = 300.0, ref["pressure_Pa"], ref["initial"]["Y"]
    fresh = np.r_[
        gas.density, 0.0, gas.density * gas.int_energy_mass, gas.density * gas.Y
    ]
    # Two millimeters of causal left buffer. No extrapolation of a short reference:
    # constant CJ-equilibrium tail is explicitly appended beyond computed ZND.
    gas.TPY = ref["CJ"]["T"], ref["CJ"]["p"], ref["CJ"]["Y"]
    u = D * (1 - ref["initial"]["rho"] / gas.density)
    tail = np.r_[
        gas.density,
        gas.density * u,
        gas.density * (gas.int_energy_mass + 0.5 * u * u),
        gas.density * gas.Y,
    ]
    length = 0.004096
    shock = 0.002048
    if distance[-1] < shock:
        distance = np.r_[distance, shock]
        rows = np.vstack([rows, tail])
    widths = np.diff(distance)
    slopes = np.diff(rows, axis=0) / widths[:, None]
    prefix = np.vstack(
        [
            np.zeros(rows.shape[1]),
            np.cumsum(0.5 * (rows[:-1] + rows[1:]) * widths[:, None], axis=0),
        ]
    )

    def primitive(x):
        idx = np.clip(
            np.searchsorted(distance, x, side="right") - 1, 0, len(distance) - 2
        )
        delta = x - distance[idx]
        return (
            prefix[idx]
            + rows[idx] * delta[:, None]
            + 0.5 * slopes[idx] * delta[:, None] ** 2
        )

    save(
        a.output / "reference.json",
        dict(
            CJ=ref,
            ZND=strict,
            coarse_ZND=coarse,
            half_heat_refinement=difference,
            mechanism_sha256=hashlib.sha256(mechanism.read_bytes()).hexdigest(),
            species=gas.species_names,
            thermo_ranges={
                s.name: [s.thermo.min_temp, s.thermo.max_temp] for s in gas.species()
            },
            sdtoolbox=manifest,
        ),
    )
    for nx in (512, 1024, 2048, 4096):
        dx = length / nx
        lo = np.arange(nx) * dx
        hi = lo + dx
        table = (
            primitive(np.maximum(shock - lo, 0))
            - primitive(np.maximum(shock - hi, 0))
            + np.maximum(hi - np.maximum(lo, shock), 0)[:, None] * fresh
        ) / dx
        table[:, 0] *= 0.001
        table[:, 1] *= 0.1
        table[:, 2] *= 10
        table[:, 3:] *= 0.001
        path = a.output / f"profile_n{nx}.dat"
        np.savetxt(
            path,
            table,
            fmt="%.17e",
            header=f"{nx} {table.shape[1]} {dx * 100:.17e}",
            comments="",
        )
        save(
            a.output / f"case_n{nx}.json",
            dict(
                nx=nx,
                ny=8,
                dx_m=dx,
                length_m=length,
                shock_initial_m=shock,
                final_time_s=2e-7,
                plot_interval_s=1e-8,
                CJ_speed_mps=D,
                profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                mechanism="FFCM1_Red",
                scope="Planar gate, no continuing ignition or engine",
            ),
        )
    print("Reference and two conservative initial profiles ready", flush=True)


if __name__ == "__main__":
    main()
