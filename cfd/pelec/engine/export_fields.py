"""Export actual native engine fields to SI; preserve time and validity evidence."""

import json
import numpy as np


def export_fields(run, out):
    import cantera as ct
    import yt

    yt.set_log_level(40)
    case = json.loads((run / "case.json").read_text())
    gas = ct.Solution(
        "/opt/PeleC/Submodules/PelePhysics/Mechanisms/FFCM1_Red/mechanism.yaml"
    )
    coeff = np.array(case["element_weights"]).reshape(gas.n_species, gas.n_elements)
    fields = {
        k: []
        for k in (
            "pressure_Pa",
            "density_kg_m3",
            "heat_release_W_m3",
            "u_mps",
            "v_mps",
            "temperature_K",
        )
    }
    times = []
    rows = []
    for path in sorted(run.glob("plt[0-9]*")):
        ds = yt.load(str(path))
        g = ds.covering_grid(0, ds.domain_left_edge, ds.domain_dimensions)
        if ds.dimensionality != 2:
            raise ValueError("Wrong dimension")

        def f(name):
            a = np.asarray(g["boxlib", name].d, dtype=np.float64)[:, :, 0]
            if not np.isfinite(a).all():
                raise ValueError("Nonfinite field " + name)
            return a

        t = float(ds.current_time.d)
        rho = f("density") * 1000
        p = f("pressure") * 0.1
        T = f("Temp")
        u = f("x_velocity") * 0.01
        v = f("y_velocity") * 0.01
        heat = f("heatRelease") * 0.1
        Y = np.stack([f("Y(" + n + ")") for n in gas.species_names], axis=-1)
        elerr = float(np.max(abs(Y @ coeff - np.array(case["elements"]))))
        ysum = float(np.max(abs(Y.sum(axis=-1) - 1)))
        valid = bool(
            rho.min() > 0
            and p.min() > 0
            and T.min() >= 200 - 1e-6
            and T.max() <= 5000 + 1e-6
            and Y.min() >= case.get("species_floor", -1e-12)
            and ysum < 1e-9
            and elerr < 1e-7
        )
        if not valid:
            raise ValueError(
                "Saved state failed independent range/element checks: "
                + json.dumps(
                    dict(
                        time_s=t,
                        Tmin=float(T.min()),
                        Tmax=float(T.max()),
                        Ymin=float(Y.min()),
                        sumY=ysum,
                        elements=elerr,
                    )
                )
            )
        # Independent EOS for all native cells; no native pressure reused as input.
        state = ct.SolutionArray(gas, shape=rho.shape)
        state.TDY = T, rho, Y
        pressure_error = float(np.max(abs(p / state.P - 1)))
        en = f("rho_E") * 0.1
        expected = rho * (state.int_energy_mass + 0.5 * (u * u + v * v))
        energy_error = float(np.max(abs(en - expected)) / max(np.max(abs(en)), 1.0))
        if pressure_error > 1e-5 or energy_error > 1e-5:
            raise ValueError("Native/independent thermodynamics mismatch")
        volume = case["dx_m"] * case["dy_m"] * case["gap_m"]
        fuel = Y[:, :, gas.species_index("CH4")]
        rows.append(
            dict(
                time_s=t,
                Tmin_K=float(T.min()),
                Tmax_K=float(T.max()),
                pmax_Pa=float(p.max()),
                minimum_Y=float(Y.min()),
                sumY_error=ysum,
                element_error=elerr,
                eos_pressure_error=pressure_error,
                eos_energy_error=energy_error,
                mass_kg=float(rho.sum() * volume),
                methane_kg=float((rho * fuel).sum() * volume),
                heat_release_W=float(heat.sum() * volume),
                total_energy_J=float(en.sum() * volume),
            )
        )
        for key, a in zip(fields, (p, rho, heat, u, v, T)):
            fields[key].append(a.astype(np.float32))
        times.append(t)
    if len(times) < 2:
        raise ValueError("Insufficient native frames")
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out / "fields_si.npz",
        time_s=np.array(times),
        x_m=(np.arange(case["nx"]) + 0.5) * case["dx_m"],
        y_m=(np.arange(case["ny"]) + 0.5) * case["dy_m"],
        **{k: np.stack(v) for k, v in fields.items()},
    )
    (out / "field_checks.json").write_text(
        json.dumps(
            dict(
                rows=rows,
                interpretation="Actual native snapshots. State checks do not establish resolved detonation or experimental validation. Boundary flux budgets remain a separate qualification.",
            ),
            indent=2,
        )
        + "\n"
    )
    return dict(frames=len(times), last_time_s=times[-1], valid_snapshots=True)
