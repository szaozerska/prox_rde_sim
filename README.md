# prox_rde_sim

**2026-10-25: new 2D backend work uses PeleC/PelePhysics/CVODE.**
The existing custom one-step solver is preserved unchanged and remains runnable.
This is an integration transition, not a resolved sustainment result. See the
[selection, rollback and verification plan](docs/plans/pelec_2d_transition.md).


Reduced RDE simulation project. Foundation, bounded-run persistence, reactive-source
checks and saved-run plots are implemented. D2 adds full-height reaction diagnostics,
periodic pressure-peak tracks and an explicit startup comparison. D3 adds physical
CJ/ZND references, contact controls, spatial comparisons and diagnostic graphs.
See [D3 results](docs/verification/d3_investigation.md) for numerical evidence and
[the paper/model audit](docs/verification/mundt_model_audit.md) for the checked
physics and construction assumptions. No new studies were run for the audit.

**Known unresolved result: reduced Run 937 does not demonstrate sustained detonation in either
of the tested starts (3.8 or 7.6 mm initial layer, 189.394 microseconds).** Numerical
checks pass, but the broader physical-model/refinement work is incomplete and the
sustained-wave milestone is not met. See [RDE-001](docs/verification/run937_unresolved.md)
for the exact cases, evidence, candidate causes and criteria for a fix. D0-D3 are
short development increments, not completion of the broader physics stages.

The [quarter-length chemistry experiment](docs/verification/c5_short_reaction.md)
now passes its reactor/planar/contact checks and retains near-wall/middle
shock-associated reaction in a 3.8 mm isolated layer through 10 us on two meshes.
This is an explicit surrogate test variant, not a solved rotating-engine case.
The [formed-engine initializer and bounded benchmark](docs/verification/c6a_functional_pipeline.md)
are implemented and tested (2 us, 556 steps, zero invalid states). The sustaining-wave investigation is
assigned to a separate chat; after finishing 2D functionality, this branch now
adds the user-requested radial-wall closures and their controlled comparison.

## Directional startup

The default `config.yaml` now launches a finite +theta formed detonation profile,
including its laboratory-frame tangential momentum. Set `initialization.direction`
to `-theta` to reverse the launch. This is a surrogate for the wave after launch,
not a simulated pre-detonator tube. Continuous injection remains axial.
The previous default is preserved in `cases/run937_hotpatch.yaml`.
`cases/run937_radial_directional.yaml` is matched to the original radial GIF case
except for startup. Both use the existing `calib.json`; no chemistry retuning.
See [comparison protocol and verification status](docs/verification/directional_startup.md).

## Complete 2D software workflow

The functional workflow is implemented through F4. Start with the
[completion matrix](docs/plans/2d_workflow_completion.md) and
[test/acceptance report](docs/verification/f4_workflow_completion.md).
Sustained Run 937 detonation and predictive performance remain unresolved.

