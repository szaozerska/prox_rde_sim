"""Independent gate: every-step state validity, native EOS and wave motion."""

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path
import numpy as np


def crossing(x, v, threshold):
    hits = np.flatnonzero((v[:-1] >= threshold) & (v[1:] < threshold))
    if not len(hits):
        return None
    i = hits[-1]
    return float(x[i] + (threshold - v[i]) / (v[i + 1] - v[i]) * (x[i + 1] - x[i]))


def history_complete(hist, target, dt):
    expected = round(target / dt) + 1
    fields = {"density", "Temp", "pressure", "massfrac", "sumYminus1"}
    if set(hist) != fields:
        return False
    for values in hist.values():
        a = np.asarray(values)
        if len(a) != expected or not np.isfinite(a).all():
            return False
        if not np.allclose(a[:, 0], np.arange(expected) * dt, rtol=1e-7, atol=1e-18):
            return False
        if not np.all(np.diff(a[:, 0]) > 0):
            return False
    return True


def analyze(directory, reference, output):
    import cantera as ct
    import yt

    yt.set_log_level(40)
    status = json.loads((directory / "status.json").read_text())
    raw = directory / "native.tar.gz"
    if hashlib.sha256(raw.read_bytes()).hexdigest() != status["artifact_sha256"]:
        raise ValueError("Corrupt archive")
    native = directory / "native"
    if not native.exists():
        with tarfile.open(raw) as tar:
            for item in tar.getmembers():
                if (
                    not (native / item.name).resolve().is_relative_to(native.resolve())
                    or item.issym()
                    or item.islnk()
                ):
                    raise ValueError("Unsafe archive")
            tar.extractall(native, filter="data")
    run = native / "run"
    case = json.loads((run / "case.json").read_text())
    ref = json.loads(reference.read_text())
    cj = ref["CJ"]
    if (
        hashlib.sha256((native / "mechanism.yaml").read_bytes()).hexdigest()
        != ref["mechanism_sha256"]
    ):
        raise ValueError("Mechanism mismatch")
    gas = ct.Solution(str(native / "mechanism.yaml"))
    gas.TP = 298.15, ct.one_atm
    hf = gas.standard_enthalpies_RT * ct.gas_constant * gas.T / gas.molecular_weights
    elements = np.array(
        [
            [
                gas.n_atoms(k, e) * gas.atomic_weights[e] / gas.molecular_weights[k]
                for e in range(gas.n_elements)
            ]
            for k in range(gas.n_species)
        ]
    )
    y0 = np.array(cj["initial"]["Y"])
    x = (np.arange(case["nx"]) + 0.5) * case["dx_m"]
    dx = case["dx_m"]
    rows = []
    snap = []
    maxchar = 0.0
    for plot in sorted(run.glob("plt[0-9]*")):
        ds = yt.load(str(plot))
        g = ds.covering_grid(0, ds.domain_left_edge, ds.domain_dimensions)
        if ds.dimensionality != 2:
            raise ValueError("Not 2D")

        def f(n):
            a = np.asarray(g["boxlib", n].d, dtype=float)[:, :, 0]
            if not np.isfinite(a).all():
                raise ValueError("Nonfinite field")
            return a

        t = float(ds.current_time.d)
        rho = f("density") * 1000
        p = f("pressure") * 0.1
        T = f("Temp")
        u = f("x_velocity") * 0.01
        v = f("y_velocity") * 0.01
        E = f("rho_E") * 0.1
        Y = np.stack([f("Y(" + n + ")") for n in gas.species_names], axis=-1)
        ym = Y.mean(axis=1)
        state = ct.SolutionArray(gas, shape=(case["nx"],))
        state.TDY = T.mean(axis=1), rho.mean(axis=1), ym
        q = (y0 @ hf - ym @ hf) / cj["q_equilibrium_Jkg"]
        pressure = p.mean(axis=1)
        fronts = [
            crossing(
                x, pressure, cj["pressure_Pa"] + a * (cj["VN"]["p"] - cj["pressure_Pa"])
            )
            for a in (0.2, 0.5, 0.8)
        ]
        half = crossing(x, q, 0.5)
        sep = None if half is None or fronts[1] is None else fronts[1] - half
        fronts = [
            None
            if position is None
            else position + case.get("frame_speed_mps", 0.0) * t
            for position in fronts
        ]
        energy = rho * (state.int_energy_mass[:, None] + 0.5 * (u * u + v * v))
        maxchar = max(maxchar, float(np.max(abs(u) + state.sound_speed[:, None])))
        rows.append(
            dict(
                time_s=t,
                fronts_m=fronts,
                half_heat_distance_m=sep,
                Tmin_K=float(T.min()),
                Tmax_K=float(T.max()),
                minimum_Y=float(Y.min()),
                minimum_species=gas.species_names[
                    np.unravel_index(np.argmin(Y), Y.shape)[-1]
                ],
                element_composition_error=float(
                    np.max(abs(Y @ elements - y0 @ elements))
                ),
                species_sum_error=float(np.max(abs(Y.sum(axis=-1) - 1))),
                eos_pressure_relative=float(np.max(abs(pressure / state.P - 1))),
                eos_energy_relative=float(
                    np.max(abs(E - energy)) / max(np.max(abs(E)), 1.0)
                ),
                mass_kg_m2=float(rho.mean(axis=1).sum() * dx),
                energy_J_m2=float(E.mean(axis=1).sum() * dx),
                boundary_mass_flux=float((rho * u)[0].mean() - (rho * u)[-1].mean()),
                boundary_energy_flux=float(
                    ((E + p) * u)[0].mean() - ((E + p) * u)[-1].mean()
                ),
                transverse_nonuniformity=float(
                    max(
                        np.ptp(T, axis=1).max() / T.max(),
                        np.ptp(p, axis=1).max() / p.max(),
                    )
                ),
            )
        )
        snap.append((t, pressure, T.mean(axis=1), q, rho.mean(axis=1)))
    log = (run / "solver.log").read_text()
    hist = {}
    pattern = r"TIME = (\S+)\s+(density|Temp|pressure|massfrac|sumYminus1)\s+MIN = (\S+)\s+MAX = (\S+)"
    for t, n, lo, hi in re.findall(pattern, log):
        hist.setdefault(n, []).append([float(t), float(lo), float(hi)])
    history_valid = history_complete(hist, case["final_time_s"], status["dt"])
    history_checks = {}
    for n, a in hist.items():
        a = np.array(a)
        lo = float(a[:, 1].min())
        hi = float(a[:, 2].max())
        ok = (
            (lo > 0)
            if n in ("density", "pressure")
            else (
                (lo >= 199.9 and hi <= 5000)
                if n == "Temp"
                else (
                    (lo >= -1e-12 and hi <= 1 + 1e-10)
                    if n == "massfrac"
                    else max(abs(lo), abs(hi)) < 1e-9
                )
            )
        )
        history_checks[n] = dict(
            minimum=lo, maximum=hi, passed=bool(ok), samples=len(a)
        )
    times = np.array([r["time_s"] for r in rows])
    mask = times >= 5e-8
    speeds = []
    for i in range(3):
        positions = [r["fronts_m"][i] for r in rows]
        speeds.append(
            None
            if any(v is None for v in positions)
            else float(np.polyfit(times[mask], np.array(positions)[mask], 1)[0])
        )
    expected = ref["ZND"]["heat_fraction_lengths_m"]["0.5"]
    distances = [r["half_heat_distance_m"] for r in rows if r["time_s"] >= 5e-8]
    budgets = {}
    for name, field, flux in [
        ("mass", "mass_kg_m2", "boundary_mass_flux"),
        ("energy", "energy_J_m2", "boundary_energy_flux"),
    ]:
        predicted = np.trapezoid([r[flux] for r in rows], times)
        actual = rows[-1][field] - rows[0][field]
        budgets[name] = dict(
            change=actual,
            boundary_integral=float(predicted),
            normalized_residual=float(
                abs(actual - predicted) / max(abs(rows[0][field]), 1e-20)
            ),
        )
    checks = dict(
        native_completion=status["returncode"] == 0
        and abs(times[-1] - case["final_time_s"]) < 1e-14,
        no_native_errors=not bool(
            re.search(r"CVODE ERROR|AMReX::Abort|\bERROR\b", log, re.I)
        ),
        every_step_history=history_valid
        and all(r["passed"] for r in history_checks.values()),
        element_composition=max(r["element_composition_error"] for r in rows) < 1e-7,
        eos=max(r["eos_pressure_relative"] for r in rows) < 1e-5
        and max(r["eos_energy_relative"] for r in rows) < 1e-5,
        speed=all(
            v is not None and abs(v / cj["CJ_speed_mps"] - 1) < 0.05 for v in speeds
        ),
        structure=all(v is not None and abs(v / expected - 1) < 0.2 for v in distances),
        boundary_buffer=min(
            case["shock_initial_m"], case["length_m"] - case["shock_initial_m"]
        )
        - maxchar * times[-1]
        > 0.0002,
        conservation=all(b["normalized_residual"] < 0.005 for b in budgets.values()),
    )
    checks = {k: bool(v) for k, v in checks.items()}
    report = dict(
        status="passed" if all(checks.values()) else "failed",
        checks=checks,
        case=case,
        rows=rows,
        expected_speed_mps=cj["CJ_speed_mps"],
        speeds_mps=speeds,
        expected_half_heat_m=expected,
        history=history_checks,
        budgets=budgets,
        max_characteristic_mps=maxchar,
        interpretation="Planar prerequisite only. No engine sustainment inference. Short-window CJ/structure checks are conservative screening criteria, not proof that physical pulsations cannot occur. Cantera normalizes invalid negative species, so EOS residuals in failed states are not independent evidence of an EOS defect.",
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    np.savez_compressed(
        output / "profiles.npz",
        x_m=x,
        frame_speed_mps=case.get("frame_speed_mps", 0.0),
        time_s=times,
        pressure_Pa=np.array([s[1] for s in snap]),
        temperature_K=np.array([s[2] for s in snap]),
        heat_fraction=np.array([s[3] for s in snap]),
        density_kg_m3=np.array([s[4] for s in snap]),
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].plot(
        times * 1e6,
        [(r["fronts_m"][1] or np.nan) * 1000 for r in rows],
        "o-",
        label="Native pressure front",
    )
    axes[0].plot(
        times * 1e6,
        (case["shock_initial_m"] + cj["CJ_speed_mps"] * times) * 1000,
        "--",
        label="Independent CJ",
    )
    axes[0].set(xlabel="Time (microseconds)", ylabel="Front position (mm)")
    axes[0].legend()
    axes[1].plot(
        (x + case.get("frame_speed_mps", 0.0) * times[-1]) * 1000,
        snap[-1][1] / 1e6,
        label="Pressure (MPa)",
    )
    axes[1].plot(
        (x + case.get("frame_speed_mps", 0.0) * times[-1]) * 1000,
        snap[-1][3],
        label="Chemical heat fraction",
    )
    axes[1].set(
        xlabel="Distance (mm)",
        xlim=(
            (case["shock_initial_m"] + cj["CJ_speed_mps"] * times[-1] - 0.0003) * 1000,
            (case["shock_initial_m"] + cj["CJ_speed_mps"] * times[-1] + 0.0003) * 1000,
        ),
    )
    axes[1].legend()
    fig.suptitle("Native 2D propagation prerequisite: " + report["status"])
    fig.tight_layout()
    fig.savefig(output / "propagation_gate.png", dpi=160)
    plt.close(fig)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("run", type=Path)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    r = analyze(a.run, a.reference, a.output)
    print(
        json.dumps(
            {
                k: r[k]
                for k in (
                    "status",
                    "checks",
                    "speeds_mps",
                    "expected_speed_mps",
                    "history",
                )
            },
            indent=2,
        )
    )
    raise SystemExit(0 if r["status"] == "passed" else 1)
