# Reduced 2D workflow status

The functional workflow F1–F4 is implemented on **main**. Acceptance: 122 tests passed with no skips; 16 affected checks were repeated after
review and one additional coupled wall-heating/chemistry check passed (123 distinct
passing tests). Details are recorded in [the completion report](../docs/verification/f4_workflow_completion.md).
See the [capability/verification matrix](../docs/plans/2d_workflow_completion.md).

**RDE-001 remains OPEN.** The original 3.8 and 7.6 mm Run 937 starts did not show
sustained rotating detonation by 189.394 µs. C1–C5 bounded controls and C6a's 2 µs
formed-engine benchmark are evidence within their stated limits, not a validated
engine solution. The broader sustaining-wave study belongs to the separate investigation;
3D belongs to the separate branch.

Implemented: strict reactive Euler/source controls; conservative formed startup;
case/calibration preflight and versioned SI contracts; bounded saved runs and
checked restart; native mass/energy/momentum/storage accounting; selected-window
exit force/Isp; opt-in adiabatic constant-Cf drag and mean-radius torque; pressure,
reaction and candidate-front inspection; PSD/rolling spectra; case-guarded pressure
comparison; saved-run sensitivity tables; offline playback, wrapped/head-end
views and checkpoint refresh; illustrative constant-inertia roll response.

The default case is still inviscid. No friction coefficient is calibrated by
default. An opt-in `annular_closure` now reconstructs separate wall pressures
from radial equilibrium and applies per-wall drag and optional heat exchange.
Acceptance passed (130 full-suite tests plus two additional tests; 132 distinct).
The matched 189.394 us engine comparison is complete: zero invalid states,
no restored sustained detonation in this case. See [results](../docs/verification/radial_closures.md). Radial
momentum/velocity, empirical curvature loss and inner-wall detachment are not
resolved. See the [reviewed closure plan](../docs/plans/radial_closures_2d.md).
CAD/coreless/nonuniform geometry and 3D are explicitly unsupported by this backend.

Production sensitivity campaigns, steady-wave/pressure validation and matched
measured thrust/torque comparisons remain open. Native version-2 historical runs
can be analyzed; exact restart requires their original source/environment.

Latest follow-on request: implement and evaluate the independent report's radial
closures after this workflow completion. This is a new physics increment, distinct from workflow completion. No CAD work.

## Timed final GIFs and replenishment review

Final static workflow reports now export every saved frame to wrapped/unwrapped
pressure-and-reaction GIFs; `animate.py` also provides a standalone CLI.
[Evidence and interpretation](../docs/verification/propagation_gifs.md): the
radial-active run receives 49.87 mg of fresh mixture and ends with 49.64 mg
unreacted, compared with 15.35 mg initially. No global fuel exhaustion.
RDE-001 remains open; the time-limit endpoint is not a detected extinction.

## Flow-structure animations

The final-report GIF exporter now uses numerical schlieren, compression, heat
release, shear/contact candidates and injector blocking. The standalone entry
point is `flow_structure.py`. [Definition and evidence](../docs/verification/flow_structure_gifs.md).
12 affected tests pass; no new CFD or physics change. Canonical shock/slip-line
identities remain unverified; progress=0.5 is not the paper's new/old-product slip line.
