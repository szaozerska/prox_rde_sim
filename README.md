# prox_rde_sim

Reduced RDE simulation project. The foundation and bounded-run plumbing are
implemented. Source-accuracy checks and the first reactive Run 937 run are next.

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
production performance setting. The suite includes conservation, source/energy
algebra, boundary handling, Sod, saved-run restart and injected failure tests.
The inherited 95 microsecond detonation test is opt-in with
`RDE_RUN_REACTIVE_BASELINE=1`; it has not been rerun in these increments.
The small nonreactive runner tests are not a Run 937 propagation check.

## Saved-run interface

From `rde_sim_starter`, the following starts a reactive Run 937 case. The runner
is ready, but source-integration accuracy and inlet/outlet behavior still need the
focused D1 checks before interpreting an engine result:

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
It requires matching numerical source and package versions. Completed runs cannot
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

Defaults include startup in the transient mean. `max_step_ns` is an optional
step cap, not automatic reactive-source accuracy control. Invalid states stop the
run without clipping. Power loss can discard work after the latest checkpoint;
a full disk may prevent writing an updated summary. Restart validates the saved
state/history rather than trusting the summary alone.

`config.yaml` now names the supported model explicitly: constant annulus,
equivalent premixed plenum, inviscid walls and inherited one-step chemistry.
Separate measured feed states are reference data; the plenum boundary predicts
flow rather than also imposing the reference mass flow. The old config is retained
in the pre-foundation archive. Supplied `calib.json` and test JSON/PNGs are unchanged.

## Calibration and plotting

```sh
mkdir -p runs/my_calibration
../.venv/bin/python calibrate.py --out runs/my_calibration/calibration.json
../.venv/bin/python plot.py --calibration runs/my_calibration/calibration.json --out runs/my_calibration/znd.png
```

These commands require a new output filename. Calibration does not render;
plotting never advances the CFD solver. Run-directory field plots and front
tracking remain the D1/D2 follow-up. `analyze.py` supplies pure reductions rather
than the retired automatic mode/torque/stability report.

## Project documents

- [Current handoff](HANDOFF.md): verified progress and the next concrete step.
- [Run-plumbing verification](docs/verification/d0_run_plumbing.md).
- [Foundation verification](docs/verification/foundation_session.md): historical first-increment baseline.
- [Current simulation plan — revision 6](first_sim_plan.md).
- [Figure validation roadmap](docs/plans/figure_validation_roadmap.md): later Chapter 3–4 campaigns.
- [Local planning review](sim_plan_review.md): historical revision-3 review, excluded from Git.
- [Revision 4](docs/plans/first_sim_plan_rev4.md) and [revision 3](docs/plans/first_sim_plan_rev3.md): superseded plans.
- [Reference dissertation](Mundt2023.pdf) and [starter status](rde_sim_starter/STATUS.md).
- [Pre-foundation source archive](docs/archive/starter_pre_foundation.zip) and
  [planning handoff](docs/archive/HANDOFF_planning_20261021.md): historical reference only.
