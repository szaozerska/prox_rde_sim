# Quick 2D estimate: theoretical framework and interpretation

This is an offline algebraic screen for an unwrapped annular RDE. It does not
advance a 2D flow field or integrate chemical kinetics. It estimates refill
capacity and candidate wave counts using empirical cell-size rules and a mass
balance. Its sustain/fail classification accuracy has **not** been established.

## Source and adaptation

Adapted at the user's request from `RDEPathwaySpaceXBackyard`, commit
`211b44a5def869d568d986d05fc7c714aaa278c7`,
`Simulation/Models/chamber_sizing.py`. The unchanged original and its SHA-256
are in `vendor/`. This provenance copy is not the supported executable.

The source paper is Law et al., *Design and testing of a small-scale laboratory
rotating detonation engine running on ethylene-oxygen*, AIAA 2021-3658:
https://doi.org/10.2514/6.2021-3658 . Equations 2--8 and Table 1 were checked
against the locally available paper during implementation. The paper attributes
the empirical rules to Kiyanda et al. and Bykovskii et al.; those underlying
studies were not independently revalidated here.

**Correction to the Fable descriptions:** h is radial chamber width (annular
gap); L_cr is critical axial fresh-mixture depth. L_cr is not chamber length.
The paper uses a minimum chamber length of 2 L_cr and recommends at least
4 L_cr for efficient operation. The old code's PASS checked provenance labels,
not physical criteria. This implementation reports those criteria individually.

## Inputs and equations

Required JSON keys explicitly encode units:

| Input | Meaning |
|---|---|
| lambda_mm | Detonation cell size at the relevant fresh-mixture state |
| rho_kg_m3 | Unreacted mixture density, not post-detonation/CJ-product density |
| U_d_m_s | Assumed actual wave speed; CJ speed may be used as a stated reference |
| m_dot_g_s | Combined fuel plus oxidizer mass flow |
| d_c_mm | Outer annulus diameter, matching Law's convention |
| annulus_mm | Radial gap h |
| chamber_length_mm | Actual axial chamber length |
| usable_flow_fraction | Optional eta in [0,1], default 1; explicit assumed usable fraction |

A number may be supplied directly or as `{ "value": 1.0, "class": "...", "hook": "..." }`.
Metadata is carried unchanged. No fuel-specific values are silently selected.
Cell size, density and wave speed must represent compatible conditions. A CJ
calculation alone does not supply cell size. Existing equilibrium/reference
results can supply input values, but no chemistry packages are imported here.

All internal lengths are metres and mass flows kg/s:

- Minimum gap: h >= a lambda, with a = 2.4 and range [1.4, 3.4].
- Critical fresh depth: L_cr = b lambda, with b = 12 and range [7, 17].
- Circumference: C = pi d_c (outer-diameter thin-annulus convention).
- Passage time for N equally spaced co-rotating heads: t = C/(N U_d).
- Strip injection area A = C h; average usable injection velocity = eta mdot/(rho A).
- Fresh depth per passage: H_N = eta mdot/(rho U_d h N).
- Continuous refill capacity: w = eta mdot/(rho L_cr U_d h).
- Spacing rule: K_N = C/(N L_cr), accepted within [5,9], nominal reference 7.

The paper's original refill relation is recovered exactly at eta=1. The area
and circumference cancel in that relation; diameter still affects spacing and
return time. Exact annulus volume uses actual chamber length, not L_cr. This
volume is informational; refill uses the paper's strip area consistently.

## From continuous capacity to integer candidates

`continuous_refill_capacity` is w. Its floor is only the maximum integer count
permitted by the nominal refill balance, not an observed mode. The tool then
checks every potentially feasible integer N against gap, minimum chamber
length, refill and spacing constraints. `expected_wave_count` is populated
only when exactly one nominal candidate survives; otherwise it is null and
the candidate list is the result. Even a unique candidate is conditional.
The 4 L_cr recommended length is reported separately, not a survival gate.

