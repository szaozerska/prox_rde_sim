# 3D modelling branch

Work in `/Users/sgfx/Desktop/Projects/prox_rde_sim_3d`, branch **3d-modelling**.
The separate original checkout belongs to the parallel 2D session. This branch
starts from investigation commit `0f435aa` (October 22, 2026, 01:35 PDT).

Follow the [3D plan](first_sim_plan.md), [plan reviews](docs/plans/3d_plan_reviews.md),
and [implementation record](docs/verification/3d_progress.md). The 3D pipeline is
an add-on; existing physics, thermochemical references, tests and figure roadmap
are retained. Installation/mesh checks do not establish sustained detonation.
Only commit and push to `3d-modelling` from this checkout.

Current direction: [revision 18](first_sim_plan.md) evaluates PeleC for Modal GPU
production, with small same-backend CPU checks and the installed detonationFoam
fallback. No separate CPU/GPU model branches. See [solver choices and speed/accuracy
tradeoffs](docs/plans/3d_literature_runtime_review.md). Modal CPU access passed;
the pinned native GPU installation smoke and G1a shock/reactor controls have passed (see [evidence](docs/verification/pelec_g0/result.json)). The current objective is measured <=2-hour
routine cases and eventual sustained-detonation design screening. Short diagnostic
propagation is not yet proof of long-term or real-engine stability.

Verified so far: pinned OpenFOAM 8/detonationFoam installation smoke; full-annulus
and core-end expansion meshes with native volume/area/quality checks. Prepare a
new mesh with `python -m rde3d.prepare --out runs3d/my_mesh`, then verify it with
`python -m rde3d.mesh_metrics runs3d/my_mesh`. Run fast add-on checks with
`python -m unittest discover -s rde3d/tests -v`. Use the existing Python environment
or install the pinned repository requirements. Native setup is documented in
[tools/openfoam](tools/openfoam/README.md). Native methane closed-reactor numerical controls now pass on CPU/H100 with
timestep/tolerance checks; their explicit thermo assumption and remaining physical
limits are in [G2 evidence](docs/verification/pelec_g2/README.md). Cold geometry,
propagation and experimental validation remain separate gates; no sustained 3D
engine result is claimed.


Native formed-wave initialization is verified, but **P3D-001 / G2b fails**:
0.2 us controls run about 15–18% too fast and do not resolve the reaction distance.
An every-step audit withdraws the earlier snapshot-only first-order probe pass.
See [G2b diagnostics](docs/verification/pelec_g2b/README.md). Do not advance to an
engine run. Repair the control buffer and compare one native transport option
before considering substantial solver work; no two-hour engine runtime is established.

The documentation below describes the inherited 2D backend at the frozen baseline.
Its unresolved Run 937 result remains open.

# prox_rde_sim

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
`RDE_RUN_REACTIVE_BASELINE=1`; it was exercised during D1 and the full 59-test D3 suite.
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
- [Current simulation plan — revision 9](first_sim_plan.md).
- [Paper/model audit](docs/verification/mundt_model_audit.md): checked assumptions and requirements before new studies.
- [Figure validation roadmap](docs/plans/figure_validation_roadmap.md): later Chapter 3–4 campaigns.
- Local `sim_plan_review.md`: historical revision-3 review, retained locally and excluded from Git.
- [Revision 4](docs/plans/first_sim_plan_rev4.md) and [revision 3](docs/plans/first_sim_plan_rev3.md): superseded plans.
- [Reference dissertation](Mundt2023.pdf) and [starter status](rde_sim_starter/STATUS.md).
- [Pre-foundation source archive](docs/archive/starter_pre_foundation.zip) and
  [planning handoff](docs/archive/HANDOFF_planning_20261021.md): historical reference only.

Native control results and failure root causes: [G1a report](docs/verification/pelec_g1/README.md). No methane or sustained 3D detonation has yet been validated.


Native geometry/static checks and regular-grid MOL direction/refinement checks
pass; see [G1b evidence](docs/verification/pelec_g1b/README.md). Full dynamic EB,
AMR and reacting-engine gates remain open.
