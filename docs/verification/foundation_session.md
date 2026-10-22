# Foundation verification — October 21, 2026

Scope: the opening part of D0. The 2D Run 937 workflow is not complete and no
2D engine run was performed. The existing one-step model and supplied case
parameters were retained.

## Checks performed

- `python -m pip check`: no broken requirements.
- Foundation unittest discovery: **21 passed, 1 skipped** (22 discovered).
  The 95 microsecond inherited detonation test is explicitly opt-in and was not run.
- New invalid-state handling rejects bad inputs and intermediate RK stages without
  altering the accepted state/time. No silent pressure/density/progress repairs.
- Closed-reactor Ea=0 check agrees with `xi = 1 - exp(-k t)` within 6e-6 absolute
  progress and conserves the stored-chemical-energy formulation. This verifies a
  simple source limit, not general Arrhenius-source accuracy or induction chemistry.
- Periodic nonreacting conservation, uniform HLL fluxes, injector limiting states,
  ghost boundaries and nondimensional Sod assertions passed.
- Calibration reproduces inherited gamma/R/q/k/Ea/p1/half-reaction length to the
  asserted relative tolerance 2e-10, without mutating configuration.
- Fresh-process imports do not launch simulations, calibration, rendering or
  output writes. Matplotlib remains unloaded until a renderer is called.
- Numerical analysis checks cover a partial-step averaging window, explicit empty-
  window errors, a known exit momentum/pressure integral and both directions of an
  analytic traveling signal. This does not validate a physical wave classifier.
- Calibration CLI and plotting CLI exercised with new output paths. The Sod and
  ZND PNGs were visually inspected; labels/plots were readable with no clipping.
- Supplied configuration, calibration/test JSON and three supplied PNGs match
  [the saved SHA-256 manifest](inherited_baseline_hashes.json).

## New nonreacting Sod result

400 cells, nondimensional end time exactly 0.2, with no invalid states or repairs.

| Quantity | Computed | Exact reference | Assertion tolerance |
|---|---:|---:|---:|
| Star pressure | 0.3031368288 | 0.3031301781 | 0.003 absolute |
| Star velocity | 0.9274700177 | 0.9274526200 | 0.005 absolute |
| Shock coordinate (density-threshold estimator) | 0.84875000 | 0.85043115 | 3 cells = 0.0075 |

The shock estimator is quantized at cell centres. Its difference from the supplied
old result is not a detonation result; the new solver also stops at the exact test
end time and fixes boundary initialization. No engine performance follows from
this check.

Machine-readable result: [foundation_metrics.json](foundation_metrics.json).
The saved warm Sod artifact run took 1.301 seconds on the
local environment with two Numba threads; this excludes initial import/JIT cost
and is not an RDE runtime forecast.

## Outputs and remaining work

Generated outputs (ignored by Git) are under
`rde_sim_starter/runs/foundation_session/`: `sod_fields.npz`, `sod_metrics.json`,
`sod.png`, `calibration.json`, and `znd.png`. The supplied artifacts were not
replaced. Plotting consumes data; it does not run the solver.

The old automatic mode/torque/stability report was retired because its claims
were unsupported. Its full pre-session source is archived. The numerical FFT
reduction was retained without a strongest-peak classification claim. The legacy
2D runner was only made import-safe; output/restart/averaging/native budgets still
need work, as detailed in [HANDOFF.md](../../HANDOFF.md).

Reproduce the foundation checks from the project root:

```sh
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

Pinned packages are in [requirements.txt](../../requirements.txt); tested on
Python 3.12.0, macOS 15.7.9 x86_64. Physical CJ/ZND, two-step induction, sustained
2D propagation, convergence and measured thrust/torque validation are unperformed.