A fast software demonstration (from `rde_sim_starter`; use fresh output names):

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --preflight --case cases/workflow_smoke.yaml
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --case cases/workflow_smoke.yaml --benchmark-us 0.3 --out runs/my_workflow_smoke
../.venv/bin/python plot.py --workflow runs/my_workflow_smoke --start-us 0.055 --end-us 0.25 --frames 3 --inertia-kg-m2 0.01 --out ../reports/my_workflow_smoke
```

Open `reports/my_workflow_smoke/index.html`. This nonreactive 16 × 2 fixture tests
software plumbing; it is not a physical engine case. Reports contain native
budgets/loads, explicit missing-data reasons, field playback, spectral windows,
CSV/JSON exports and provenance. Positive inertia enables only an illustrative
constant-inertia response when wall torque is modeled.

For an existing running native case, use a separate terminal:

```sh
../.venv/bin/python plot.py --workflow runs/EXISTING_RUN --follow --start-us 0 --refresh-seconds 30 --frames 4 --out ../reports/live_preview
```

The preview updates only at committed checkpoints and stops when the run stops.
`--max-updates 3` bounds preview updates; Ctrl-C stops the viewer, not the solver.
Native CFD is stopped with Ctrl-C in its own terminal and resumed with
`../.venv/bin/python run.py --resume runs/EXISTING_RUN`; ordinary engine runs
extend from three to five total expected intervals. Completed development
benchmarks retain their separate cap and cannot become engine studies by resume.

For sensitivity comparisons, add `--compare-runs runs/SECOND_RUN ...` to a static
`--workflow` command. Every run must cover the full selected window. The CSV/JSON
records changed settings and flags confounded comparisons; no CFD is launched.
Full native windows remain available through `window_report.py` without reading
fields. The existing `--coupling` option provides candidate front tracks and
multi-height reaction inspection; spectra alone do not classify detonation.

**Radial physics:** the default remains inviscid. The optional `annular_closure`
reconstructs inner/outer pressure using radial equilibrium, applies separate wall
drag, and supports Reynolds-analogy heat exchange with explicit wall temperatures
and recovery factor. Radial velocity/momentum, wave detachment and calibrated
curvature losses remain unresolved. Wrapped/head-end views add no physics.
See the [reviewed equations and assumptions](docs/plans/radial_closures_2d.md) and
[completed comparison with plots](docs/verification/radial_closures.md). Both new
cases completed 189.394 us with no invalid states; these closures did not restore
sustained rotating detonation in the original case.

Named exploratory cases hold the original D1 mesh, chemistry and startup fixed:
`cases/run937_wall_control.yaml` disables the centrifugal split;
`cases/run937_radial.yaml` enables it. Both use explicitly assumed Cf=0.005,
Tw=300 K, analogy factor=1 and recovery factor=0.9; these are not Run 937 fits.
From `rde_sim_starter` (fresh output names):

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --preflight --case cases/run937_radial.yaml
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --case cases/run937_wall_control.yaml --out runs/my_wall_control
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --case cases/run937_radial.yaml --out runs/my_radial
../.venv/bin/python radial_study.py --runs runs/d1_run937 runs/my_wall_control runs/my_radial --out ../reports/my_radial_comparison
```

Native run directories are local and Git-ignored. If the historical D1 directory
is unavailable, supply the two new directories only. The study reader preserves
absolute reaction magnitudes and source budgets; it does not automatically label
pressure pulses as detonations. Existing window/workflow reports also accept the
new cases. Saved snapshots include `inner_pressure`/`outer_pressure` in Pa, labeled
as reconstructions. Wall heat and actual-radius traction integrals are retained
separately from the solver's mean-radius angular balance.

## Run the fast checks

From the project root (Python 3.12; verified on macOS x86_64):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

With the existing environment, use only the last two lines. Numba compiles kernels
on first use. Two threads keep these small tests inexpensive; this is not a
production performance setting. The suite includes conservation, Arrhenius source convergence against an independent
ODE, boundary-plane checks, Sod, restart/failure handling, and read-only plotting.
The 95 microsecond detonation test is opt-in with
`RDE_RUN_REACTIVE_BASELINE=1`; it also passed in the final 122-test F4 acceptance run (no skips). Final review added one coupled-physics test, for 123 distinct passing tests.
The small nonreactive runner tests are not a Run 937 propagation check.

## D3 investigation and graphs

The physical reference and the existing thickened surrogate remain separate.
D3 quantifies thermodynamic/reaction-length differences, contact mixing and
1D grid/window sensitivity; it does not resolve the 2D sustained-wave issue.
[The report](docs/verification/d3_investigation.md) includes five figures.
[The revised plan](first_sim_plan.md) selects the reviewed [C1–C6 controls](docs/plans/controlled_2d_tests.md): multirow/direction, formed-profile, layer survival, then initiation isolation before a justified engine revision. This session publishes 2D work on main; independent 3D work uses its own branch.

Optional physical-reference dependencies are isolated from the pinned CFD stack.
From the repo root, install once into a new `.reference-deps` directory:

```sh
.venv/bin/python -m pip install --only-binary=:all: --no-deps --target .reference-deps -r requirements-reference.txt
cd rde_sim_starter
PYTHONPATH=../.reference-deps ../.venv/bin/python reference.py --out runs/new_reference
../.venv/bin/python plot.py --reference runs/new_reference --out runs/new_reference/plots
```

