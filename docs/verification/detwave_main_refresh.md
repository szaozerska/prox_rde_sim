# Main refresh and injector-angle clarification — October 22, 2026

## Integration decision

Reviewed GitHub main through `050995e`, including `7144d28` (completed radial
comparison) and the committed wrapped/unwrapped propagation GIFs. A newer
flow-structure visualization was still in progress in the other chat; after
several minutes of paper/source review and repeated fetches it was not published.
Integrated the available main into `2d-modelling-detwave-sustaining-fix` without
changing the original checkout or restarting an investigation engine job.

One merge conflict in `plot.py` was resolved by retaining the investigation's
`plot_detwave` and main's new `plot_workflow(..., gifs=True)` interface. Main's
GIF/reporting changes are read-only postprocessing. Its source changes since
`f12cca1` do not alter flow evolution, chemistry, injection or radial physics.
The solver, run construction, physics, radial model, calibration and investigation
drivers are byte-identical to investigation commit `800d466`; hashes are recorded
in `detwave_main_refresh_source_audit.json`. The historical HANDOFF instruction
to publish on main applies to the other task; this user's branch-only instruction
continues to govern this work.

## What Mundt actually says about injector angle

Read the complete relevant pages in the local `Mundt2023.pdf`; visually checked
printed pp.15, 26 and 34. Printed p.15 discusses injection design and mixing
affecting wave speed, wave count and performance, including prior comparisons
of impinging and misaligned injectors. Printed p.16 connects injector recovery,
mixing and plenum interaction with detonation behavior.

Printed pp.27 and 34 hold both fuel and oxidizer holes at **30 degrees to the
combustor axis** across configurations, with **2.16 mm impingement height**.
The study does not vary angle to identify an ignition threshold. Startup ignition
is described separately on p.26: a spark-fired predetonator, with its own supply,
connected through an instrument port. Thus injector geometry is important to
mixture preparation, but the thesis does not establish angle as the unique cause
of ignition or sustaining failure in our model.

The earlier statement that angle is outside the model's demonstrated scope must
not be read as saying it is physically unimportant. Our spatially uniform premixed
inlet does not represent the impinging jets. Adding a tangential velocity to mimic
30 degrees would also be unjustified: the actual inclination/impingement occupies
the radial-axial geometry, which the unrolled theta-axial solver does not resolve.
Predicting angle effects requires resolved injection or a separately validated
mixing/injection closure.

## What the 1 mm control establishes, and what it does not

The completed control is a counterexample to assuming that initial-layer success
guarantees refill-layer success: the tested chemistry/grid and product-layer
conditions lose pressure/reaction coupling even with fully fresh gas and HLLC.
It is not a unique causal attribution to chemistry, not a physical extinction
limit, and not a validation of the real injector, mixing field or startup history.
It cannot exclude an injector-model contribution to the full-engine discrepancy.
Consequently, improving ignition alone has no demonstrated basis as a complete
fix, but ignition and supply modeling have not been universally ruled out.

## New evidence from main and decision on reruns

Main's matched wall-control/centrifugal runs both completed 189.394 us using the
coarser original chemistry/startup. They failed to retain near-injector coupling
while burning continued higher in the channel. The radial-active case retained
49.64 mg of fresh-mixture equivalent from 15.35 mg initially plus 49.87 mg injected;
late total injection was 267.5 g/s versus 268.65 g/s in the experiment. This excludes
global exhaustion for that case, but not local mixture-preparation problems.
These runs are not matched A/B comparisons with our shortened-chemistry/HLLC cases.
They also do not test resolved radial motion or detonation curvature.

**No engine or thin-layer rerun is warranted merely by this merge:** the numerical
evolution code is unchanged, and the additional wall-physics comparison already
exists. Repeated runs would not distinguish a new hypothesis. Only focused merge
regressions cover GIF/workflow integration, read-only analysis, case loading and
the retained HLLC implementation; results are in `detwave_main_refresh_tests.log`.

The investigation remains closed with sustaining validation unresolved. Any
further physics work should be a separately bounded model correction, with one
acceptance path: credible chemical timing and spatial resolution, propagation
at the actual refill conditions, then several periodic returns in one engine.
Do not open another generic test campaign or tune six engines independently.

## Integration verification

20 focused tests passed in 116.588 seconds with no skips. The resolved
`plot_detwave` function is AST-identical to investigation commit `800d466`;
`plot_workflow` and `watch_workflow` are AST-identical to main `050995e`.
`git diff --check` passed. These are merge regressions, not a renewed physical
validation campaign or evidence that sustained detonation has been achieved.
