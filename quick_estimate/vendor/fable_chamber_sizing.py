#!/usr/bin/env python3
"""chamber_sizing.py - S3 of the sizing chain (simulation skill section 2): from a detonation cell size to the annulus and chamber.

The relations are the published design-rule chain of the design-basis paper (Law et al. 2021, K1 in
Scraping/Knowledge/Law-2021-Southampton-Lab-RDE-Assembly.md; STATED-IN-TEXT, each with the paper's own uncertainty band):
  critical layer height      h      >= (2.4 +/- 1.0) * lambda
  critical chamber length    L_cr    = (12 +/- 5)    * lambda
  optimum chamber length     L_opt  >= 4 * L_cr
  wave-number parameter      K       = pi * d_c / (w * L_cr) = 7 +/- 2     ->  minimum chamber diameter d_c,min = L_cr * K / pi
  fill requirement           w       = m_dot / (rho * L_cr * U_d * h) >= 1  (fresh mixture refilled in one wave period)
  wave period                t_d     = pi * d_c / (w * U_d)
  chamber (annulus) volume   V       = pi * (d_c^2 - d_i^2) * L_cr / 4
NO NUMBER IS INVENTED HERE: lambda, rho, U_d and m_dot come from the inputs file (each with its class and its catalogue row); the control
engine's values come from the K rows. The known-answer control (rule 3) must reproduce Law 2021 (75 mm OD, 0.7-1.2 mm annulus, ethylene-
oxygen, 3.5 / 6.6 / 9.7 g/s -> 1 / 2 / 3 waves) once the cell-size row for ethylene-oxygen at the paper's pressure is in the catalogue.

Usage: python3 Simulation/Models/chamber_sizing.py <inputs.json> [--out Simulation/Runs/<id>/]   -> CHAMBER_SIZING PASS|FAIL + result.json
       python3 Simulation/Models/chamber_sizing.py --selftest                                   (dimensional and monotonic sanity only)
inputs.json: {"lambda_mm": {"value", "class", "hook"}, "rho_kg_m3": {...}, "U_d_m_s": {...}, "m_dot_g_s": {...}, "d_c_mm": {...} (optional),
              "annulus_mm": {...} (optional), "coeffs": {"h": 2.4, "h_tol": 1.0, "Lcr": 12, "Lcr_tol": 5, "K": 7, "K_tol": 2}}"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path

DEFAULT_COEFFS = {"h": 2.4, "h_tol": 1.0, "Lcr": 12.0, "Lcr_tol": 5.0, "K": 7.0, "K_tol": 2.0}   # Law 2021 K1 (STATED-IN-TEXT)


def v(d, key):
    x = d[key]; return float(x["value"]) if isinstance(x, dict) else float(x)


def size(inputs: dict) -> dict:
    c = {**DEFAULT_COEFFS, **inputs.get("coeffs", {})}
    lam = v(inputs, "lambda_mm") / 1000.0; rho = v(inputs, "rho_kg_m3"); Ud = v(inputs, "U_d_m_s"); mdot = v(inputs, "m_dot_g_s") / 1000.0
    h_min = c["h"] * lam; h_band = (max(c["h"] - c["h_tol"], 0.1) * lam, (c["h"] + c["h_tol"]) * lam)
    Lcr = c["Lcr"] * lam; Lcr_band = ((c["Lcr"] - c["Lcr_tol"]) * lam, (c["Lcr"] + c["Lcr_tol"]) * lam)
    Lopt = 4 * Lcr
    out = {"inputs": inputs, "coeffs": c, "lambda_m": lam,
           "h_min_m": h_min, "h_band_m": h_band, "L_cr_m": Lcr, "L_cr_band_m": Lcr_band, "L_opt_m": Lopt}
    h = v(inputs, "annulus_mm") / 1000.0 if "annulus_mm" in inputs else h_min
    out["annulus_used_m"] = h; out["annulus_meets_critical"] = h >= h_band[0]
    if "d_c_mm" in inputs:
        dc = v(inputs, "d_c_mm") / 1000.0; di = dc - 2 * h
        w = mdot / (rho * Lcr * Ud * h)                       # fill requirement: waves supported by the mass flow
        K = math.pi * dc / (max(w, 1e-9) * Lcr)
        out.update({"d_c_m": dc, "d_i_m": di, "wave_number_w": w, "waves_supported": max(0, math.floor(w + 1e-9)), "K": K,
                    "K_in_band": (c["K"] - c["K_tol"]) <= K <= (c["K"] + c["K_tol"]), "t_d_s": math.pi * dc / (max(w, 1e-9) * Ud),
                    "V_m3": math.pi * (dc ** 2 - di ** 2) * Lcr / 4})
    out["d_c_min_m"] = Lcr * c["K"] / math.pi
    out["d_c_min_band_m"] = (Lcr_band[0] * (c["K"] - c["K_tol"]) / math.pi, Lcr_band[1] * (c["K"] + c["K_tol"]) / math.pi)
    out["classes"] = {k: (inputs[k].get("class") if isinstance(inputs.get(k), dict) else "UNLABELLED") for k in ("lambda_mm", "rho_kg_m3", "U_d_m_s", "m_dot_g_s")}
    out["hooks"] = {k: (inputs[k].get("hook") if isinstance(inputs.get(k), dict) else None) for k in ("lambda_mm", "rho_kg_m3", "U_d_m_s", "m_dot_g_s")}
    return out


def selftest() -> int:
    """Dimensional and monotonic sanity only (no physical claim): halving lambda halves L_cr and d_c,min; doubling m_dot doubles w."""
    base = {"lambda_mm": {"value": 1.0, "class": "SYNTHETIC", "hook": "selftest"}, "rho_kg_m3": {"value": 1.0, "class": "SYNTHETIC"},
            "U_d_m_s": {"value": 1500.0, "class": "SYNTHETIC"}, "m_dot_g_s": {"value": 5.0, "class": "SYNTHETIC"}, "d_c_mm": {"value": 75.0, "class": "SYNTHETIC"}}
    a = size(base); b = size({**base, "lambda_mm": {"value": 0.5, "class": "SYNTHETIC"}}); c2 = size({**base, "m_dot_g_s": {"value": 10.0, "class": "SYNTHETIC"}})
    ok = abs(b["L_cr_m"] / a["L_cr_m"] - 0.5) < 1e-9 and abs(b["d_c_min_m"] / a["d_c_min_m"] - 0.5) < 1e-9 and abs(c2["wave_number_w"] / a["wave_number_w"] - 2.0) < 1e-9
    ok = ok and all(k in a["classes"] for k in ("lambda_mm", "rho_kg_m3")) and a["annulus_meets_critical"]
    print(f"CHAMBER_SIZING_SELFTEST {'PASS' if ok else 'FAIL'} (monotonic in lambda and m_dot; classes carried)"); return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="?"); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.selftest: return selftest()
    if not a.inputs: ap.error("inputs.json required (or --selftest)")
    inputs = json.loads(Path(a.inputs).read_text()); res = size(inputs)
    unl = [k for k, cl in res["classes"].items() if cl in (None, "UNLABELLED")]
    verdict = "FAIL" if unl else "PASS"
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True); (a.out / "result.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"CHAMBER_SIZING {verdict} lambda_mm={res['lambda_m']*1e3:.3f} h_min_mm={res['h_min_m']*1e3:.3f} L_cr_mm={res['L_cr_m']*1e3:.1f} "
          f"L_opt_mm={res['L_opt_m']*1e3:.1f} d_c_min_mm={res['d_c_min_m']*1e3:.1f}" + (f" w={res['wave_number_w']:.2f} waves={res['waves_supported']} K={res['K']:.2f}" if "K" in res else "")
          + (f" UNLABELLED_INPUTS={unl}" if unl else ""))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
# -claude, 2026-10-20 (Prox; S3 scaffold; the control run waits for the cell-size row)
