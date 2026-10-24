"""Adapted from Fable chamber_sizing.py; see vendor/provenance.json and THEORY.md."""
import math

REQUIRED = ("lambda_mm", "rho_kg_m3", "U_d_m_s", "m_dot_g_s",
            "d_c_mm", "annulus_mm", "chamber_length_mm")
OPTIONAL = ("name", "description", "sources", "usable_flow_fraction")
COEFFICIENTS = {"gap": [1.4, 2.4, 3.4], "critical_depth": [7.0, 12.0, 17.0],
                "spacing_K": [5.0, 7.0, 9.0]}


def number(inputs, key):
    raw = inputs[key]
    if isinstance(raw, dict):
        raw = raw.get("value")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"{key} must be a finite number (or an object with numeric value)")
    x = float(raw)
    if not math.isfinite(x):
        raise ValueError(f"{key} must be finite")
    return x


def estimate(inputs):
    if not isinstance(inputs, dict):
        raise ValueError("input must be a JSON object")
    missing = set(REQUIRED) - inputs.keys()
    unknown = inputs.keys() - set(REQUIRED) - set(OPTIONAL)
    if missing or unknown:
        raise ValueError(f"missing keys={sorted(missing)}; unknown keys={sorted(unknown)}")
    v = {k: number(inputs, k) for k in REQUIRED}
    for k, x in v.items():
        if x < 0 or (k != "m_dot_g_s" and x == 0):
            raise ValueError(f"{k} must be positive (mass flow may be zero)")
    eta = number(inputs, "usable_flow_fraction") if "usable_flow_fraction" in inputs else 1.0
    if not 0 <= eta <= 1:
        raise ValueError("usable_flow_fraction must lie in [0, 1]")
    lam, gap, diameter, length = (v[k]/1000 for k in
        ("lambda_mm", "annulus_mm", "d_c_mm", "chamber_length_mm"))
    if 2*gap >= diameter:
        raise ValueError("annulus_mm must be less than half d_c_mm")
    rho, speed, mdot = v["rho_kg_m3"], v["U_d_m_s"], v["m_dot_g_s"]/1000
    circum = math.pi*diameter  # Outer-diameter strip convention in Law Eq. 4/6.
    low, critical, high = (x*lam for x in COEFFICIENTS["critical_depth"])
    supply_depth = eta*mdot/(rho*speed*gap)  # Available depth for one head.
    capacity = supply_depth/critical
    upper = min(supply_depth/low, circum/(5*low))
    if not all(math.isfinite(x) for x in (supply_depth,capacity,upper,high)):
        raise ValueError("input scales exceed numerical range")
    if upper > 10000:
        raise ValueError("more than 10000 candidate modes; check input units")
    rows = []
    for n in range(1, max(1, math.floor(upper))+1):
        k = circum/(n*critical)
        depth = supply_depth/n
        # A single Lcrit must satisfy ALL conditions; do not mix incompatible extremes.
        feasible_low = max(low, circum/(9*n))
        feasible_high = min(high, circum/(5*n), depth, length/2)
        nominal = (gap >= 2.4*lam and length >= 2*critical and
                   depth >= critical and 5 <= k <= 9)
        possible = gap >= 1.4*lam and feasible_low <= feasible_high
        rows.append({"waves":n, "K_nominal":k, "return_time_s":circum/(n*speed),
                     "passage_frequency_Hz":n*speed/circum,
                     "fresh_depth_m":depth, "nominal_rules_satisfied":nominal,
                     "possible_with_coefficient_ranges":possible,
                     "compatible_critical_depth_m":[feasible_low,feasible_high] if possible else None})
    nominal = [r["waves"] for r in rows if r["nominal_rules_satisfied"]]
    possible = [r["waves"] for r in rows if r["possible_with_coefficient_ranges"]]
    checks = {"gap_nominal":gap >= 2.4*lam, "chamber_minimum_nominal":length >= 2*critical,
              "chamber_recommended_nominal":length >= 4*critical,
              "one_wave_refill_nominal":capacity >= 1, "integer_mode_nominal":bool(nominal)}
    return {"schema_version":1, "model":"Law2021-algebraic-screen-v1",
            "inputs":inputs, "coefficients":COEFFICIENTS,
            "status":"conditional_candidates" if nominal else
                     "marginal_coefficients_only" if possible else "no_candidate_in_model",
            "expected_wave_count":nominal[0] if len(nominal)==1 else None,
            "nominal_candidate_wave_counts":nominal, "possible_candidate_wave_counts":possible,
            "continuous_refill_capacity":capacity, "nominal_refill_capacity_floor":math.floor(capacity),
            "critical_fresh_depth_m":critical, "critical_fresh_depth_range_m":[low,high],
            "minimum_gap_m":2.4*lam, "minimum_chamber_length_m":2*critical,
            "recommended_chamber_length_m":4*critical,
            "annulus_volume_m3":math.pi*(diameter**2-(diameter-2*gap)**2)*length/4,
            "checks":checks, "candidate_details":rows,
            "trace":[{"quantity":"critical_fresh_depth_m", "equation":"12 * lambda_m", "value":critical},
                     {"quantity":"usable_mass_flow_kg_s", "equation":"eta * mdot_kg_s", "value":eta*mdot},
                     {"quantity":"one_head_fresh_depth_m", "equation":"eta*mdot/(rho*Ud*gap)", "value":supply_depth},
                     {"quantity":"continuous_refill_capacity", "equation":"one_head_fresh_depth/Lcrit", "value":capacity},
                     {"quantity":"outer_circumference_m", "equation":"pi*d_outer", "value":circum}],
            "limitations":["Unvalidated stability screen; candidates are not observed or guaranteed stable waves.",
                           "Coefficient ranges are sensitivity bounds, not confidence intervals or probabilities.",
                           "Cell size, density and wave speed must describe the same unreacted mixture/operating state.",
                           "No resolved injection, mixing, ignition, chemistry, wall losses or wave competition.",
                           "usable_flow_fraction is an explicit assumed correction, not a calibrated loss model."]}
