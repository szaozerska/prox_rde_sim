# Starter status — D2 coupling diagnostics, October 21, 2026

Source accuracy, 1D propagation and the bounded Run 937 workflow are implemented.
See [the handoff](../HANDOFF.md) and [D1 results](../docs/verification/d1_propagation.md)
and [D2 comparison](../docs/verification/d2_coupling.md) for observed outcomes; completion of the time cap does not establish detonation.

**OPEN: [RDE-001](../docs/verification/run937_unresolved.md).** The 3.8 and 7.6 mm
Run 937 starts do not demonstrate sustained detonation by 189.394 microseconds.
D2 diagnostic work is implemented; the broader physics/reference/refinement work
is incomplete and the sustained-wave milestone is not met. The issue record
specifies candidate causes and checks needed to claim a fix.

| Component | Current state |
|---|---|
| `physics.py` | One-step EOS/chemical energy/source; global source-slope cap; roundoff-aware validity; consistent sonic/pressure-matched injector plane and open/closed area pressure. |
| `solver.py` | HLL/MUSCL/SSP-RK2, strict significant-state rejection, unchanged conserved state at tolerated progress roundoff, actual RK-weighted budgets. Flow and source step caps. |
| `calibrate.py` | Pure surrogate calculation; inherited calibration and chemistry parameters preserved. |
| `run.py` | Bounded three-interval run and five-total resume, frozen inputs, snapshots, native probe/station histories, means, failure recovery, version-2 checkpoints. |
| `test_1d.py` | Saved 95 µs propagation experiment plus compatibility test entry point; common initializer used by opt-in test. |
| `analyze.py` | Pure reductions, conservation, checked saved-run reader and hysteretic pressure arrivals. No detonation classifier. |
| `coupling.py` | Saved full-height chemical-conversion diagnostics, periodic pressure-peak candidates, conservative track association and explicit case-input comparison. No detonation classifier. |
| `plot.py` | Saved calibration, 1D fields/fronts, engine fields, multi-height candidate tracks, conversion-height histories and case comparison. No CFD calls. |
| `tests/` | Foundation/D0 coverage plus independent source refinement, injector-plane consistency, normal Mach, roundoff handling, event detection and read-only saved-output checks. |

The 1D default/half-source-step speeds are 2490.157/2490.179 m/s, compared with the
fitted 2471 m/s surrogate reference. Source accuracy is supported for the tested
states, not for arbitrary chemistry. Run 937 completed 189.394 µs without invalid
states; its weakening pressure fronts do not establish sustained detonation.
No spatial convergence, physical CJ/ZND, whole-engine force/torque validation,
wall-loss closure, CAD or 3D work is claimed.