The possible-mode set uses the full coefficient ranges without a parameter
sweep. For each N it intersects:

    L_cr in [7 lambda, 17 lambda]
    L_cr in [C/(9 N), C/(5 N)]       (spacing)
    L_cr <= H_N                    (refill)
    L_cr <= chamber_length / 2      (chamber length)

A nonempty intersection plus h >= 1.4 lambda means a mode is possible under
some allowed coefficients. This prevents combining inconsistent coefficient
choices to manufacture a candidate. These intervals are sensitivity bounds,
not confidence intervals or probabilities. Input uncertainty is not included
in those bounds; rerun explicitly for alternative justified input states.

`conditional_candidates` means nominal rules admit modes;
`marginal_coefficients_only` means only the coefficient ranges admit modes;
`no_candidate_in_model` means no candidate under these assumptions, not proof
that a real engine cannot operate. Integer enumeration is complete up to the
analytic supply/spacing bound, with a 10000-mode input sanity limit.

## Scope and accuracy

No startup, shock evolution, finite-rate chemistry, injector blockage, mixing,
liquid evaporation, wall losses, counter-rotating modes or mode competition is
resolved. eta is only an explicit sensitivity input, not a validated substitute
for those processes. No extra pressure scaling of cell size is applied silently.
The framework does not predict injector-angle effects or actual CAD flow fields.

In particular, Law's chosen 1-bar design-point assumptions can produce no nominal
candidate even though the paper reports successful engine tests at other/local
conditions. The included case is a design calculation, not a reconstruction of
those measured runs. Do not tune lambda until a desired head count appears and
then call that validation. Quantified predictive accuracy requires operating
states and both successful and failed experiments, with held-out comparisons.

This module is useful for fast sensitivities and input consistency checks. It
complements the reduced 2D wave solver and higher-fidelity CFD; it cannot certify
their sustained-wave result or supply physically evolving wave diagrams.

## Verification and traceability

Run `python3 -m unittest discover -s quick_estimate/tests -v`.
Checks cover an independently calculated two-head fixture, mass injected per
passage versus refill volume, parity with Fable's equation, original source hash,
Law Table 1's upper bound and retained lower-bound discrepancy, zero flow, parameter scaling, geometry rejection,
input validation, metadata preservation and CLI output integrity.

These are closed-form expressions plus finite integer enumeration: no spatial,
time-step or iterative-solver convergence test is applicable. Tests demonstrate
implementation consistency, not experimental stability accuracy.

Each CLI JSON result retains the complete inputs, coefficients, formula traces,
per-mode values, checks, limitations, input SHA-256, model SHA-256 and Python
version. Existing result files are refused, preserving previous evidence.
CLI exit 0 means calculation completed (including no-candidate results);
exit 2 means malformed input or file/numerical failure.

## Recorded paper-table discrepancy

Table 1 on PDF page 4 was also visually checked: at 1 bar it prints
w = 0.18--0.75, h = 0.651--1.581 mm, L_cr = 3.255--7.905 mm.
Using the full joint extremes with rho = 100000/(268.1*298) kg/m3,
mdot = 0.005 kg/s and U_d = 2500 m/s gives w = 0.1278525--0.7540690.
The upper endpoint agrees at the table's precision; the lower does not.
The cause is unresolved (coefficient pairing, an unstated assumption, or a table
error are possibilities). No coefficient was fitted to conceal this discrepancy.
The test preserves it explicitly; this is NOT a fully reproduced paper table or
experimental validation. The example's fixed 0.7 mm gap gives nominal w = 0.409.

## Subsequent experimental comparison (2026-10-24)

The [Mundt comparison](validation/README.md) found no admitted modes for five
selected sustained annular cases, or the real deflagration control. Coreless
25-FI-12.7 is unsupported. This is a failed transfer of the current combined
rules, not validation. The conflict persists without relying on cell-size
precision and at half-CJ reference speed. Do not interpret no-candidate as a
reliable prediction of failed operation for these engines.
