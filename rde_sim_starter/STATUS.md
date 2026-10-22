# Reduced 2D workflow status

The functional workflow F1–F4 is implemented on **main**. Acceptance: 122 tests passed with no skips; 16 affected checks were repeated after
review and one additional coupled wall-heating/chemistry check passed (123 distinct
passing tests). Details are recorded in [the completion report](../docs/verification/f4_workflow_completion.md).
See the [capability/verification matrix](../docs/plans/2d_workflow_completion.md).

**RDE-001 remains OPEN.** The original 3.8 and 7.6 mm Run 937 starts did not show
sustained rotating detonation by 189.394 µs. C1–C5 bounded controls and C6a's 2 µs
formed-engine benchmark are evidence within their stated limits, not a validated
engine solution. Sustaining-wave studies belong to the separate investigation;
3D belongs to the separate branch.

Implemented: strict reactive Euler/source controls; conservative formed startup;
case/calibration preflight and versioned SI contracts; bounded saved runs and
checked restart; native mass/energy/momentum/storage accounting; selected-window
exit force/Isp; opt-in adiabatic constant-Cf drag and mean-radius torque; pressure,
reaction and candidate-front inspection; PSD/rolling spectra; case-guarded pressure
comparison; saved-run sensitivity tables; offline playback, wrapped/head-end
views and checkpoint refresh; illustrative constant-inertia roll response.

The default case is still inviscid. No friction coefficient is calibrated by
default. No radial momentum/velocity, centrifugal pressure split, curvature loss,
heat loss or separate inner/outer wall states are implemented. This is a reduced
2D solver with optional gap-averaged drag, not the report's full proposed 2.5D tier.
CAD/coreless/nonuniform geometry and 3D are explicitly unsupported by this backend.

Production sensitivity campaigns, steady-wave/pressure validation and matched
measured thrust/torque comparisons remain open. Native version-2 historical runs
can be analyzed; exact restart requires their original source/environment.

Latest follow-on request: implement and evaluate the independent report's radial
closures after this workflow completion. This is a new physics increment; the
above radial omissions still describe the current implementation. No CAD work.
