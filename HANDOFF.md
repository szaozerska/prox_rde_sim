# Handoff: controlled 2D investigation on main

Snapshot: **October 22, 2026**. Repository:
`/Users/sgfx/Desktop/Projects/prox_rde_sim`.

## Current result and plan

[Revision 9](first_sim_plan.md) records the completed D3 investigation and the
[paper/model audit](docs/verification/mundt_model_audit.md). The latest instruction authorizes controlled 2D tests, three plan reviews,
small verified increments and publication on **main only**. The independent
session handles 3D in another checkout/branch; do not push to its branch. D3 and
audit work is included in the initial publication for that session to consume.
See [controlled-test plan](docs/plans/controlled_2d_tests.md) for all three reviews
and the C1–C6 gates. No detonationFoam install is needed for the current controls.

**[RDE-001 remains OPEN](docs/verification/run937_unresolved.md).** The 3.8 mm
baseline and 7.6 mm startup variant both fail to demonstrate sustained rotating
detonation over 189.394 µs. D3 adds physical references and numerical evidence;
it did not modify production chemistry or run a new 2D case. Passing software
checks is not the broader Stage 3 sustained-wave milestone. The solver can
attempt detonation and supports the tested 1D wave; no missing switch guarantees
stable rotation. Broader Stage 1 refinement/model assessment remains incomplete.

See [D3 evidence and graphs](docs/verification/d3_investigation.md):

- Cantera 3.2.0 / GRI-Mech 3.0 / pinned SDToolbox give a physical CJ reference of
  2531.86 m/s, 5.41847 MJ/kg and 3994.14 K, versus the surrogate's fitted
  2471 m/s, 5.5 MJ/kg and 4885.15 K. Half-heat distances are 0.03952 versus 1 mm.
  Detailed ZND uses maximum dT/dt for induction, with a 1.0644 mm factor-29 proxy.
  CJ/heat-release neighborhood and stricter-tolerance checks are saved. NASA CEA
  was not run; this is an independent equilibrium cross-check. The 2.46% CJ
  difference from the paper remains to be reconciled, not silently fitted away.
- At 0.5/0.25/0.125 mm, moving-contact conversion decreases from
  726.44 to 457.79 to 289.78 J/m². Frozen controls preserve pressure and release
  no heat. This demonstrates mesh-dependent numerical-contact reaction, without
  proving its causal contribution to 2D decay or predicting physical flame speed.
- Fixed-chemistry 1D speeds over 40–95 µs are 2456.05/2490.16/2522.45 m/s;
  the 65–90 µs fits are 2457.33/2477.59/2495.97 m/s. A settled, spatially
  converged speed has not been established by matching the fitted CJ value.

**C1 passed:** all four 95 µs controls have identical saved primitive fields,
fronts and zero transverse variation; conservation residual <4e-15, zero invalid
states. Default suite: 60 passed, one opt-in skipped.

**C2 passed:** conservative formed-profile and filled-strip propagation checks
at 0.5/0.25/0.125 mm through 40 µs, plus half-source-step control. Continued
near-front reaction, no invalid states, budgets <2e-14 and positive causal margins.
This verifies a surrogate control, not Run 937.

**Next planned increment:** C3's bounded layer comparison; C4 compares initiation methods in a demonstrated
supporting layer. Freeze chemistry and quantify source/time/grid effects, initial
inventory and boundary causality. Stop advancement on a critical inconsistency.
Document each increment and push it to main after verification. The old automatic
0.25 mm engine refinement is superseded by these causal controls.

## Subsequent diagnostic review

The [layer-height / reaction-length review](docs/verification/layer_diagnostic_review.md)
finds the central hypothesis credible and still untested: at the time of that review no multirow reactive strip, formed-profile layer-height
bracket, or matched ignition control had been run. C1 now passes; the latter
two controls remain pending. Saved-profile postprocessing gives 5.72 µs to 95% surrogate heat
release versus a 4.16–4.39 µs illustrative transverse relief scale. This supports
a targeted test, not a proven extinction criterion. The submitted diagnosis
incorrectly asserted delayed outflow and broadly excluded outlet/contact effects.
No new simulation was run for this review. Prioritize these controls before
expensive full-engine 3D reacting runs; 3D backend preparation is independent.
The issue now clarifies that predeclared, verified reaction-length sensitivity
is allowed, while outcome-driven tuning is not.

The pre-publication default suite ran 59 tests in 188.374 s: 58 passed, one
opt-in propagation test skipped. Its full D3 execution is recorded separately.
See [increment log](docs/verification/controlled_2d_progress.md).

