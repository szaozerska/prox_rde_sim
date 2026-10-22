# G1: native control results and chemistry hold

The shock-control increment passed. The chemistry increment has **not passed**;
no methane detonation or engine simulation is authorized by these results. All
cases use pinned upstream PeleC, 3D FP64, with eight transverse cells per direction
for the shock and an 8 x 8 x 8 uniform periodic closed reactor. One H100 is used;
CPU executables are serial controls, not a CPU scaling benchmark. The common
runner reserves one GPU even when filtering to a CPU control; those timings must
not be represented as CPU-only allocation cost.

## Shock verification passed

At normalized time 0.2, the three axial resolutions (64/128/256) and corresponding
fixed steps (0.001/0.0005/0.00025) have decreasing exact-Sod mean absolute errors:

| Quantity | 64 | 128 | 256 |
|---|---:|---:|---:|
| Density | 0.0065600 | 0.0032081 | 0.00179636 |
| Pressure | 0.0050041 | 0.0022096 | 0.00111912 |
| Axial velocity | 0.0167757 | 0.0063082 | 0.00310159 |

A separate step-halving check at 128 cells changes these quantities by less than
10% of their same-grid exact-reference error. CPU/GPU relative maximum differences
are below 1.6e-14. Finite/positive states, transverse invariance, final time,
mass/energy and pressure-impulse budgets pass. This is a discontinuous mathematical
shock problem, not a smooth second-order convergence claim or methane validation.
The plot was rendered and visually checked. Full report: `shock_checks.json`.

The five native executions took 2.06/2.30/4.32/3.71 s on the H100 and 11.64 s for
the serial CPU control. Startup and output are included. These tiny timings do not
predict reacting RDE cost or production GPU speedup.

## Chemistry acceptance criteria, unchanged

The closed constant-volume LiDryer hydrogen control starts at **1001 K**, 101325 Pa,
Y(H2/O2/N2)=0.06/0.50/0.44, and targets 1 ms. The reason for avoiding the 1000 K
NASA fit join is already documented in G0. This is not the methane engine model.

Before accepting it require: actual CVODE activation; no solver errors; completed
physical interval; all-step temperature relative error <2e-5 against the stated
reference; sampled pressure relative error <2e-5 and species absolute error <2e-6;
native energy drift <1e-10; independent thermodynamic energy residual <1e-8;
element error <1e-9; density drift <1e-12; mass-fraction sum error <1e-11;
nonnegative species to 1e-12; spatial uniformity <1e-8. Compare CPU/GPU and halve
the outer step independently of tightening the chemistry solver tolerance.
These are numerical control criteria, not experimental uncertainty estimates.

Cheap native reductions cover every step. Full-cell field checks cover endpoints,
11 regular checkpoints and neighbors of peak heating. Five-microsecond histories
include a steep ignition point omitted by ten-microsecond output; their maxima
must not be compared as though they used identical time samples.

## Failures and discriminating checks

1. **No-op chemistry:** `do_react=1` alone leaves the default `ReactorNull` selected.
   The initial controls finished and conserved energy but did not react. Independent
   temperature/activation checks reject them. The runner now explicitly selects
   `ReactorCvode`, and checks the initialization log. Initial evidence is retained.
2. **Species absolute tolerance:** rtol=1e-9, atol=1e-15 gives a 0.467% maximum
   temperature error at ten-microsecond samples (14.44% at the additional 135 us
   sample in the step-halved case). CPU/GPU agree, and budgets pass; neither proves
   correct ignition timing. Holding rtol fixed and reducing atol to 1e-18 improves
   the errors to 0.0238% and 0.600%, respectively. These still fail the reference
   criterion. Very tight settings either time out or hit CVODE's internal step
   limit; they are not successful tests.
3. **Generated-rate conventions:** a direct compiled chemistry-operator probe,
   independent of CVODE/CFD, finds a source-derived difference from the nominal
   YAML: generated activation energies use Rcal=1.9872155831739962 while Cantera's
   thermochemical-calorie value is 1.9872042586408318; reverse-rate reference
   concentration uses rounded R=8.31446. Thermodynamics agree near roundoff, but
   production-rate differences reach about 4e-5 in the tested reacting mixtures.
   This is a model representation difference, not a GPU error. A separate Cantera
   diagnostic derives those two conventions from the pinned header, without fitting
   reactor data or changing the solver. It matches direct hot-state rates to about
   2e-14 across fresh/reacting mixtures, 1001–3000 K and 1/3 bar. At 300 K a residual
   up to 3e-8 remains, consistent with additional coefficient rounding; do not claim
   exact equivalence at all temperatures. Nominal YAML reports remain separate.
   Even with these conventions, atol=1e-18 leaves a 0.0826% maximum history error
   in the five-microsecond case: this does **not** clear the integration gate.
4. **CPU can silently under-advance chemistry:** the analytical-Jacobian CPU
   diagnostic at rtol=1e-10, atol=1e-20 hits the internal CVODE step limit, then
   continues the flow clock. Source `ReactorCvode.cpp` calls CVode without checking
   its return in the CPU per-cell path. In the GPU path that return is checked.
   At reported 140 us the failed CPU run is about 39.7% low in temperature against
   the native-constant diagnostic. It eventually hits the external timeout at
   570 us. Preserve it as invalid numerics; do not infer a physical ignition delay.
   New runner/analyzer log checks reject native errors regardless of final time or
   exit status. A regression test reproduces this failure signature.
5. **Current hypothesis under test:** the native EOS inversion stops at a 1e-6 K
   correction, whereas the tight relative ODE setting requests roughly 1e-7 K at
   initial temperature. The RHS recomputes temperature from fixed energy. This can
   create an accuracy floor, but it is not yet a demonstrated root cause. A bounded
   A/B build uses the mechanism's existing `CONVERGENCE` mode (1e-12 K inversion, iteration cap 5000 rather than 200)
   with unchanged rates and ODE settings. No native numerical source is patched.

No grid issue is implicated by a homogeneous, no-hydro reactor. Do not explain a
failed integration away with future 3D geometry or injector physics. GPU-first
remains a bounded engineering trial: failures also occur on CPU, so there is not
yet evidence that changing hardware or CFD package would solve this issue.

## Reproduction and retained evidence

See `tools/pelec/README.md` for commands. Bulk native fields remain under ignored
`runs3d/pelec_*`. This directory preserves compact execution/field checks, build
hashes, direct-rate diagnostics and a native failure log. Execution completion and
physics acceptance are deliberately separate. `initial_*` includes the rejected
no-op case. `tight_timeout_*` and `atol20_failure_*` preserve incomplete controls.

Gate status: G0 passed; G1 shock passed; G1 chemistry blocked pending the above
small investigation. G2 methane/formed-wave propagation and G3 engine work have
not started. Do not advertise sustained detonation, a calibrated classifier, or a
measured two-hour RDE runtime from these controls.

Committed log copies have trailing whitespace removed; original byte-for-byte logs
remain in the checksummed native run artifacts.
