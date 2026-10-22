# Timed propagation GIFs and the fuel-exhaustion question

October 22, 2026. Saved-data review of the completed `radial_active` case;
no new engine simulation, chemistry change, CAD work or extinction-time fit.

## Final run products

- [Unwrapped pressure and reaction](propagation_gifs/unwrapped.gif).
- [Wrapped pressure and reaction, opposite fixed views](propagation_gifs/wrapped.gif).
- [Manifest, actual timestamps, input/frame hashes and fuel balance](propagation_gifs/manifest.json).

Both cover all 96 committed snapshots from **0 to 189.393939 microseconds**.
Pressure and reaction have fixed logarithmic color scales throughout. Each frame
shows physical time, frame number, whole-domain peak reaction and the peak at the
actual lower-ring height (0.751974 mm). The azimuth coordinate and periodic seam
are labeled. The initial hot patch can launch multiple pressure disturbances;
no single tracked front or direction is invented. Watch the motion in successive
frames and inspect whether reaction accompanies it.

Playback slows the physical intervals to 14 seconds, rounded to GIF's 10 ms
clock, then holds the last frame for 1.5 seconds. There is no loop extension.
All saved times are retained, without interpolating or synthesizing wave fronts.
Tiny rates below the common display floor use the lowest color; the printed
absolute rates prevent mistaking a dark panel for exactly zero chemistry.
The wrapped GIF shows the same mean-radius 2D fields with two opposite cameras,
not an independent 3D solution or the reconstructed inner/outer wall pressures.
Wrapped display faces average blocks of native cells; the unwrapped image retains
the native mesh. A coordinate arrow means +theta, not detected wave velocity.

**The last frame is the end of the saved time window, not a detected extinction
or fuel-exhaustion event.** Pressure pulses and burning higher in the channel
persist. We cannot truthfully label this as a movie ending when all combustion
stops. No new long run is justified just to make the animation end in darkness.

`plot.py --workflow` now includes both GIFs in final static reports (when at least
two saved fields exist). The PNG preview's `--frames` limit does not drop GIF
frames. Live `--follow` previews keep their lightweight PNG behavior; create a
static final report for the GIF pair. The focused exporter is:

```sh
cd rde_sim_starter
../.venv/bin/python animate.py --run runs/radial_active --out ../reports/radial_movie
```

Use a new output directory outside the native run. `--seconds` adjusts playback;
`--start-us`/`--end-us` select a saved window. Too-dense timestamps for the chosen
GIF duration are rejected rather than silently dropping frames; increase duration.
An incomplete/failed export has an `INCOMPLETE` marker and no `COMPLETE` marker.

## Is it running out of fuel?

**No global depletion is present in this case.** The injector law is evaluated
at every flux stage. It draws from a fixed plenum and supplies fresh premixed gas
whenever the local injector-face pressure is below the plenum pressure; it blocks
locally above that pressure. There is no once-per-revolution injection timer,
finite fuel tank, or rule that stops fuel when the initial charge has burned.
The run ends because its configured time budget is reached (`completed_limit`).

Native conserved histories, not colors in the movie, give:

| Quantity | Radial-active case |
|---|---:|
| Initially unreacted mixture | 15.350911 mg |
| Fresh mixture injected over the run | 49.868259 mg |
| Mixture converted by reaction over the run | 15.575516 mg |
| Unreacted mixture leaving the outlet | 0.00000365 mg |
| Unreacted mixture remaining at the end | 49.643650 mg |
| Mean injection, entire startup window | 263.304407 g/s |
| Mean injection, 100–180 us | 267.494624 g/s |
| Mean injection, final 180–189.394 us | 267.756215 g/s |
| Paper Run 937 reference mass flow | 268.65 g/s |

Here “unreacted mixture” means the one-step model's integral of rho*(1-progress),
not methane mass alone and not a measurement of a uniformly detonable layer.
The 100–180 us mean is about 0.43% below the measured reference. This excludes
**global fuel exhaustion or gross missing total feed** as a sufficient explanation
for the observed decay. It does not validate local refill, mixture temperature,
jet recovery, distribution or chemical readiness ahead of a particular shock.

[Fuel inventory and injection plot](propagation_fuel_balance.png) and
[independent checkpoint/ledger audit](propagation_fuel_audit.json) preserve this
check. The final fresh-mixture integral from checkpoint conserved fields agrees
with the native history inventory to floating-point precision.

The model supplies fresh gas continuously subject to pressure blocking. Mundt's
experiment also has supplied fuel/oxidizer streams; the distinction is not that
we forgot to add more fuel. Real separate impinging jets, mixing, startup and
outlet hardware differ substantially from our equivalent boundary. The source
comparison and paper page citations are in the [paper/model audit](mundt_model_audit.md).

## What radial effects are present?

