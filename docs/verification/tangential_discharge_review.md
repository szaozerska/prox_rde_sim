# Tangential discharge versus the current formed startup

October 22, 2026. Saved-field/source audit only: no new CFD, solver change or
parameter tuning. RDE-001 remains OPEN. This updates the access limitations and
startup interpretation in the earlier Argonne review.

## Findings and source limits

The distinction is real: a finite pre-detonator discharge is not equivalent to
placing a traveling detonation profile in the chamber. The current initializer
has purely tangential initial velocity, but it bypasses the port discharge,
expansion history and radial wall interaction. Neither a stronger velocity
multiplier nor a rounder initial patch would establish equivalence.

**Argonne primary simulation:** Pal et al., *Multidimensional Numerical Modeling
of Combustion Dynamics in a Non-Premixed Rotating Detonation Engine with Adaptive
Mesh Refinement*, [DOE-hosted manuscript](https://www.osti.gov/servlets/purl/1881007).
PDF page 12 establishes steady nonreacting feed before spark/DDT in a separate
H2/O2 tube; its connection opens briefly and closes afterward. Figure 2 on PDF
page 30 was rendered and visually inspected: the tube approaches tangentially
in the perspective drawing. That view does not dimension an exact inlet angle.
The annulus uses H2/air, unlike our methane/oxygen surrogate. The paper reports
5–6 ms to its limit cycle; our 40 us prefix is not a comparable settled window.
The actual requested YouTube frames remain unavailable, and exact attribution of
that segment to this particular journal simulation remains unverified.

**Independent physical startup evidence:** Armbruster et al. (2025),
[Design and testing of a hydrogen–oxygen pre-detonator for rotating detonation engines](https://link.springer.com/article/10.1007/s12567-025-00605-y),
section 4, Figures 10–11 (PDF pages 8–9), rendered and visually inspected.
The connection is 41 degrees, a compromise between normal and fully tangential.
The images show expansion into the annulus, inner-wall interaction and unequal
opposing disturbances. The authors interpret the stronger branch as reinitiated
detonation, and the weaker branch as a shock passing through burned gas.
Crucially, these integration tests fed the pre-detonator only, not the main RDC;
they do not validate sustained operation. This supports asymmetric startup,
not a quantitative pressure ratio or strictly tangential Argonne geometry.

**Mundt remains a separate target:** rechecked printed pages 26 and 37 of
[Mundt2023.pdf](../../Mundt2023.pdf). The pre-detonator connects through a radial
instrument port; Table 2-2 puts the 76-FI-5 port at z=73 mm, diameter 3.2 mm.
An Argonne-inspired tangential launch is a declared alternative initialization,
not a correction that makes our startup reproduce Mundt's hardware.

Interpretation: a tangential incident momentum vector does not prevent a pressure
front and hot products from expanding sideways after emerging from a port.
Shock-front orientation, gas velocity and motion of a luminous region are different
observables. A growing blob is consistent with discharge/expansion, but its
appearance alone cannot determine inlet velocity, injected amount or detonation.

## What the current fields actually show

Read `formed.py`, its resolved metadata and all saved frames of
`runs/directional_startup_40us`. The native run retains status `failed` because
of the previously documented interrupt/Numba exception after its coherent 40 us
checkpoint. Only that verified prefix is used; it is not relabelled completed.

At t=0, the finite charge is 30 mm circumferentially and nominally 3.8 mm high.
It contains a cell-averaged surrogate ZND profile and a burned tail, with
stationary fresh gas outside and stationary hot products above. It is a long
pre-positioned strip, not a compact incoming port plume. The downstream shock
is followed by a separate, imposed burned-to-fresh trailing discontinuity. That
trailing jump can radiate a backward pressure disturbance; it is not the
wall-reflection mechanism in the DLR study.

From the saved float32 fields:

- Initial tangential gas speed: 0 to **1994.59 m/s**, with no negative velocity.
- Initial axial velocity: **exactly zero** in every cell.
- Positive tangential momentum: **0.00579854 kg m/s**; negative contribution zero.
- Initial kinetic energy: **3.80984 J**; maximum cell-averaged pressure **19.6941 MPa**.
- The **2471 m/s** metadata is the profile's reference wave speed, not injected
  gas speed or a speed continuously enforced during the run.

Thus the current initialization is not nearly perpendicular or stationary.
By 2 us, axial gas velocity appears because the high-pressure strip expands into
the region above it. This demonstrates expansion of the imposed initial state;
it does not demonstrate correctly modeled pre-detonator expansion.

At z=0.751974 mm, previously inspected pressure paths give:

| Time, us | Forward peak, MPa | Backward peak, MPa | Forward/backward pressure ratio |
|---:|---:|---:|---:|
| 10 | 6.78045 | 1.18849 | 5.71 |
| 20 | 4.58679 | 1.02567 | 4.47 |
| 30 | 3.43542 | 0.98613 | 3.48 |
| 40 | 2.56288 | 0.88486 | 2.90 |

These are absolute pressure maxima, not wave energy ratios or measured shock
jumps. The main disturbance is already substantially stronger. At 20 us,
reaction within +/-2 mm of the forward peak reaches 2148.72/s, versus 0.157/s
around the backward peak. At 40 us the forward value has fallen to 7.089/s.
The 20 us forward +/-8 mm maximum is much larger (74469.6/s): window choice
matters because reaction is falling behind the shock. Do not classify either
front from pressure dominance alone. Higher regions still react.

This supports **directional launch achieved, discharge fidelity unverified,
near-injector coupling still weakening**. It does not establish that the imposed
impulse is adequate, that a stronger pulse would fix propagation, or that the
backward branch causes the decay. Existing thin-layer formed controls retain
their relevance: an incoming wave also has to survive the receiving mixture.

## Presentation correction and reproducibility

[New field view](launch_direction_audit/launch_fields.png) has equal spatial scale
on both axes and arrows for actual gas velocity at 0, 2, 10 and 20 us. Its
circumferential origin is shifted to the initial leading front. The charge crosses
the old plot's periodic seam; two edge segments there are one connected charge.
Previous automatically scaled plots stretched axial distances relative to
circumferential distances, which could exaggerate the impression of upward motion.
The arrows are velocity vectors, not particle trajectories or wave-speed vectors.
Pressure is not camera brightness. The top of this 20 mm view is a crop, not a wall.

Reproduce from the repo root into an absent output directory:

```sh
MPLCONFIGDIR=/tmp/rde-directional-mpl .venv/bin/python docs/verification/audit_launch_direction.py
```

[Metrics](launch_direction_audit/metrics.json) retain native provenance, script
and prior-report hashes, peak-window definitions in the script, and qualifications.
The reader checked the native prefix and all 21 comparison field hashes. An
independent reconstruction of initial momentum agrees with native inventories
within float32 tolerance. The generated figure was visually inspected. No new
solver tests or CFD campaign were needed for this read-only audit.

Downloaded source SHA-256 values (PDFs not added to the repository):

- Argonne: `12167655cf2fc7635bf0d89c233fc7f0a79281ab7ae9a20757b7571d1455efa6`.
- DLR: `6d00a7d23cd808fd2aadaabf5e068c277b9e24268efe9b1c00ab528487a8b7a9`.

## Small next increments and review decisions

1. **L0 — completed:** establish the incident direction, distinguish the finite
   formed state from discharge, quantify forward/backward pressure and reaction,
   and correct visualization scale/seam ambiguities. No strength retuning.
2. **L1 — specify the finite pulse before implementation:** define the spatial
   footprint, incident conservative state, time history, duration and total
   admitted mass/energy/tangential impulse. Use a trace from a verified tube or
   an explicitly approximate blowdown calculation; do not infer these numbers
   from movie brightness. Retain +theta incident momentum with no imposed axial
   component for the requested tangential variant. Resolve how the localized
   inflow couples conservatively to the periodic reduced domain before coding.
   A single-species surrogate cannot silently import an H2/O2 discharge into
   the methane/oxygen model. Label any same-surrogate pulse as exploratory.
3. **L2 — implement the reduced discharge only after L1 is coherent:** finite-area,
   finite-duration input with exact shutoff and recorded native mass, both momentum
   components and total energy. Fast checks: zero-pulse equivalence, prescribed
   integrated fluxes, mirrored direction, periodic placement, temporal event
   alignment, spatial footprint integration and restart across shutoff. Include
   pressure work/chemical energy consistently; do not add heat and velocity by
   independent arbitrary assignments.
4. **L3 — one bounded startup comparison:** unchanged chemistry, mesh, receiving
   layer, feed and walls; record unequal startup inventories. Assess early
   expansion, both wave paths, local upstream state, shock/reaction separation
   and refill, then survival after forcing ends. Do not advance to a longer run
   merely because the plume looks closer to a video. Revisit chemistry/layer and
   numerical resolution if coupling still fails.

Review 1: purely tangential velocity is already implemented; increasing it alone
would conflate direction with strength and violate the formed profile. Keep it.
Review 2: the real discharge is finite and geometry-dependent. Account for its
mass/impulse/energy and shutoff before treating it as a physical improvement.
Review 3: the present theta-z solver has no radial velocity or cross-gap shock
reflection. Its radial pressure/wall closures do not supply those dynamics.
A reduced pulse can test temporal/spatial input effects but cannot reproduce
Figures 10–11's radial reflection mechanism; reserve that claim for a model that
resolves the gap. The separate 3D track is unaffected.
