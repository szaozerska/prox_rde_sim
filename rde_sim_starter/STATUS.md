# Starter status — D0 run plumbing, October 21, 2026

Foundation and bounded-run plumbing are implemented. Small synthetic nonreactive
cases verify output/restart. The first reactive Run 937 check is still pending.
See [the current handoff](../HANDOFF.md) and
[verification record](../docs/verification/d0_run_plumbing.md).

| Component | Current state |
|---|---|
| `physics.py` | One-step EOS/chemical energy, source, inherited equivalent injector and strict validity checks. |
| `solver.py` | HLL/MUSCL/SSP-RK2; invalid candidates rejected. Actual RK-weighted boundary/source integrals and cumulative budgets now recorded on accepted steps. Flow CFL plus optional cap; automatic source accuracy control remains pending. |
| `calibrate.py` | Pure surrogate calculations and explicit-output CLI; supplied calibration preserved. |
| `run.py` | Three-interval new-run cap, five-total resume, frozen inputs, periodic ignition masks, early fields, per-step diagnostics, transient means, atomic checkpoints and failure recovery. |
| `analyze.py` | Pure means, window weights, exit contribution, directional-spectrum reduction and storage-inclusive conservation budgets. No automatic wave/stability verdict. |
| `plot.py` | Saved calibration/Sod rendering only. Run-field rendering/front tracking remains D1/D2 work. |
| `tests/` | Foundation checks plus native open-domain budgets, short CLI/restart, immutable inputs, averaging and failure-injection tests. Opt-in 95 µs detonation baseline not rerun. |
| `config.yaml` | Explicit schema-1 model/reference/initialization/output settings. Startup included in transient means; old millisecond defaults removed. |
| Supplied JSON/PNGs | Unchanged inherited calibration/tube evidence, not fresh physical validation. |

The inherited report of 2D extinction near 90 µs has not been reproduced or repaired.
Native flux closure does not validate the inlet/outlet physics. No sustained
rotation, experimental pressure agreement, whole-engine thrust or torque is claimed.
