# D0 run plumbing verification — October 21, 2026

Scope: the second implementation increment, following foundation commit `6ae65ad`.
This verifies run limits, persistence, averaging and discrete conservation with
small synthetic cases. No reactive Run 937 check, physical validation or new
chemistry model is included. The inherited 95 µs 1D detonation check remains opt-in.

## Automated checks

From `rde_sim_starter`, using the existing Python 3.12 environment:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

Final suite: **34 passed, one explicitly skipped** (35 discovered). This includes
13 new tests in `tests/test_run.py` and `tests/test_budgets.py` and the 21 passing
foundation checks. A first staging run exposed a misspelled budget key in a new
test; correcting that assertion was followed by successful targeted checks and
the final full suite in the repository.

New coverage:

- All five conserved quantities close against actual open-boundary RK-weighted
  numerical fluxes and source integrals, including stored angular momentum.
  The test distinguishes both-stage quadrature from the final-stage flux alone.
- Rejected reaction stages leave the accepted state, clock and cumulative budgets
  unchanged. Total-energy reaction source is zero because chemical energy is stored.
- Three-interval cap, initial/early/final fields, bounded step timing, explicit
  missing averages, and null unsupported passage/torque quantities.
- Same-run extension to five total: no repeated history prefix, pressure averaging
  spans both segments correctly, and conserved state and flux accumulators match
  uninterrupted replay of the recorded steps **bit for bit**.
- Unsupported model choices, incompatible calibration, an existing output directory,
  changed saved inputs, changed source/environment and a second writer are rejected.
- Injected invalid RK states preserve the accepted checkpoint and failure location;
  injected bookkeeping and checkpoint-write failures preserve a resumable checkpoint.
  Resume archives partial history and fields before restoring the checkpoint prefix.
- Partial atomic-file writes do not replace a previously complete checkpoint.
- Periodic ignition-mask wrapping and a real subprocess CLI create/resume round trip.

## Recorded synthetic probe

[Machine-readable metrics](d0_run_plumbing_metrics.json) record source/package
fingerprints and the following measurements. Generated state/field/history data
are under `rde_sim_starter/runs/d0_plumbing_probe/` and excluded from Git.

The probe uses a 16 × 2 mesh, disabled chemistry, a uniform initial state and an
artificial 10 MHz reference frequency. Its 0.3/0.5 µs durations exercise I/O quickly;
these are not the Run 937 duration policy and do not represent observed passages.

| Quantity | Result |
|---|---:|
| First cap / accepted steps | 0.3 µs / 15 |
| Resumed total cap / accepted steps | 0.5 µs / 25 |
| Field snapshots across both segments | 15 |
| Initial / first nonzero snapshot | 0 / 0.04 µs |
| Averaging start / accumulated overlap | 0.055 / 0.445 µs |
| Largest conservation residual divided by initial component inventory | 6.82 × 10⁻¹⁶ |
| Rejected states in this clean probe | 0 |
| History prefix retained | Yes |
| State and native flux accumulators equal uninterrupted replay | Bitwise |

A separate synthetic open-domain test with nonuniform flow and active, mild
reaction ran 12 steps. Its maximum inventory-scaled conservation residual was
3.75 × 10⁻¹⁶. The chemical source changed reacted mass while its total-energy
component remained zero. These checks verify the discrete accounting; they do
not establish physically accurate boundary conditions or reactive-source time steps.

## Implementation and remaining limits

`solver.py` records the same face fluxes used by its update, integrated over faces
and both SSP-RK2 stages. `analyze.py` applies radial depth and mean-radius angular
weighting with storage. `run.py` owns case validation, orchestration, snapshots,
weighted pressure means, checkpoint consistency, locks and recovery. Rendering
and front tracking remain in the next D1/D2 increment.

The schema-1 config replaces inherited 1 ms end/0.4 ms averaging settings with
three expected intervals from startup and an explicitly transient averaging window.
At Run 937's 15.84 kHz, the actual caps are 189.394 µs and 315.657 µs total.
Measured separate feed states remain reference metadata; injection is driven by
the documented equivalent plenum, without simultaneously imposing measured flow.

Chemistry constants, physical energy convention and existing outlet closure are
unchanged. Flow CFL plus an optional user step cap still does not control source
accuracy automatically. Strict invalid-state rejection can expose inherited
reactive failures. The next increment must address those checks before interpreting
a reactive engine run. No wall torque, whole-engine thrust or physical CJ/ZND
validation is claimed. Exit contribution and axial Mach are scoped diagnostics.

The original config remains in `docs/archive/starter_pre_foundation.zip`; supplied
calibration/tube JSON and PNGs are unchanged. The earlier foundation verification
and hash manifest describe their historical snapshot. Living README, STATUS,
HANDOFF and the master plan status now agree on current progress.
