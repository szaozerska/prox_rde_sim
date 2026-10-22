# Starter status — controlled 2D investigation

**RDE-001 remains OPEN:** the original 3.8 and 7.6 mm Run 937 starts do not
show sustained rotating detonation by 189.394 µs. Software checks and isolated
controls are not experimental validation. This session publishes only on main;
the separate 3D checkout/branch remains independent.

## Current evidence

- C1: matched 1D/multirow/rotated controls agree exactly at saved times through
  95 µs; no transverse drift or invalid states.
- C2: conservative formed profile passes jump/inventory checks and propagates
  through 40 µs on three meshes; half-source-step sensitivity is small.
- C3: 3.8 mm loses leading shock/reaction coupling on both 0.5/0.25 mm grids
  and with the aligned interface. The 15 mm formed layer retains strong
  wall/middle coupling at 40 µs on both grids. This is a bounded contrast,
  not a converged critical height or indefinite-survival claim.
- C4: 15 mm blast completes 40 µs, still reacting behind the leading shock but
  weaker/slower than the formed cases. Long-term initiation outcome is unresolved.
  Different initial energy/momentum and a reverse-going disturbance are recorded.
- C3/C4 states and native budgets are valid, with checked remote-boundary
  margins. The refined-thick speed-bound stop was corrected by audited
  continuation, preserving the original evidence and cumulative budgets.
- Numerical interface burning, physical reaction/EOS mismatch, equivalent
  injection, startup and engine outlet assumptions remain open contributors.

The full 71-test suite passed after continuation support; the controlled tests
also pass after C4 comparison plotting. Current logs and later checks are in the
[increment report](../docs/verification/controlled_2d_progress.md).

## Implemented tools

| Module | Purpose |
|---|---|
| `physics.py`, `solver.py` | Constant-gamma reactive Euler, strict state checks, source/flow caps and native RK-weighted budgets. |
| `calibrate.py` | Pure inherited-surrogate calibration; not a physical-chemistry validation. |
| `run.py`, `analyze.py` | Bounded engine runs, checked checkpoints, stored diagnostics and pure reductions. |
| `coupling.py` | Multi-height pressure/reaction candidates; no automatic detonation classifier. |
| `experiments.py`, `reference.py` | Contact/1D numerical controls and optional pinned Cantera/SDToolbox physical references. |
| `controlled.py` | Row/direction, formed-strip and finite-layer/blast controls, conservative initialization and checked continuation. |
| `plot.py` | Saved-data fields, histories and comparisons; no CFD execution. |

**Next gate: C5 model/source/resolution review.** No arbitrary chemistry change,
engine-fill increase or longer engine run follows from C3/C4. Production solver,
physics, calibration, engine driver, config and calibrated inputs are unchanged.
See the [reviewed plan](../docs/plans/controlled_2d_tests.md),
[handoff](../HANDOFF.md), [paper audit](../docs/verification/mundt_model_audit.md)
and [open issue](../docs/verification/run937_unresolved.md). Historical progress
and test counts are retained in the dated increment report, rather than competing
with this current status.
