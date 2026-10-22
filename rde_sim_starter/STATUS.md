# Starter status — paper/model audit, October 22, 2026

Source accuracy, 1D propagation and the bounded Run 937 workflow are implemented.
See [the handoff](../HANDOFF.md) and [D1 results](../docs/verification/d1_propagation.md)
and [D3 investigation](../docs/verification/d3_investigation.md) for observed outcomes; completion of the time cap does not establish detonation.

**OPEN: [RDE-001](../docs/verification/run937_unresolved.md).** The 3.8 and 7.6 mm
Run 937 starts do not demonstrate sustained detonation by 189.394 microseconds.
D3 diagnostics and the initial physical reference are implemented; broader model/refinement work
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
| `experiments.py` | Frozen/reactive moving contacts and fixed-chemistry 1D spatial comparisons. |
| `reference.py` | Optional Cantera/SDToolbox CJ/ZND and independent equilibrium heat-release reference; exact CEA remains pending. |
| `plot.py` | Saved calibration, 1D fields/fronts, engine fields, multi-height candidate tracks, conversion-height histories and case comparison. No CFD calls. |
| `tests/` | Foundation/D0 coverage plus independent source refinement, injector-plane consistency, normal Mach, roundoff handling, event detection and read-only saved-output checks. |

The 1D default/half-source-step speeds are 2490.157/2490.179 m/s, compared with the
fitted 2471 m/s surrogate reference. Source accuracy is supported for the tested
states, not for arbitrary chemistry. Run 937 completed 189.394 µs without invalid
states; its weakening pressure fronts do not establish sustained detonation.
D3 adds the physical CJ/ZND reference and three-grid numerical comparisons.
Contact conversion falls from 726.44 to 289.78 J/m² across 0.5 to 0.125 mm;
1D speed remains sensitive to both mesh and fit window. No completed spatial
convergence, 2D sustained wave, whole-engine force/torque validation, wall-loss
closure, CAD or 3D work is claimed. The full 59-test suite passed during D3;
no new studies or test suite were run for the documentation-only
[paper audit](../docs/verification/mundt_model_audit.md). Production code and inputs
are unchanged. The reviewed controlled-test plan now specifies C1–C6. C1 has passed; C2 is
next; the proposed unchanged-start 0.25 mm engine case is superseded.

The authorized next implementation is [C1–C6 controlled 2D testing](../docs/plans/controlled_2d_tests.md), published on main in small verified increments. The prior automatic engine refinement is superseded.

## C1 controlled strip update

C1 passed at 0.5 mm through 95 µs: identical saved fields/fronts in 1D, multirow,
rotated and original-open controls; no invalid states; residual <4e-15. Default
suite 60 passed/one opt-in skipped. C2 formed-profile verification is next.
See [increment log](../docs/verification/controlled_2d_progress.md).

## C2 formed-wave update

Conservative initializer, jump/inventory/table checks and four bounded formed-wave
runs passed. Three meshes give 20–40 µs speeds 2478.15/2472.97/2472.07 m/s with
continued near-front reaction and isolated remote boundaries. C3 layer response
is next; Run 937 remains unresolved. See the increment log for qualifications.
