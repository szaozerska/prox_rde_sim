# prox_rde_sim

Reduced RDE simulation project. The first foundation increment is implemented;
the bounded 2D Run 937 workflow is the next increment.

## Run the foundation checks

From the project root (Python 3.12; the recorded environment was verified on macOS x86_64):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

If `.venv` is already installed, run only the last two lines. The first numerical
run compiles Numba kernels. Two threads keep these small checks inexpensive;
this is not a production performance setting or benchmark.

The default suite exercises imports, gas/energy consistency, one-step source
timing, injector limits, boundary handling, invalid-state rejection, periodic
conservation, a nonreacting Sod tube, and basic analysis reductions. The inherited
95 microsecond detonation test is opt-in, using `RDE_RUN_REACTIVE_BASELINE=1`;
it was not run in this foundation session. No 2D engine simulation has been run.

For a new surrogate calibration and its plot, from `rde_sim_starter`:

```sh
mkdir -p runs/my_calibration
../.venv/bin/python calibrate.py --out runs/my_calibration/calibration.json
../.venv/bin/python plot.py --calibration runs/my_calibration/calibration.json --out runs/my_calibration/znd.png
```

Both CLIs require an explicit new output filename. Calibration performs no
plotting. Plotting consumes saved calibration data and never advances the CFD
solver. The supplied `calib.json`, test JSON/PNGs, and `config.yaml` are preserved.

`run.py` is now safe to import, but retains its legacy 2D behavior and old defaults.
Its short-run CLI, averaging, early output, immutable inputs, and restart support
remain unfinished. `analyze.py` is a library of reductions, not the old automatic
mode/torque report. Do not use the legacy runner to claim the revision-6 workflow
is complete.

## Project documents

- [Current handoff](HANDOFF.md): completed work, verification, remaining blockers, and next steps.
- [Foundation verification](docs/verification/foundation_session.md): scope and measured baseline.
- [Current simulation plan — revision 6](first_sim_plan.md): short tests, file boundaries, and the longer-term roadmap.
- [Figure validation roadmap](docs/plans/figure_validation_roadmap.md): Chapter 3–4 comparisons and deferred campaigns.
- [Local physics and implementation review](sim_plan_review.md): review of revision 3; kept out of Git.
- [Revision 4](docs/plans/first_sim_plan_rev4.md) and [revision 3](docs/plans/first_sim_plan_rev3.md): historical, superseded plans.
- [Reference dissertation](Mundt2023.pdf).
- [Starter status](rde_sim_starter/STATUS.md).
- [Pre-session source archive](docs/archive/starter_pre_foundation.zip) and [planning handoff](docs/archive/HANDOFF_planning_20261021.md): historical reference only.