Cantera/GRI-Mech and unmodified, hash-pinned SDToolbox provide CJ/frozen-shock/ZND
references. The heat-release calculation is an independent equilibrium cross-check;
NASA CEA has not been executed. The first mechanism load can take a minute or two
on this host. Inputs, source/mechanism hashes, versions, warnings, solver checks
and nominal/strict tolerance results are retained with each reference.

The numerical experiments use the original chemistry, without Cantera:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python experiments.py contact --out runs/new_contact
NUMBA_NUM_THREADS=2 ../.venv/bin/python experiments.py refinement --out runs/new_refinement
../.venv/bin/python plot.py --experiments runs/new_contact --out runs/new_contact/plots
../.venv/bin/python plot.py --experiments runs/new_refinement --out runs/new_refinement/plots
```

These commands create six contact controls (20 µs) or three 1D grids (95 µs).
All spacings keep the chemistry fixed. `test_1d.py --dx-mm 0.125 --out ...`
selects one spacing explicitly. Existing destinations are rejected; figures read
saved arrays and need no optional chemistry package. Current local artifacts are
`runs/d3_contact`, `runs/d3_refinement` and `runs/d3_reference`.

## Saved-run interface

From `rde_sim_starter`, the following starts a reactive Run 937 case. The runner
uses the tested source cap and consistent injector-plane closure. The resulting
short record is still a development check, not validated engine performance:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --case config.yaml --calibration calib.json --out runs/run937_first
```

A new run stops at **three expected passage intervals from startup**: 189.394 µs
at the saved 15.84 kHz reference frequency. That frequency budgets duration;
it neither imposes wave count nor detects real passages. No existing output
directory is overwritten. If useful, extend that same saved run to five intervals
**total**, 315.657 µs:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --resume runs/run937_first --test-passages 5
```

After a failure/interruption, `--resume ... --test-passages 3` continues toward
the original cap. Resume uses saved inputs, not the current config or calibration.
It requires matching numerical source and package versions. D0 checkpoints cannot
be resumed with D1 source changes; retain their original code for replay. Completed runs cannot
be extended beyond five intervals by this development CLI. Locking currently
uses Unix `flock` (macOS/Linux).

Each run contains:

- `inputs.json`: frozen case, calibration, raw CLI input text, resolved geometry,
  initialization energy change, implementation/environment hashes and units.
- `fields/step_*.npz`: initial, early, cadence and final pressure/reaction/flow fields;
  field previews use float32, while checkpoints retain the float64 conserved state.
- `history.jsonl`: one initial row and one row per accepted step, station pressures,
  actual RK-weighted boundary/source integrals, storage residuals, exit contribution
  and axial-Mach diagnostics. Exit contribution is not whole-engine thrust.
- `checkpoint.npz`: atomic replacement with state, clock, flux/averaging accumulators
  and history position. Restart preserves post-checkpoint partial output under
  `recovery/` before restoring the checkpoint's history prefix.
- `summary.json`: completion/failure status, transient pressure mean and conservation
  budgets. Empty averaging windows have `available: false` and a null profile.
  Observed passage count and engine torque remain null until supported analysis/models exist.

Defaults include startup in the transient mean. `source_cfl: 0.05` bounds the
one-step source slope and gives a 14.455 ns maximum source step for this calibration.
`max_step_ns` can impose an additional cap. Significant invalid states stop the run;
progress excursions up to 64 float64 epsilons are recorded without changing the
conserved state. There are no state floors or repairs. Work after the latest complete checkpoint may need to be repeated;
a full disk may prevent writing an updated summary. Restart validates the saved
state/history rather than trusting the summary alone. Checkpoints retain the
maximum accepted progress excursion at float64 roundoff scale.

`config.yaml` now names the supported model explicitly: constant annulus,
equivalent premixed plenum, inviscid walls and inherited one-step chemistry.
Separate measured feed states are reference data; the plenum boundary predicts
flow rather than also imposing the reference mass flow. A converging opening uses
a sonic plane when choked; pressure is accounted for on open and closed face areas. The old config is retained
in the pre-foundation archive. Supplied `calib.json` and test JSON/PNGs are unchanged.

## Calibration and plotting

```sh
mkdir -p runs/my_calibration
../.venv/bin/python calibrate.py --out runs/my_calibration/calibration.json
../.venv/bin/python plot.py --calibration runs/my_calibration/calibration.json --out runs/my_calibration/znd.png
```

These commands require a new output filename. Calibration does not render;
plotting never advances the CFD solver. To save a 1D check and render its fields:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python test_1d.py --out runs/my_tube --source-cfl 0.05
../.venv/bin/python plot.py --tube runs/my_tube --out runs/my_tube/plots
```

