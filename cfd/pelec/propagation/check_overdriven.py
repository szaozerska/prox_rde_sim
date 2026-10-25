"""Diagnostic only: compare a transient front with its own overdriven ZND scale.

A match does not establish spatial convergence or engine sustainment. Never use
this diagnostic to silently change the originally recorded propagation gate.
"""

import argparse
import copy
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "rde_sim_starter"))
from reference import _libraries, _znd, _state  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("reference", type=Path)
    p.add_argument("wave", type=Path)
    p.add_argument("mechanism", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    ref = json.loads(a.reference.read_text())
    wave = json.loads(a.wave.read_text())
    ct, post, znd, thermo, _ = _libraries()
    rows = wave["rows"][-3:]
    speed = float(
        np.polyfit([r["time_s"] for r in rows], [r["fronts_m"][1] for r in rows], 1)[0]
    )
    initial = ct.Solution(str(a.mechanism))
    initial.TPX = 300.0, ref["CJ"]["pressure_Pa"], {"CH4": 1.176, "O2": 2}
    work = ct.Solution(str(a.mechanism))
    work.TPX = initial.T, initial.P, initial.X
    work = post.shk_calc(speed, work, initial, 1e-8, 1e-8)
    r = copy.deepcopy(ref["CJ"])
    r["CJ_speed_mps"] = speed
    r["VN"] = _state(work)
    r["VN"]["u_shock_frame"] = speed * initial.density / work.density
    gas = ct.Solution(str(a.mechanism))
    gas.TP = 298.15, ct.one_atm
    hf = gas.standard_enthalpies_RT * ct.gas_constant * gas.T / gas.molecular_weights
    result, _ = _znd(
        ct, znd, thermo, r, initial, work, hf, 2e-8, 1e-14, 1e-10, end=2e-7
    )
    out = dict(
        measured_late_speed_mps=speed,
        steady_CJ_speed_mps=ref["CJ"]["CJ_speed_mps"],
        overdriven_VN=r["VN"],
        ZND=result,
        measured_final_half_heat_m=wave["rows"][-1]["half_heat_distance_m"],
        interpretation="Diagnostic at measured transient speed, with the same heat-fraction normalization. No change to original acceptance status. Does not prove a physical instability or engine sustainment.",
    )
    a.output.write_text(json.dumps(out, indent=2) + "\n")
    print(
        "Late speed",
        speed,
        "expected half heat",
        result["heat_fraction_lengths_m"]["0.5"],
        "measured",
        out["measured_final_half_heat_m"],
    )


if __name__ == "__main__":
    main()