The optional `annular_closure` case implements centrifugal radial equilibrium,
using local gas tangential velocity to reconstruct separate inner/outer wall
pressure and density while preserving annular means. Each wall has its own drag
coefficient and temperature, with explicit heat-transfer/recovery assumptions.
The matched tests used Cf=0.005 and Tw=300 K at both walls, analogy=1 and recovery=0.9.
These are exploratory settings, not measured Run 937 coefficients.

They were actually run, not just planned. The matched centrifugal-on/off runs
both completed 189.394 us and neither restored sustained detonation. The additional
centrifugal feedback changed late exit force by only -0.000814% in that comparison.
Full radial momentum/velocity, radial wave detachment and a validated curvature
loss model remain absent. The default baseline is still inviscid; the GIFs use
the explicitly enabled radial case. See [equations, tests and results](radial_closures.md).

This review found stale sentences in the HTML/Markdown report generator saying
centrifugal pressure and heat loss were absent. They now describe enabled case
settings correctly; a regression test covers the radial Markdown report.

## Why does the wave fail, and why is this still unresolved?

The observed failure is **loss of sustained shock-associated reaction**, not
extinction of all burning. At the lower ring the peak reaction falls from about
47,500/s at 20 us to 11/s at 40 us and 0.009/s at the end. At the endpoint the
whole-domain peak is still about 86,616/s and median heat-release height is about
18.7 mm. Pressure disturbances alone therefore cannot close RDE-001.

The strongest existing evidence points toward the relationship between reaction
structure, layer thickness, expansion and numerical mixing:

1. The selected surrogate has a 1 mm half-reaction length and 4.177 mm length to
   95% heat release, compared with the independently calculated detailed-chemistry
   reference's 0.03952 and 0.05108 mm. The surrogate's long tail is comparable to
   the assumed 3.8 mm starting layer. CJ-speed agreement does not validate this
   timing or thin-layer survival.
2. Controlled formed-wave tests propagate in a thick layer but lose coupling in
   the thin layer, including refinement and an aligned-interface control. This
   is stronger evidence than the engine GIF alone, but not a unique engine root cause.
3. Isolated contact tests demonstrate artificial reaction caused by numerical
   mixing, with conversion decreasing on refinement. That could redirect burning
   toward the interface; its causal share in this engine failure remains unproven.
4. Uniform premixed injection, a hot-patch start and an annulus-end outlet replace
   the experiment's separate jets, pre-detonator and downstream expansion. They
   still require physical assessment, even though total feed is nearly correct.

These are measured discrepancies and ranked hypotheses, not a claim that a
particular next patch will solve the problem. The experimental Run 937 sustained
operation for 0.696 s; this startup calculation is only 0.000189394 s. It does not
reproduce that result. It is also too strong to say a physically established
rotating detonation has been reproduced and merely dies a known amount too early:
the artificial startup never demonstrates the required sustained state here.

The functional workflow is complete, but its physical reproduction of Run 937 is
not. More plotting/machinery alone does not make the chosen chemistry and boundary
assumptions adequate. Conversely, 2D itself has not been established as the cause:
[JAXA reports 2D methane/oxygen rotating detonation calculations](https://www.jss.jaxa.jp/en/ar/e2020/14259/)
with different chemistry, geometry and resolution. That is existence evidence,
not validation of this reduced model. RDE-001 remains open with the independent
sustainment investigation responsible for the discriminating physics studies.

## Implementation review and verification

Three small reviews before publication:

1. Avoid a pressure-only “detonation” movie: pair pressure with absolute reaction,
   fix color scales, include all saved times and label the finite endpoint.
2. Avoid a misleading 3D/front-direction claim: wrap existing fields, expose both
   sides, mark coordinate orientation and preserve area when coarsening display faces.
3. Check the proposed exhaustion explanation against native mass/source ledgers;
   fix the discovered stale radial-physics text and add its regression check.

Focused rendering/workflow tests initially passed (9 tests). Visual inspection
caught overlapping labels in the first draft; layout was corrected before final
publication. Final full acceptance: **137 tests passed, zero skips, 169.957 s**, including
the opt-in inherited reactive baseline. [Full test log](propagation_gif_full_tests.txt).
The added checks cover unequal-time GIF timing, zero-reaction rendering, both
encoded products, periodic orientation/area-preserving display averaging, native
fuel balance, source immutability, refusal of unsafe output paths, failed-export
markers, import isolation, final-workflow integration and enabled radial metadata. No solver, feed, chemistry or native-run files are changed by export.

Final artifact audit: both encoded GIFs have 96 frames and total display time
15.5 seconds (14 s physical-time-scaled playback plus 1.5 s endpoint hold),
with no loop extension. First, middle and final preview frames were visually
inspected for both views; the fuel-balance plot was also inspected. All 96
source-frame hashes, committed input/summary/history hashes and renderer hash
match the manifest after export. The unwrapped GIF is 1020 x 544 pixels and
the wrapped GIF is 1020 x 697 pixels.
