# Argonne startup and UW wave-dynamics source review

October 22, 2026. Documentation only; no new CFD or parameter changes. RDE-001 remains open.

**Later access update:** the [tangential-discharge audit](tangential_discharge_review.md)
obtained and visually inspected the DOE-hosted Argonne journal manuscript's
Figure 2, plus DLR startup Figures 10–11. The video access limitations below
remain. The original access statements are retained as the history of this review.

## Access and provenance

Requested: Scott Manley's [4:50–5:10 segment](https://www.youtube.com/watch?v=rG_Eh0J_4_s&t=290s)
and [Kutz's dynamics video](https://www.youtube.com/watch?v=Ws4kbgfpKCw).
The available tools returned page text or fetch errors, not playable video frames.
No frame-by-frame viewing or exact segment-to-source match is claimed.

A NETL [presentation reference list](https://netl.doe.gov/projects/files/EquivalenceRatioScansinaRotatingDetonationEngine_010824.pdf)
identifies Pal's [original CONVERGE animation](https://www.youtube.com/watch?v=-5KtQ8YvdXI),
published January 4, 2019. Its player also could not be fetched.
The [publisher's description](https://www.linkedin.com/posts/convergent-science-inc_simulationfriday-activity-7288639199597973504-hh5S)
credits Argonne's Pinaki Pal and describes separate hydrogen ports, an air slot,
jet-in-crossflow mixing, and a spark-initiated pre-detonation tube.
It distinguishes the temporary startup event from continuous propellant supply.
This is relevant source material, not proof of which exact frames Manley used.

## Primary CFD source

Pal et al., [2019 paper](https://www.researchgate.net/publication/331907638_Numerical_Modeling_of_Supersonic_Combustion_in_a_Non-Premixed_Rotating_Detonation_Engine),
sections 2–3, describes hydrogen/air, 120 fuel holes, an air slot, and a separate
hydrogen/oxygen initiator. The simulation establishes a nonreacting flow first,
ignites the tube, briefly opens its annulus connection, then closes it. This
provides a concrete startup protocol to compare against our imposed patch.
The two operating cases also produce different fill/wave heights as flow changes.
Their hardware and chemistry differ from Mundt Run 937; do not copy their feed
numbers or tube geometry into the Run 937 baseline.
PDF text was accessible; PDF download and screenshot requests failed. Figure 1's
[author-uploaded page](https://www.researchgate.net/figure/Schematic-of-the-AFRL-non-optically-accessible-rotating-detonation-engine-6_fig1_331907638)
was found, but the tools did not provide inspectable figure pixels.

## What the UW framework adds

[Paper 1](https://arxiv.org/html/1908.03116v3), sections II and V.1, connects wave
behavior to injection/replenishment and treats co-rotating waves. Its reduced
model is a qualitative analog, not a calibration for this solver.

[Paper 2](https://arxiv.org/html/2003.06655v1), sections III–V, ties modulation to
reactant availability, injector blockage and recovery, combustion and exhaust.
Its soliton-like interactions concern co-rotating waves; counter-rotating waves
are explicitly outside scope. An apparent reversal in a moving reference frame
must not be interpreted as opposing laboratory-frame travel. Its internal-energy
analog variable is not our gas velocity. Its qualitative bifurcations do not
supply quantitative Run 937 injector constants or prove our failure's cause.

## Comparison with current implementation

Checked `physics.py:injector_flux`, `run.py:build_solver`, and existing saved-data
reviews. The displayed `radial_active` run has a uniform premixed equivalent inlet,
zero injected circumferential momentum and instantaneous pressure-dependent
blockage/reopening. It has no separate species mixing, resolved injector passages,
plenum dynamics, or pre-detonator. The initial hot patch has zero velocity; it is
not an incoming traveling detonation. A separate formed-wave initializer already
exists and includes a traveling profile. These are materially different starts.

Direction and amount cannot be dismissed. Distinguish the startup impulse,
steady feed momentum, and wave motion relative to the gas. A circumferentially
located slot does not by itself specify tangential injection. Mundt's impingement
angle does not establish net azimuthal swirl. Exact vectors require the hardware
geometry; the inaccessible footage is not a basis for inventing them.

Our current saved fuel budget shows continuing injection and increasing fresh
inventory. That excludes global fuel exhaustion, not inadequate usable mixture
at the moving shock. Existing thin-layer formed controls also lose coupling:
startup direction alone is not an established remedy. See
[controlled tests](../plans/controlled_2d_tests.md) and
[UW/saved-data comparison](uw_visual_comparison.md).

## Small next steps and acceptance

1. Reconcile the existing formed-wave results, actual refill thickness and
   chemistry/resolution evidence before commissioning another run. Separate
   initiation failure from propagation failure; do not repeat existing controls.
2. If startup remains an independent discriminator, compare the hot patch and
   existing formed initializer at identical chemistry, mesh, feed, boundaries and
   target fresh layer. Record their differing mass, momentum and energy; do not
   label unequal initial conditions an equal-energy experiment. First verify the
   formed profile propagates in its isolated reference control.
3. Only if a physical startup surrogate adds information, implement a finite
   directional boundary pulse based on a verified incoming-wave state. Measure
   its injected mass, impulse and energy; verify exact shutoff, seam handling and
   reversed-direction symmetry. It approximates an initiator, not tube DDT or a
   resolved radial port. Do not sustain the result by leaving the pulse on.
4. Diagnose refill versus wave phase using existing fields: local fresh areal
   mass/height, pressure, temperature, injector blockage duration and reaction
   lag behind the shock. Distinguish measured model reopening from missing
   physical mixing/recovery. Consider a new closure only after this identifies
   a missing effect and literature supplies a defensible parameter range.

Success requires continuing shock-associated heat release on renewed mixture
across repeated returns after startup forcing ends. A bright moving pressure
pulse, a longer movie, or improved global mass flow alone is insufficient.
No new solver tests were run for this source/documentation review. Source/code
consistency and documentation links were checked; no physical gate was closed.
