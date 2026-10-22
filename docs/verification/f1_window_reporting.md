# F1: native saved-window reporting

October 22, 2026. Functional 2D increment on main; RDE-001 remains open and its
sustaining-wave investigation stays in the separate chat/branch. No engine
simulation or parameter study was launched for this increment.

## Delivered interface

`rde_sim_starter/window_report.py` generates JSON and readable Markdown for an
explicit start/end time. It uses the existing native runner's format 2 inputs,
summary, history and small checkpoint metadata. It reads neither full field
snapshots nor the checkpoint solution array, imports no solver, and never
advances CFD. Original numerical source files and checkpoint fingerprints are
unchanged, so the historical runs remain usable under their existing restart
rules. Other backend/study formats require an explicit adapter.

From `rde_sim_starter`:

```sh
../.venv/bin/python window_report.py --run runs/c6a_formed_benchmark \
  --start-us 0.55 --end-us 1.75 --out ../reports/c6a_selected_window
```

Output must be a new directory outside the saved run. It contains `report.json`
and `report.md`. No silent overwrite, truncation to available duration or
replacement of missing data with zero. Invalid, nonfinite or out-of-record
windows are rejected. The report retains source/input/history hashes, the
committed step, run status, invalid-state count and benchmark/engine mode.

## Three review passes and decisions

1. **Physical accounting.** History boundary/source integrals already include
   radial depth and RK weights. Do not multiply by gap again or substitute
   cell-centre flux estimates. Compute exit impulse as the top-face integrated
   axial momentum flux minus ambient pressure × annulus area × window duration.
   Reconstruct that same exit impulse independently from side/inlet transport,
   source and **minus axial momentum storage**. They are two estimates of the
   same contribution, never additive forces. The report retains mass, both
   momentum components, total energy, reacted mass and angular storage/residual.
   Chemical conversion is q times the reacted-mass source, not an additional
   total-energy source. No mechanical torque is reported without wall tractions.
2. **Time-window semantics.** Endpoint times can cut accepted steps. Prorate
   each saved step integral by its overlap; interpolate inventory linearly
   between its accepted endpoints. Label that approximation and the number of
   partial steps. At aligned boundaries the native accounting is retained.
   At partial boundaries closure checks the interpolation, not a separately
   evolved solution. Pressure and cell-centre force samples are explicitly
   step-end rectangle averages. No stationary-window or wave-stability label is
   inferred. Effective Isp uses exit impulse divided by the net injected mass
   in exactly the same window and g0; zero/reverse net injection makes it
   unavailable. It is an annulus-exit transient diagnostic, not validated
   whole-engine Isp or measured thrust.
3. **Silent-failure review.** Verify consecutive step IDs, finite increasing
   timestamps, and agreement between stored dt and consecutive timestamps.
   Validate every supplied numeric field before reduction. Compare input hash,
   history byte boundary, time and step to checkpoint metadata; ignore only the
   uncommitted tail. Reject changes observed during reading. Missing native
   columns produce explicit unavailable results, while independent saved
   station/cell estimates remain available. A corrupted source integral must
   produce a failed budget-closure flag, not a reconstructed pass. Near-zero
   net momentum uses the dimensional sqrt(mass × total energy) reference rather
   than dividing roundoff by an almost-zero net momentum. Raw dimensional
   residuals and all scaling factors remain available.

The reader checks bookkeeping consistency, not a cryptographic signature of
all solution data. Reports do not replace solver-state checks, numerical
sensitivity studies or physical validation. Availability is conservative: a
native column missing anywhere in the committed prefix disables its dependent
reduction, even if the requested window avoids that row.

## Tests and results

Twelve focused tests passed in 6.682 s. They cover an independent uniform-exit
force calculation, nonzero storage, effective-Isp denominator/sign, uneven time
steps, partial overlap, invariance to splitting constant-flux intervals, zero
and negative force, missing columns, corrupt budgets, NaN/infinity, wrong shapes,
bad timestep accounting and zero-net-momentum scaling. Saved-run tests inject an
uncommitted tail, prohibit solver calls/full-array reads, hash inputs/outputs to
confirm they stay unchanged, reject altered inputs/truncated history, and check
CLI output/non-overwrite rules. The first targeted run found a scope mistake in
the test's metadata-only wrapper; it was corrected before the passing run. This
was a test fixture error, not a numerical implementation failure.

Full regression: **98 passed, one opt-in long propagation test skipped** (99
collected, 186.530 s under shared-machine load). After the final Markdown additions,
the CLI/output and import checks also passed (2 tests, 13.625 s). Evidence:
[focused tests](f1_focused_tests.txt), [full suite](f1_tests.txt),
[final output checks](f1_output_tests.txt). Expected rejection messages in the
logs are the deliberate overwrite/invalid-option tests. Existing Matplotlib
deprecation/empty-legend warnings are unrelated to F1 numerical reductions.

## Saved-data examples

- [C6a window, 0.55–1.75 us](f1_c6a_window/report.md): exercises two partial
  steps on the 1,091,290-cell benchmark, with no new CFD. Native and
  storage-corrected exit means are 186.36946 N; the cell-centre estimate is
  203.95718 N. The difference illustrates why a reconstructed cell flux must
  not replace the numerical flux used in conservation. Scaled residual <2.86e-15.
- [Historical D1 window, 100–180 us](f1_d1_window/report.md): works from the
  earlier checkpoint without restarting old solver code. Native exit mean is
  482.54698 N; mean inlet/outlet flows are 0.26730581/0.41516461 kg/s and mass
  storage decreases by 1.18287e-5 kg. Scaled residual <4.40e-14. This failed
  sustained-wave case can still have a nonzero exit momentum/pressure
  contribution: the numbers do **not** establish successful detonation or
  validate thrust against Mundt. The native run status `completed_limit` means
  its duration cap was reached, not that the physical target was achieved.

The different windows and initial states are not a model-improvement comparison.
The reports preserve their own inputs, status and numerical-versus-physical
qualifications. Reuse these outputs without rerunning simulation for formatting.

## Next increment

F2: minimal versioned geometry/result metadata for the supported constant
annulus, preserving units/provenance and rejecting unsupported geometry. Keep
this small and verify dimensions/areas and capability errors with analytical
fixtures. No CAD mesher, plugin framework, 3D work or sustaining-wave campaign
is implied by F1 completion.
