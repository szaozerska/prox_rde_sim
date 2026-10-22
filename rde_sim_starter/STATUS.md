# Starter status — foundation increment, October 21, 2026

The opening part of D0 is implemented. No 2D RDE run has been performed.
See [the current handoff](../HANDOFF.md) and [verification record](../docs/verification/foundation_session.md).

| Component | Current state |
|---|---|
| `physics.py` | Extracted one-step EOS/chemical energy, source rate, injector law, interior conversion and validity scan. No new chemistry model. |
| `solver.py` | Original HLL/MUSCL/SSP-RK2 retained. Ghost conversion fixed, supported boundaries checked, invalid initial/stage/final states rejected without clipping or advancing the accepted state. Optional step cap supports exact test end times. |
| `calibrate.py` | Pure surrogate calculations plus explicit-output CLI. Same supplied calibration reproduced. No rendering or file reads on import. |
| `run.py` | Import-safe legacy 2D runner. Short-run output, averaging, native budgets, checkpoints/restart and bounded run orchestration remain unfinished. |
| `analyze.py` | Pure means/window weights, planar exit contribution and directional-spectrum reduction. Old automatic classification/torque/stability report retired; its source is archived. Full short-run analysis remains future work. |
| `plot.py` | Explicit rendering functions; CLI for saved surrogate calibration. No simulation calls. Full field/run report comes later. |
| `tests/` | 21 passing foundation tests; one opt-in 95 microsecond detonation test not run. |
| `test_1d.py` | Compatibility runner for the same `tests/test_solver.py`; no duplicate numerical tests or import side effects. |
| `config.yaml`, supplied JSON/PNGs | Unchanged inherited inputs/evidence. Old 1 ms duration and 0.4 ms averaging start are not current run-policy defaults. |

The inherited report of 2D extinction near 90 microseconds has not been reproduced
or repaired. No sustained detonation, thrust, or torque validation is claimed.
