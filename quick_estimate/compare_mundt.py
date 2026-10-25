"""Reproduce the bounded Mundt figure-based comparison without chemistry packages.

Run from repository root: python3 -m quick_estimate.compare_mundt --out NEW_DIRECTORY
Observed wave labels are used only after estimation, never to construct inputs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from .model import estimate

HERE=Path(__file__).resolve().parent

def pressure_kpa(flux,phi):
    return -531.2+2.965*flux+526.6*phi+.0009336*flux**2-1.418*flux*phi-54.73*phi**2

def interpolate(x, grid, values):
    if not grid[0] <= x <= grid[-1]:
        raise ValueError("reference interpolation outside recorded figure range")
    for i in range(len(grid)-1):
        if grid[i] <= x <= grid[i+1]:
            t=(x-grid[i])/(grid[i+1]-grid[i])
            return values[i]*(1-t)+values[i+1]*t
    raise ValueError("empty reference interpolation interval")

def make_inputs(case, reference):
    phi=case["phi"]; flux=case["mass_flux"]
    pressure=pressure_kpa(flux,phi)
    # CH4:phi, O2:2 mol; fresh-gas mixture MW in kg/kmol.
    molecular_weight=(16.043*phi+31.998*2)/(phi+2)
    gas_constant=8314.46261815324/molecular_weight
    rho=pressure*1000/(gas_constant*300)
    d=case["diameter_mm"]*.001; gap=case["gap_mm"]*.001
    area=math.pi*((d/2)**2-(d/2-gap)**2)
    mdot=case.get("mass_flow_g_s",flux*area*1000)
    at_phi=[interpolate(phi,reference["phi"],row) for row in reference["lambda_mm"]]
    lam=interpolate(pressure,reference["pressure_kPa"],at_phi)
    inputs={"name":case["id"],"lambda_mm":lam,"rho_kg_m3":rho,
            "U_d_m_s":case["speed_reference_m_s"],"m_dot_g_s":mdot,
            "d_c_mm":case["diameter_mm"],"annulus_mm":case["gap_mm"],
            "chamber_length_mm":case["length_mm"],"usable_flow_fraction":1,
            "sources":{"operating_point":case["source"],"geometry":"Mundt Table 2-1",
                       "density":"Eq.4.1 pressure + ideal CH4/O2 at 300 K",
                       "cell_size":"Figure4.2 approximate bilinear interpolation",
                       "speed":case["reference_speed_source"]}}
    c=math.pi*d
    available=mdot*.001/(rho*inputs["U_d_m_s"]*gap)
    diagnostic={"pressure_kPa":pressure,"fresh_R_J_kg_K":gas_constant,
                "exact_exit_area_m2":area,"strip_to_exact_area_ratio":c*gap/area,
                "one_wave_refill_depth_m":available,
                "minimum_K_compatible_with_refill":c/available,
                "minimum_K_using_exact_area_refill":rho*inputs["U_d_m_s"]*area/(mdot*.001),
                "raw_refill_capacity":available/(12*lam*.001),
                "interpretation":"K must be <=9 in inherited model; refill requires K >= C/H1 independently of cell size. Coreless raw formulas are extrapolations only."}
    return inputs,diagnostic

def evaluate(case,reference):
    inputs,diagnostic=make_inputs(case,reference)
    coreless=2*case["gap_mm"]==case["diameter_mm"]
    try:
        result=estimate(inputs)
    except ValueError as exc:
        if not coreless: raise
        return {"case":case,"inputs":inputs,"diagnostics":diagnostic,
                "status":"unsupported_coreless","error":str(exc),"result":None,
                "comparison":"excluded, not predicted zero","sensitivity":[]}
    sensitivity=[]
    # Bounded physical-assumption check, not calibrated uncertainty/probability.
    for speed_factor in (.5,.75,1.):
        for cell_factor in (.8,1.,1.2):
            varied=dict(inputs,U_d_m_s=inputs["U_d_m_s"]*speed_factor,
                        lambda_mm=inputs["lambda_mm"]*cell_factor)
            r=estimate(varied)
            sensitivity.append({"speed_factor":speed_factor,"cell_size_factor":cell_factor,
                                "nominal":r["nominal_candidate_wave_counts"],
                                "possible":r["possible_candidate_wave_counts"]})
    observed=case["primary_waves"]
    candidates=result["nominal_candidate_wave_counts"]
    agrees=(observed in candidates) if observed else not candidates
    return {"case":case,"inputs":inputs,"diagnostics":diagnostic,"status":"evaluated",
            "result":result,"comparison":"admitted_observed_count" if agrees and observed else
            "correct_no_candidate" if agrees else "missed_observed_count", "sensitivity":sensitivity}

def run(manifest):
    rows=[evaluate(c,manifest["reference_grid"]) for c in manifest["cases"]]
    positives=[r for r in rows if r["status"]=="evaluated" and r["case"]["primary_waves"]>0]
    negatives=[r for r in rows if r["status"]=="evaluated" and r["case"]["primary_waves"]==0]
    return {"provenance":{"source_pdf_sha256":manifest["source_sha256"],
                "model_sha256":hashlib.sha256((HERE/"model.py").read_bytes()).hexdigest(),
                "comparison_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "manifest_sha256":hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()},
            "summary":{"supported_positive_cases":len(positives),
                "positive_cases_admitting_observed_count":sum(r["comparison"]=="admitted_observed_count" for r in positives),
                "supported_negative_cases":len(negatives),
                "negative_cases_with_no_candidate":sum(r["comparison"]=="correct_no_candidate" for r in negatives),
                "unsupported_cases":sum(r["status"]!="evaluated" for r in rows),
                "accuracy_claim":"Small selected figure-based comparison, not a population accuracy estimate."},
            "cases":rows}

def markdown(data):
    lines=["# Mundt six-configuration comparison", "", "Figure-derived inputs are approximate; all outputs are conditional.", "",
           "| Configuration / point | Observed primary heads | Nominal candidates | Coefficient-range candidates | Refill capacity |",
           "|---|---:|---|---|---:|"]
    for row in data["cases"]:
        c=row["case"];r=row["result"]
        label=f"{c['configuration']}, phi {c['phi']}, flux {c['mass_flux']}"
        if r is None:
            lines.append(f"| {label} | {c['primary_waves']} | Unsupported coreless | Unsupported | N/A |")
        else:
            lines.append(f"| {label} | {c['primary_waves']} | {r['nominal_candidate_wave_counts']} | {r['possible_candidate_wave_counts']} | {r['continuous_refill_capacity']:.3f} |")
    lines.extend(["", "Empty candidates mean no mode admitted by this model, not proven extinction.", "", "```json",json.dumps(data["summary"],indent=2),"```", ""])
    return "\n".join(lines)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads((HERE/"validation/mundt_cases.json").read_text())
    pdf=HERE.parent/manifest["source_pdf"]
    if hashlib.sha256(pdf.read_bytes()).hexdigest()!=manifest["source_sha256"]:
        parser.error("source PDF differs from reviewed version")
    data=run(manifest)
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/"comparison.json").write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")
    (args.out/"comparison.md").write_text(markdown(data))
    print(markdown(data))

if __name__=="__main__":main()
