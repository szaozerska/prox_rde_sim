# prox_rde_sim

Reduced RDE simulation project. Foundation, bounded-run persistence, reactive-source
checks and saved-run plots are implemented. D2 adds full-height reaction diagnostics,
periodic pressure-peak tracks and an explicit startup comparison. See the D1/D2
verification records for results and their limits.

**Known unresolved result: reduced Run 937 does not sustain detonation in either
of the tested starts (3.8 or 7.6 mm initial layer, 189.394 microseconds).** Numerical
checks pass, but the broader physical-model/refinement work is incomplete and the
sustained-wave milestone is not met. See [RDE-001](docs/verification/run937_unresolved.md)
for the exact cases, evidence, candidate causes and criteria for a fix. D0-D2 are
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
`RDE_RUN_REACTIVE_BASELINE=1`; it was exercised during D1 and the full 51-test D2 suite.
The small nonreactive runner tests are not a Run 937 propagation check.

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
- [D2 coupling diagnostics and startup comparison](docs/verification/d2_coupling.md).
- [D1 propagation verification](docs/verification/d1_propagation.md).
- [Run-plumbing verification](docs/verification/d0_run_plumbing.md).
- [Foundation verification](docs/verification/foundation_session.md): historical first-increment baseline.
- [Current simulation plan — revision 6](first_sim_plan.md).
- [Figure validation roadmap](docs/plans/figure_validation_roadmap.md): later Chapter 3–4 campaigns.
- Local `sim_plan_review.md`: historical revision-3 review, retained locally and excluded from Git.
- [Revision 4](docs/plans/first_sim_plan_rev4.md) and [revision 3](docs/plans/first_sim_plan_rev3.md): superseded plans.
- [Reference dissertation](Mundt2023.pdf) and [starter status](rde_sim_starter/STATUS.md).
- [Pre-foundation source archive](docs/archive/starter_pre_foundation.zip) and
  [planning handoff](docs/archive/HANDOFF_planning_20261021.md): historical reference only.