To render an existing engine run (also works on a failed or checkpointed prefix):

```sh
../.venv/bin/python plot.py --run runs/run937_first --out runs/run937_first/plots
```

This creates `fields.png`, `space_time.png`, `diagnostics.png`, and `analysis.json`.
It uses saved pressure/progress/reaction fields and native histories. Pressure
crossings use explicit hysteresis thresholds; they are candidates for inspection,
not confirmed detonation passages or a mode count. All means include the recorded
window and startup status. `analyze.py` supplies pure reductions, not an automatic
mode/torque/stability verdict.

D1 outputs are under `runs/d1_tube_default`, `runs/d1_tube_half_step`, and
`runs/d1_run937`. Bulk runs remain Git-ignored. Selected figures and compact metrics
are retained in `docs/verification/` so the evidence can accompany the source.

## Pressure/reaction diagnostics

From `rde_sim_starter`, inspect saved fields throughout the chamber and at several
axial ring heights:

```sh
../.venv/bin/python plot.py --coupling runs/d1_run937 --out runs/my_coupling
```

This creates `reaction_fields.png`, `axial_evolution.png`, `ring_tracks.png` and
`coupling.json`. Optional `--heights-mm 1 4 8 16` selects ring positions; outputs
record the actual cell-center heights. Chemical-to-thermal conversion is computed
as `rho*q*reaction_rate`. It is a diagnostic of stored chemical energy conversion,
not a second source added to the total-energy equation.

Pressure peaks use explicit height/prominence thresholds and periodic distances.
Tracking breaks at missing frames, ambiguous matches and insufficient temporal
sampling. Peaks, tracks, proximity to reaction and high-pressure conversion
fractions do not automatically identify detonation passages or modes.

D2 saves one controlled startup variant with a 7.6 mm initial layer. Its ignition
patch height and initialization energy also increase under the existing
initializer. All chemistry, numerical settings and boundaries match D1:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --case cases/run937_fill_7p6mm.yaml --out runs/new_startup_variant
../.venv/bin/python plot.py --coupling runs/d1_run937 --compare-run runs/new_startup_variant --out runs/my_comparison
```

The comparison lists every changed case input, calibration/source equality and
both initialization energies. It renders both cases plus `comparison.png` and
`comparison.json`. No simulation is advanced by these plotting commands.
The completed experiment is under `runs/d2_fill_7p6mm`; selected figures and
metrics are retained with [the D2 report](docs/verification/d2_coupling.md).

## Project documents

- [Current handoff](HANDOFF.md): verified progress and the next concrete step.
- [RDE-001: Run 937 sustained detonation unresolved](docs/verification/run937_unresolved.md).
- [D3 physical reference, contact and spatial investigation](docs/verification/d3_investigation.md).
- [D2 coupling diagnostics and startup comparison](docs/verification/d2_coupling.md).
- [D1 propagation verification](docs/verification/d1_propagation.md).
- [Run-plumbing verification](docs/verification/d0_run_plumbing.md).
- [Foundation verification](docs/verification/foundation_session.md): historical first-increment baseline.
- [Current simulation plan — revision 10](first_sim_plan.md).
- [Paper/model audit](docs/verification/mundt_model_audit.md): checked assumptions and requirements before new studies.
- [Figure validation roadmap](docs/plans/figure_validation_roadmap.md): later Chapter 3–4 campaigns.
- Local `sim_plan_review.md`: historical revision-3 review, retained locally and excluded from Git.
- [Revision 4](docs/plans/first_sim_plan_rev4.md) and [revision 3](docs/plans/first_sim_plan_rev3.md): superseded plans.
- [Reference dissertation](Mundt2023.pdf) and [starter status](rde_sim_starter/STATUS.md).
- [Pre-foundation source archive](docs/archive/starter_pre_foundation.zip) and
  [planning handoff](docs/archive/HANDOFF_planning_20261021.md): historical reference only.

## Formed-charge functional benchmark

The named quarter-length surrogate case preserves the original baseline. From
`rde_sim_starter`:

```sh
NUMBA_NUM_THREADS=4 ../.venv/bin/python run.py \
  --case cases/run937_formed_lhalf_0p25mm.yaml \
  --calibration cases/run937_formed_lhalf_0p25mm.calib.json \
  --benchmark-us 2 --out runs/new_formed_benchmark
