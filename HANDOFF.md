# Handoff: functional 2D implementation on main

Snapshot: **October 22, 2026**. Repository:
`/Users/sgfx/Desktop/Projects/prox_rde_sim`.

Latest addition: final reports include both timed propagation GIFs; see
[GIFs and fuel accounting](docs/verification/propagation_gifs.md). Radial-active
fresh-mixture inventory increases from 15.35 to 49.64 mg while injection continues.
Global exhaustion is excluded for this case; sustained shock/reaction coupling
remains unresolved. Native inputs and physics parameters are unchanged.

## Current result and plan

[Revision 17](first_sim_plan.md) records the completed D3 investigation and the
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

**C3 completed bounded comparison:** 3.8 mm loses leading shock/reaction coupling while 15 mm
retains strong coupling near the wall/middle at 40 µs. No invalid states or
remote-boundary cone violation; numerical interface burning remains visible.
The 0.25 mm thin case also loses coupling (25.75 mm wall-to-main-reaction gap
at 40 µs). The aligned thin control also loses coupling. The thick refinement stopped
at 23.56 µs on its declared speed bound (valid state, no failure of coupling);
its audited continuation reached 40 µs, retaining wall/middle coupling and valid
budgets. C3 closes only the bounded qualitative contrast, not a steady-state or
critical-height claim. The full 71-test suite passed, including the reactive baseline.

**C4 completed:** the 15 mm blast retains nearby reaction at 40 µs, but is weaker
and slows more than the formed controls. No long-term initiation success/failure
or startup-only engine remedy is established. Fields, inventories and direct
comparison are in the increment log.

**C5a completed:** the [readiness review](docs/verification/c5_model_readiness.md)
rejects promoting an unverified rate/profile fit to the engine. Physical reaction
lengths are subcell on the current grid; a two-distance fit would require at
least 91.09 million steps under the present global source cap, while retaining
EOS/held-out profile errors. The algebraic candidate was not adopted.

**Completed functional increment:** C6a conservative periodic formed-engine
initialization and an explicitly labelled <=2 us cost/validity benchmark.
The 2 us check completed in 556 steps with zero invalid states; native budgets
stay below 6.19e-15 scaled error. 86 distinct tests pass, one opt-in is skipped.
See [implementation, test review and results](docs/verification/c6a_functional_pipeline.md).
The latest user instruction assigns the sustaining-wave study to a separate
chat; continue functional work here, preserving RDE-001 as open. Do not launch a
three-interval engine study or another layer sweep in this chat by default.

**F1 saved-window reporting is implemented:** native budgets, storage, station
means, annulus-exit force and qualified effective Isp are available from saved
history through `window_report.py`. See [F1 evidence and commands](docs/verification/f1_window_reporting.md).
Reports use explicit time windows, show partial-step interpolation and missing
native data, and never run CFD. Full regression: 98 passed, one opt-in long propagation test skipped; final
CLI/import checks passed. Saved C6a and D1 examples are linked in the F1 report.

**F2 minimal geometry/result contracts are implemented**; see [evidence](docs/verification/f2_contracts.md).
F3 optional wall friction/torque is implemented; see [verification](docs/verification/f3_wall_friction.md).
F4 is implemented; see the [completion matrix](docs/plans/2d_workflow_completion.md),
[acceptance report](docs/verification/f4_workflow_completion.md), and README commands.
Workflow acceptance: 122 tests passed with no skips, 16 affected tests repeated after final review, and one additional coupled wall/reaction ODE check passed (123 distinct tests).
The latest user request now authorizes a separate radial-closure increment and a controlled sustainment assessment here, after workflow completion. Read the independent report before choosing closures; do not add arbitrary tangential centrifugal forcing or tuned curvature losses. CAD remains out of scope.
Finish these software capabilities without treating them as physical validation. Retain
the C5 chemistry/model qualifications. The new named formed case does not replace
`config.yaml` or imply a model of Mundt's actual pre-detonator. Commit and push
2D work on main; leave the independent 3D branch alone.

## Subsequent diagnostic review

The [layer-height / reaction-length review](docs/verification/layer_diagnostic_review.md)
identified the central hypothesis as credible before these controls existed.
C1–C4 now provide row/direction checks, formed-profile verification, a refined
layer comparison and a bounded blast/profile comparison. Saved-profile postprocessing gives 5.72 µs to 95% surrogate heat
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
  wall torque. Optional wall traction/heat transfer and centrifugal equilibrium
  are now implemented; resolved radial dynamics, CAD and 3D are outside this
  branch's delivered 2D workflow.
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

## Controlled diagnostic commands

