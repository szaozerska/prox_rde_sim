"""Independent hot reacting-state control for the candidate mechanism."""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path
import numpy as np


def prepare(reference, mechanism, out):
    import cantera as ct

    out.mkdir(parents=True, exist_ok=False)
    z = np.load(reference / "znd.npz")
    ref = json.loads((reference / "reference.json").read_text())
    gas = ct.Solution(str(mechanism))
    i = int(
        np.argmin(abs(z["distance_m"] - ref["ZND"]["heat_fraction_lengths_m"]["0.9"]))
    )
    gas.TDY = z["temperature_K"][i], z["density_kg_m3"][i], z["species_Y"][:, i]
    initial = dict(
        T=gas.T, rho=gas.density, Y=gas.Y.tolist(), p=gas.P, e=gas.int_energy_mass
    )
    row = np.r_[
        gas.density * 0.001,
        0.0,
        gas.density * gas.int_energy_mass * 10,
        gas.density * gas.Y * 0.001,
    ]
    profile = out / "profile.dat"
    np.savetxt(
        profile,
        np.tile(row, (512, 1)),
        fmt="%.17e",
        header=f"512 {len(row)} 0.1",
        comments="",
    )
    case = dict(
        nx=512,
        ny=8,
        dx_m=0.001,
        length_m=0.512,
        final_time_s=2e-7,
        plot_interval_s=2e-8,
        profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),
        reconstruction_order=1,
        hydro_method="mol",
        scope="Uniform hot reactor, not wave/engine",
    )
    (out / "case.json").write_text(json.dumps(case, indent=2) + "\n")
    reactor = ct.IdealGasReactor(gas, clone=True)
    net = ct.ReactorNet([reactor])
    net.rtol = 1e-12
    net.atol = 1e-23
    rows = []
    for t in np.linspace(0, 2e-7, 11):
        if t:
            net.advance(t)
        g = reactor.phase
        if not 200 <= g.T <= 5000:
            raise ValueError("Hot reference exceeds model range")
        rows.append(
            dict(
                t=float(t),
                T=g.T,
                p=g.P,
                Y=g.Y.tolist(),
                e=g.int_energy_mass,
                rho=g.density,
            )
        )
    (out / "reference.json").write_text(
        json.dumps(
            dict(
                initial=initial,
                rows=rows,
                mechanism_sha256=hashlib.sha256(mechanism.read_bytes()).hexdigest(),
            ),
            indent=2,
        )
        + "\n"
    )
    print("Hot reference:", initial["T"], "->", rows[-1]["T"], flush=True)


def analyze(run, reference):
    import cantera as ct
    import yt

    yt.set_log_level(40)
    status = json.loads((run / "status.json").read_text())
    archive = run / "native.tar.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != status["artifact_sha256"]:
        raise ValueError("Archive checksum")
    target = run / "native"
    if target.exists():
        raise FileExistsError("Hot evidence already extracted")
    with tarfile.open(archive) as tar:
        tar.extractall(target, filter="data")
    ref = json.loads(reference.read_text())
    gas = ct.Solution(str(target / "mechanism.yaml"))
    if (
        hashlib.sha256((target / "mechanism.yaml").read_bytes()).hexdigest()
        != ref["mechanism_sha256"]
    ):
        raise ValueError("Wrong mechanism")
    gas.TDY = ref["initial"]["T"], ref["initial"]["rho"], ref["initial"]["Y"]
    reactor = ct.IdealGasReactor(gas, clone=True)
    net = ct.ReactorNet([reactor])
    net.rtol = 1e-12
    net.atol = 1e-23
    rows = []
    for plot in sorted((target / "run").glob("plt[0-9]*")):
        ds = yt.load(str(plot))
        g = ds.covering_grid(0, ds.domain_left_edge, ds.domain_dimensions)
        t = float(ds.current_time.d)
        if t:
            net.advance(t)

        def f(n):
            a = np.asarray(g["boxlib", n].d)
            if not np.isfinite(a).all():
                raise ValueError("Nonfinite " + n)
            return a

        T = f("Temp")
        P = f("pressure") * 0.1
        Y = np.stack([f("Y(" + n + ")") for n in gas.species_names], axis=-1)
        rows.append(
            dict(
                t=t,
                T_relative=float(np.max(abs(T / reactor.T - 1))),
                p_relative=float(np.max(abs(P / reactor.phase.P - 1))),
                Y_absolute=float(np.max(abs(Y - reactor.phase.Y))),
                minimum_Y=float(Y.min()),
                rho_relative=float(
                    np.max(abs(f("density") * 1000 / ref["initial"]["rho"] - 1))
                ),
                energy_relative=float(
                    np.max(
                        abs(
                            f("rho_E") * 0.1
                            - ref["initial"]["rho"] * ref["initial"]["e"]
                        )
                    )
                    / max(abs(ref["initial"]["rho"] * ref["initial"]["e"]), 1.0)
                ),
            )
        )
    checks = dict(
        completed=status["returncode"] == 0
        and len(rows) >= 11
        and abs(rows[-1]["t"] - 2e-7) < 1e-15,
        temperature=max(r["T_relative"] for r in rows) < 5e-5,
        pressure=max(r["p_relative"] for r in rows) < 5e-5,
        species=max(r["Y_absolute"] for r in rows) < 2e-6,
        positive_species=min(r["minimum_Y"] for r in rows) >= -1e-12,
        density=max(r["rho_relative"] for r in rows) < 1e-10,
        energy=max(r["energy_relative"] for r in rows) < 1e-10,
    )
    result = dict(
        passed=all(checks.values()),
        checks=checks,
        rows=rows,
        scope="Hot homogeneous chemistry integration; not engine validation",
    )
    (run / "hot_analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("reference", type=Path)
    a.add_argument("mechanism", type=Path)
    a.add_argument("output", type=Path)
    a = sub.add_parser("analyze")
    a.add_argument("run", type=Path)
    a.add_argument("reference", type=Path)
    a = p.parse_args()
    if a.action == "prepare":
        prepare(a.reference, a.mechanism, a.output)
    else:
        raise SystemExit(0 if analyze(a.run, a.reference)["passed"] else 1)