../.venv/bin/python plot.py --run runs/new_formed_benchmark --out runs/new_formed_benchmark/plots
```

This mode is capped at 2 us and labelled as a development benchmark in saved
outputs/plots. It cannot demonstrate sustained rotation. Resume an interrupted
benchmark using only `--resume <directory>`; it keeps the original cap. Engine
passage runs retain their separate three/five-interval policy. The finite charge
has an explicitly recorded trailing jump; it is not a steady periodic solution.

## Reports over a selected saved window

F1 reports native conservation budgets, storage, pressure-station means and
annulus-exit force from existing results. From `rde_sim_starter`:

```sh
../.venv/bin/python window_report.py --run runs/c6a_formed_benchmark \
  --start-us 0.55 --end-us 1.75 --out ../reports/c6a_selected_window
```

The new output directory must be outside the saved run. JSON and Markdown retain
run/input provenance, partial-step interpolation and unavailable-data reasons.
No solver execution or full-field loading is needed. Force and effective Isp are
qualified transient annulus-exit quantities, not validated whole-engine thrust,
Isp or evidence of sustained detonation. See [F1 tests and examples](docs/verification/f1_window_reporting.md).

## Case preflight and portable metadata

From `rde_sim_starter`, run `../.venv/bin/python run.py --preflight --case config.yaml`.
This validates calibration and initialization, prints the versioned SI geometry,
backend capabilities and result interpretation, and does not advance CFD. It
allocates the selected mesh. Saved native inputs retain this contract and the
original experimental stream references. Only manual constant-annulus geometry
is supported; CAD/nonuniform/coreless input is rejected. See
[F2 evidence](docs/verification/f2_contracts.md).

## Optional wall friction

Set `model.walls: constant_cf` and an explicit `model.wall_cf` in a separate case
file, then recalibrate if the chemistry/operating reference changed. Inviscid is
still the default. The adiabatic drag closure saves native momentum sources and
provides mean-radius wall torque with angular storage/flux checks. No coefficient
is calibrated by default. It does not add radial dynamics, heat loss, centrifugal
pressure split or curvature losses. See [F3 verification](docs/verification/f3_wall_friction.md).

## Final propagation GIFs

Final static workflow reports now include timed **unwrapped and wrapped GIFs**,
each pairing pressure with reaction on fixed scales. The standalone command is
`../.venv/bin/python animate.py --run runs/radial_active --out ../reports/radial_movie`
from `rde_sim_starter`. See the [movies and fuel-balance explanation](docs/verification/propagation_gifs.md).
This case continues to receive fresh mixture; it does not stop because fuel is
exhausted. The saved window ends at 189.394 us with RDE-001 still open.

## Shock, interface and slip-line diagnostics

The default final-report GIFs now show **numerical schlieren, compression fronts,
reaction zones, fresh/product interfaces and shear/contact candidates** rather
than just pressure panels. [Open the flow-structure movies and feature key](docs/verification/flow_structure_gifs.md).
The standalone exporter is `flow_structure.py --run runs/radial_active --out ../reports/flow_structures`
from `rde_sim_starter` with the project Python. The paper's new/old-product slip
line is distinct from the fresh/product boundary; candidate features are labeled
without claiming a steady detonation that this saved case does not demonstrate.