From `rde_sim_starter/`, choose a new output path for every run:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python controlled.py strip --out runs/new_strip
NUMBA_NUM_THREADS=2 ../.venv/bin/python controlled.py formed --dx-mm 0.5 --out runs/new_formed
NUMBA_NUM_THREADS=2 ../.venv/bin/python controlled.py layer --height-mm 3.8 --dx-mm 0.5 --out runs/new_layer
../.venv/bin/python plot.py --controlled runs/new_layer --out runs/new_layer/plots
```

The strip/formed/layer CLI caps are 95/40/40 µs. Do not automatically rerun
these commands when inspecting existing plots; render their saved run instead.
Layer runs retain `progress.json` while advancing and final native fields/budgets.

Large layer controls now save an exact `state.npz`. For the reviewed thick
continuation (new output path; original remains immutable):

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python controlled.py layer --height-mm 15 --dx-mm 0.25 --resume runs/c3_layer_150_025 --transverse-bound 3200 --out runs/new_thick_continuation
```

C4's `--start blast` comparator completed at 15 mm / 0.5 mm. It is a weaker
reacting transient, not a demonstrated long-term ignition failure or success.
Compare saved cases with `plot.py --layer-comparison RUN1 RUN2 --out NEW`.
C5a readiness review is complete; its successor quarter-length C5b–e controls
are now complete. C6a is the functional increment; see the current status above.
`model_audit.py --evidence ../docs/verification/d3_metrics.json --out NEW.json`
reproduces the saved-reference algebra without CFD or calibration changes.


## October 22 update: authorized quarter-length experiment

C5b–d now pass for the declared L50=0.25 mm sensitivity (k times four; unchanged
Ea/EOS/source integrator). C5e's two-mesh 3.8 mm layer pair completed
10 us with near-wall/middle coupling in compact, causally buffered domains. See [experiment and evidence](docs/verification/c5_short_reaction.md).
The previous unspecified model-choice stop is superseded; C6 remains gated.
A reactive-contact boundary check was corrected to account for homogeneous
background chemistry; the stopped attempt and corrected evidence are retained.
No 3D plan or code changes belong to this session. The user confirmed the other
branch handles 3D, including GPU decisions.

```sh
# From rde_sim_starter; each new execution requires a fresh output path.
NUMBA_NUM_THREADS=2 ../.venv/bin/python short_reaction.py verify --out runs/NEW_VERIFY
NUMBA_NUM_THREADS=4 ../.venv/bin/python short_reaction.py layer --verification runs/NEW_VERIFY --out runs/NEW_LAYERS
```

Current native verification: `runs/c5_short_verify_corrected`; current layer pair:
`runs/c5_short_layers`. Inspect their saved progress/results rather than rerunning.
The independent report and pre-existing edits in `controlled_2d_progress.md` are
preserved and are not included in this session's commits.

Radial follow-on: [reviewed scope and equations](docs/plans/radial_closures_2d.md).
Implementation/tests and the controlled comparison are complete. Both new cases
ran 189.394 us/13,165 steps without invalid states; the radial closure did not
restore sustained detonation in this case.
[Evidence and status](docs/verification/radial_closures.md). Inviscid defaults remain unchanged.

## Latest flow-structure view

Static final workflow reports now use `flow_structure.py` for both GIFs.
[Feature key, definitions and reproduction](docs/verification/flow_structure_gifs.md).
The unwrapped movie exposes density edges, compressive fronts, reaction, shear
and expansion; the cylinder shows the same composite from opposite views.
Do not relabel progress=0.5 as the paper's new/old-product slip line.

## Startup and collision clarification

[Saved-field/paper review](docs/verification/startup_collision_review.md) tests the
user's opposing-wave hypothesis. At z=0.752 mm, the whole-ring reaction maximum
falls to 10.8 /s by 40 us; the prominent far-side pressure encounter occurs around
106–110 us. Higher layers still burn. This does not support cancellation of two
healthy detonations as the sole cause. The movie ends after only 1.5 experimental
reference revolutions, so later reinitiation is not excluded. Mundt Figure 2.3
and Appendix B supply startup and counter-wave examples; verified external video
links and access limits are recorded. Four relevant analytical checks passed;
all 96 source hashes match the GIF manifest. No evolution-code change or CFD rerun.

## End-on visual comparison and gas motion

[UW comparison](docs/verification/uw_visual_comparison.md) provides a 96-frame
end-on GIF of the same saved run, a labeled five-still flipbook from Mundt Fig.2.3,
original UW video links, and a direct velocity check of the pre-collision squeeze
hypothesis. Central far-side gas has essentially zero circumferential speed at
40 us, before later convergence. This does not rule out every indirect interaction.
Projection accounting, frame timing and source hashes pass; no new CFD or solver
changes. The experimental photos and computed chemical-power view are different
observables, not synchronized measurements.
