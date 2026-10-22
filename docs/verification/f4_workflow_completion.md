# F4: complete saved-data 2D workflow and test audit

The single plotting entry point now supports `--workflow`: selected-window native
report, pressure PSD and rolling spectra, guarded Run 937 pressure comparison,
force/flow/budget/torque histories, optional constant-inertia roll response,
streaming field playback and labelled wrapped/head-end views. Outputs are
JSON/Markdown/CSV/PNG plus an offline HTML viewer. No web service or solver is
started by analysis. Full fields are read one snapshot at a time; only probe
rings and requested preview frames feed the displays. Numerical integrations
use the native history, never downsampled display fields.

`--follow` polls committed checkpoints and writes a new immutable report directory
only when the step/status changes. Its root HTML refreshes the latest report.
It stops when the run stops, reaches the requested end, or the optional update
limit is reached. Three consecutive incoherent-prefix reads fail explicitly.
Ctrl-C stops the preview process without signalling the CFD process.

`--compare-runs` reduces existing runs over one common time window. It records
changed case settings and recorded code/environment identities rather than calling a multi-parameter difference a pure
mesh or coefficient effect. This is reusable comparison machinery, not a new
parameter-sweep campaign or convergence claim.

## Three review passes and issues addressed

1. **Scientific claims and missing physics.** Spectra report pressure oscillations,
   bin width, conservative sampling Nyquist and cycles in the selected window.
   Linear resampling does not recover aliased content; fewer than three cycles is
   explicitly qualified. Flat or undersampled signals are unavailable. A wrapped
   cylinder and radially repeated head-end ring remain synthetic 2D views.
   Report/viewer/checklist explicitly list the absent radial closures.
2. **Silent comparison/accounting errors.** Legacy pressure overlays previously
   checked only whether stations fitted the geometry. Both reporting paths now
   check nominal geometry/operating conditions and the audited reference values;
   benchmarks do not overlay experimental means. The old reader now verifies
   the checkpoint/input hash/history prefix too, and ignores uncommitted field
   files before opening them. Torque comes from the wall source and is checked
   against storage/flux, not inferred from exit swirl alone.
3. **Failure and test quality.** Tests use exact drag and roll solutions,
   independently normalized sinusoid power, changing-frequency signals, deliberate
   input corruption, synthetic I/O failures and a subprocess run/resume/viewer
   acceptance path. A viewer import assertion excludes `solver`; file hashes
   prove analysis does not mutate native evidence. Rendering failure leaves an
   `INCOMPLETE` marker, never `COMPLETE`. Watch tests check unchanged checkpoints
   do not rerender and corrupt inputs do not wait forever.

## Validation evidence

- [F4 analytical tests](f4_analysis_tests.txt): six passed.
- [Initial workflow tests](f4_workflow_tests.txt): three passed, including the full
  CLI chain and injected output failure.
- [Compatibility/refresh tests](f4_compatibility_corrected.txt): seven passed.
- [Final full acceptance](f4_full_acceptance_tests.txt): includes the opt-in 95 µs
  reactive baseline as well as all fast tests. **122 tests passed in 333.152 s, with no skips.** The final review changes then passed all **16 affected tests** ([log](f4_final_focused_tests.txt)).
- An additional [coupled wall-heating/reaction ODE test](f4_coupled_wall_chemistry_test.txt) passed in 7.511 s: **123 distinct passing tests in total**. This checks the combined new physics, rather than assuming separate drag and chemistry tests suffice.
- [Smoke fixture report/viewer](f4_smoke_view/index.html): 16 × 2 nonreactive cells,
  explicit illustrative Cf=0.01; 0.3 µs/61 accepted steps. This is a plumbing
  benchmark, not Run 937 or a wall-coefficient recommendation.
- [Historical D1 report/viewer](f4_d1_view/index.html): read-only 100–180 µs window
  of the existing unresolved Run 937 case. This is not a new propagation result.

Two development commands used the repository root with starter-relative test
imports/paths and failed before the intended test selection. They were corrected
to the documented working directory/import path; the initial logs are retained
(`f4_wrong_cwd.txt`, `f4_compatibility_tests.txt`). These are invocation failures,
not hidden numerical passes. Final acceptance uses the documented command.

No wall coefficient was fitted, no chemistry/source integrator was replaced,
and no new engine sustaining study was launched. The independent investigation
report and the user's existing progress-document edits remain outside these commits.

See the [completion matrix](../plans/2d_workflow_completion.md) for the distinction
between completed software and outstanding physical validation/2.5D/3D work.

## Final artifact checks

Both viewers were rendered and inspected. Frequency axes use logarithmic scaling
so the low-frequency portion remains visible; fewer-than-three-cycle peaks are
labelled directly in the plot. Wrapped pressure fields close the periodic seam.
Saved field validation also rejects invalid progress, temperature, reaction rate
and fractional step IDs. The comparison export retains missing-metric reasons.
Offline playback scripts pass `node --check`; browser interaction itself was not
automated. All linked frame files and `COMPLETE` markers were verified.

The [acceptance summary](f4_acceptance_summary.json) confirms historical D1 input,
summary and native-history hashes match F1 exactly; native exit force and budget
residuals are unchanged. The D1 window residual is 4.39068e-14. In the nonreactive
smoke fixture it is 1.06632e-16, and wall-source versus storage/flux torque differs
by 4.94e-17 N m. These are accounting checks, not sustained-wave evidence.

**Subsequent user direction:** after this workflow completion, examine and add the
radial closures discussed in the independent investigation report and assess their
effect on sustainment. That is the next, separately verified physics increment;
it does not retroactively add radial terms to these saved results. CAD stays out
of scope.
