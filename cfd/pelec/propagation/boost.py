"""Exact Galilean transformation of the conserved launch; no physical forcing."""

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def transform(table, speed_cgs):
    out = table.copy()
    rho = table[:, 0]
    m = table[:, 1]
    out[:, 1] = m - rho * speed_cgs
    out[:, 2] = table[:, 2] - speed_cgs * m + 0.5 * rho * speed_cgs**2
    before = table[:, 2] - 0.5 * m * m / rho
    after = out[:, 2] - 0.5 * out[:, 1] ** 2 / rho
    if np.max(abs(after - before)) / max(np.max(abs(before)), 1.0) > 1e-12:
        raise ValueError("Boost changed internal energy")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("case", type=Path)
    p.add_argument("profile", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    case = json.loads(a.case.read_text())
    speed = case["CJ_speed_mps"]
    source = a.profile.read_text()
    table = np.loadtxt(a.profile, skiprows=1)
    out = transform(table, speed * 100)
    path = a.output / "profile.dat"
    np.savetxt(path, out, fmt="%.17e", header=source.splitlines()[0], comments="")
    case.update(
        frame_speed_mps=speed,
        profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        transformation="rho unchanged, m_new=m-rho*V, E_new=E-V*m+rho*V^2/2; no forcing",
    )
    (a.output / "case.json").write_text(json.dumps(case, indent=2) + "\n")


if __name__ == "__main__":
    main()