## Implemented interfaces and verification

- `experiments.py contact|refinement --out ...`: six frozen/reactive moving-contact
  cases or three 1D grids, bounded durations, frozen calibration and source cap,
  conserved initialization, native-budget metrics and source hashes.
- `reference.py --out ...`: optional physical CJ/ZND/equilibrium calculation;
  bounded CJ search, checked integration, failure evidence and exact provenance.
  Vendored upstream code/license remain unmodified. Warnings and residual limits
  are recorded in the report; full G0 curves and exact CEA replication are pending.
- `test_1d.py --dx-mm ...`: explicit spacing on the existing propagation case.
- `plot.py --experiments ...` and `--reference ...`: saved-data rendering only.
- D3 added eight tests and expanded import coverage; its full **59-test suite**
  passed, including the opt-in 95 µs reactive baseline. The audit did not rerun it. See `docs/verification/d3_tests.log`.
  New module imports do not load Cantera, solve, render or write files.

Production `solver.py`, `physics.py`, `run.py`, `analyze.py`, `calibrate.py`,
`config.yaml` and `calib.json` are unchanged. Existing D1/D2 checkpoints retain
the same numerical fingerprint. D0 checkpoints still require their original code.
The original calibration/legacy plots remain historical inputs, not new validation.

## Commands and artifacts

From the repo root, reuse `.venv`. For reference calculations only:

```sh
.venv/bin/python -m pip install --only-binary=:all: --no-deps --target .reference-deps -r requirements-reference.txt
cd rde_sim_starter
PYTHONPATH=../.reference-deps ../.venv/bin/python reference.py --out runs/new_reference
NUMBA_NUM_THREADS=2 ../.venv/bin/python experiments.py contact --out runs/new_contact
NUMBA_NUM_THREADS=2 ../.venv/bin/python experiments.py refinement --out runs/new_refinement
../.venv/bin/python plot.py --reference runs/new_reference --out runs/new_reference/plots
../.venv/bin/python plot.py --experiments runs/new_contact --out runs/new_contact/plots
../.venv/bin/python plot.py --experiments runs/new_refinement --out runs/new_refinement/plots
RDE_RUN_REACTIVE_BASELINE=1 NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

Install the optional directory only when absent; avoid updating the base stack.
Output destinations must be new. Replot saved data instead of repeating flow runs.
The default test command omits `RDE_RUN_REACTIVE_BASELINE=1`; its slow propagation
check is then skipped, as before. Cantera is unnecessary for either test command.

Local runs: `rde_sim_starter/runs/d3_contact`, `d3_refinement`, `d3_reference`.
Selected figures, `d3_metrics.json`, test/reference logs and the narrative report
are under `docs/verification/`. D1/D2 saved runs and reports remain intact.

## Preserve these distinctions

- Three reference intervals = 189.394 µs; extend the same saved run to five total
  = 315.657 µs only for a specific unresolved observation. Reference frequency
  budgets time, not the simulated wave count. A pressure peak is not a detonation.
- Baseline fill is 3.8 mm. The D2 7.6 mm variant changed initialization only and
  also enlarged the ignition mask (5.027→9.425 J). It was not fixed-energy
  isolation of fill height. Neither start established the target rotating wave.
- Chemical-to-thermal conversion is internal redistribution of stored chemical
  energy; do not add it again to total energy. Do not tune reaction length to grid.
- Native flux closure checks numerical accounting, not physical boundary validity.
  Annulus-exit force is not whole-engine thrust; angular balance is not mechanical
  wall torque. Wall traction/heat loss, CAD and 3D remain unimplemented.
- Keep the abandoned Google Drive troubleshooting stopped.

## Environment and workspace

Base Python 3.12.0 on macOS x86_64 remains pinned by `requirements.txt`.
Optional Cantera and supporting packages are isolated in `.reference-deps`, pinned
by `requirements-reference.txt`; SDToolbox/mechanism hashes are retained in results.
Use two Numba threads for small checks. The first Cantera mechanism load on this
host took roughly 1–2 minutes; reference work is separate from CFD test runtime.

The app's sandbox still names the removed `RDEPathwaySpaceXBackyard` folder.
D3 was staged in `/private/tmp/prox_rde_d3_work`; the subsequent audit used
`/private/tmp/prox_rde_d4_work`. Changes were transferred to the real repository
with original-file checks and byte verification through normal approval.
The repository and saved outputs are the durable working copies; the temporary
staging directory is not required for further work.
