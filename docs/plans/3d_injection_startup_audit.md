# Injection, startup and chemistry: 2D versus the current 3D control

October 22, 2026. Source/documents review; no new CFD or physical pass.
Fetched and reviewed these immutable remote heads in the isolated 3D checkout:

- `main`: `73d45162402403c1cdbb9b1c7f5a46d7e3cb5b51`.
- The branch referred to as the 2D detonation fix is actually
  `2d-modelling-detwave-sustaining-fix`:
  `6875f0270cd2b8652641b97d38e9e2267b075ebb`.
- Current 3D movie/source: `8307eacb2e5afb102d714c0ba2537505a3c0ef5a`.

The active 2D checkout has unpublished work. It was not modified or treated as
committed evidence. Its untracked historical investigation note was consulted as
background only; later bounded controls and committed findings govern the
conclusions below.

## Why the movies are different

The current PeleC movie is a planar initialized-wave verification case, physically
one-dimensional despite a 3D solver/grid. It does not run the prepared annular
geometry. There is **no injector, refill layer, pre-detonator, ignition pulse,
wall cooling, jet mixing or rotating return**. A Cantera/SDToolbox ZND state is
converted to conservative native cell averages; hot reacting material starts
behind a shock and stationary fresh premixed gas lies ahead. The native solver
then evolves it freely. There is no later reseeding or forcing of the wave speed.

The streamwise boundaries extrapolate the interior state; they may carry mass
and energy, so this is not a sealed constant-inventory tube. Neither boundary
implements an engine supply law. Transverse directions are periodic and uniform.
The 0.2 us run is about 1.49 reference induction times, not an engine operating
window. The fine solution's speed is ~18% above its independent reference and its
reaction structure is wrong; the conservative boundary-window check also fails.
These faults remain P3D-001 / G2b, not injector-induced failures.

## Side-by-side implemented behavior

| Physical/model decision | 2D main and fix branch | Current 3D-branch GIF | Consequence |
|---|---|---|---|
| Continuous propellant supply | Equivalent uniform premixed inlet at the base, driven by a fixed equivalent plenum. Run 937 uses 1.35 MPa / 300 K, nominal open fraction .110, Cd .76; predicted flow, not simultaneously imposed measured mass flow. | No injector or plenum. Fresh mixture is already in the streamwise domain. | 3D has not yet tested blockage, recovery, refill or sustainable feeding. |
| Injection direction / mixing | Purely axial admitted momentum; zero tangential feed momentum. No separate fuel/oxygen jets or impingement. | No injected momentum or jet mixing. Initial gas velocity behind the shock comes from the ZND solution. | Neither current reacting implementation resolves Mundt's angled injector pairs. A formed wave's tangential momentum is not injector swirl. |
| Blockage / backflow | Local chamber pressure determines choked, unchoked or blocked supply. At/above plenum pressure mass/energy influx is zero, with pressure load retained; reverse flow is suppressed. Instantaneous reopening, no dynamic plenum/port recovery. | Zero-gradient streamwise ends; not a pressure-responsive injector. | The same 2D boundary simplification has not been tested or replaced by a 3D engine boundary. |
| Ignition / startup | Older movies use a stationary hot product patch. Current main default uses a finite +theta formed charge: 30 mm long, 3.8 mm initial fresh layer, 1500 K products above. Fix studies also use formed starts and distinguish changed charge inventories. No physical tube discharge. | Full-cross-section formed planar profile, no finite-height receiving layer or port. Temperature is recovered from imported conservative energy/species. | This isolates transport/chemistry from initiation, but cannot establish whether the engine starts. |
| Chemical kinetics | One irreversible Arrhenius progress variable. Main half-reaction length 1 mm; selected fix studies shorten it to .25 mm. Heat release/CJ speed and reaction length are surrogate calibration targets. | Native PelePhysics full GRI-Mech 3.0, 53 species / 325 reactions, CVODE stiff integration. No prescribed reaction-zone thickening. | Chain chemistry, induction and dissociation can be represented by the selected mechanism, but its suitability and numerical propagation still need validation. |
| Thermodynamics / energy | Constant gamma and gas constant; a fixed unspent chemical-energy reservoir q(1-xi). Reaction updates progress without adding the same heat twice. | Composition/temperature-dependent ideal-mixture thermodynamics; species formation energies and reaction rates. Explicit diagnostic inverse-temperature bound overlay, with published fit-range limitations still open. | A numerically successful 2D calibration is not transferable thermochemical validation. Do not add the 2D q source to native species energy. |
| Fresh-layer survival | Engine contains a finite fresh layer beneath hot products; wave must return into newly supplied gas. Fix branch identifies failure at an approximately 1 mm replenished layer in a small-engine case. | Fresh mixture spans the entire transverse section; no hot product overlayer or lateral expansion from a finite fresh layer. | Current 3D control bypasses the key replenished-layer failure mechanism found in 2D. |
| Contact mixing and numerical diffusion | Main uses HLL/MUSCL; fix branch adds optional HLLC. HLLC greatly reduces artificial contact burning and improves refill but does not sustain the tested small engine. | Native PeleC MOL, currently first-order reconstruction for diagnosis after second-order species/element defects. No molecular transport or turbulence enabled. | Detailed chemistry and an upstream solver do not remove numerical mixing. First-order transport remains a risk, and the current wave fails accuracy checks. |
| Exhaust / wall coupling | Periodic circumference, axial pressure/outflow boundary, fixed gap-averaged annulus. Optional radial-pressure/friction closures do not resolve jets or radial motion. | Open-ended planar control with transverse periodicity; all transport disabled, no solid walls in this run. Cold annular/core-expansion geometry is separately verified. | The current movie cannot reproduce an RDE refill wedge, oblique exhaust shock or radial wall interaction. |
| What the chemistry plot means | xi is the evolved one-step reaction progress; a fresh-equivalent inventory follows that surrogate definition. | Heat fraction is a derived species formation-enthalpy diagnostic, not an evolved scalar xi or a direct image of flame luminosity. | Compare pressure-coupled heat release and actual species, not matching colours or identical progress thresholds alone. |
| Duration / success criterion | Engine windows of tens to ~189 us; some first transits remain coupled, but sustained periodic operation is unproven. | 0.2 us planar diagnostic; propagation gate fails. | Neither a moving pressure front nor a successful GPU job establishes sustained detonation. |

Implementation anchors: `tools/pelec/modal_wave.py` (native boundaries, transport,
chemistry), `tools/pelec/prepare_wave.py` (reference, conserved initialization),
`rde3d/native/pelec/FormedWave/prob.H` (native initializer), and
`tools/pelec/analyze_wave.py` (species-derived heat diagnostic).

## What the 2D investigation actually established

There was a real early inlet inconsistency: choked mass flow was combined with a
velocity expanded all the way to chamber pressure. D1 fixed it by using one
consistent converging-opening state for mass, momentum and enthalpy, including
pressure on both open and closed face fractions. That correction is present on
both reviewed branches. `rde_sim_starter/physics.py` is byte-identical across
those heads (SHA256 `0150132690fc1d951aaf55d7da2f17681771d25605ce3288ebbd300cc612472a`).

The later fix is not evidence of one remaining inlet-code bug as the sole cause:

- The stationary-contact test reduced artificial conversion by ~100,000x with
  HLLC. In a matched small-engine comparison at 30 us, cold refill increased
  from .65 to 1.14 mm at almost identical delivered mass. This demonstrates a
  numerical contribution to premature burning, not insufficient total supply.
- That HLLC engine still lost strong coupling after return. A separate fully
  fresh 1 mm layer, with no injector or periodic return, also lost coupling.
  Its pressure threshold and reaction peak separated by 6.25 mm within 10 us.
  Thus the tested chemistry/grid/expansion combination is insufficient even
  under idealized mixture availability; residual numerical and kinetic causes
  were not uniquely separated.
- In a different main radial-control case, late injection was 267.5 g/s versus
  268.65 g/s measured, with fresh-equivalent inventory increasing. That excludes
  global exhaustion for that case, not incorrect local temperature, composition,
  density, usable layer thickness or recovery timing.
- Initial 3.8 mm layer survival is not refill-layer survival. A paper-inferred
  height based on measured frequency is not a boundary condition that guarantees
  the same layer when the simulated speed/wave count differ.

Evidence at immutable revisions:
[fix findings](https://github.com/szaozerska/prox_rde_sim/blob/6875f0270cd2b8652641b97d38e9e2267b075ebb/docs/verification/detwave_findings.md),
[fix refresh/angle clarification](https://github.com/szaozerska/prox_rde_sim/blob/6875f0270cd2b8652641b97d38e9e2267b075ebb/docs/verification/detwave_main_refresh.md),
[early inlet correction](https://github.com/szaozerska/prox_rde_sim/blob/73d45162402403c1cdbb9b1c7f5a46d7e3cb5b51/docs/verification/d1_propagation.md),
[main configuration](https://github.com/szaozerska/prox_rde_sim/blob/73d45162402403c1cdbb9b1c7f5a46d7e3cb5b51/rde_sim_starter/config.yaml),
[main startup audit](https://github.com/szaozerska/prox_rde_sim/blob/73d45162402403c1cdbb9b1c7f5a46d7e3cb5b51/docs/verification/tangential_discharge_review.md).

## Argonne and Mundt are separate comparisons

Re-read Pal et al., *Multidimensional Numerical Modeling of Combustion Dynamics
in a Non-Premixed Rotating Detonation Engine with Adaptive Mesh Refinement*,
[DOE manuscript](https://www.osti.gov/servlets/purl/1881007), pp.8-12 and Fig.2
(p.30). Online fetch returned 502; the existing local PDF was checked against its
recorded SHA256 `12167655cf2fc7635bf0d89c233fc7f0a79281ab7ae9a20757b7571d1455efa6`.
Text and saved page renders were inspected; exact attribution of the user's
video clip remains unverified.

That CONVERGE study models hydrogen/air with separate injection (120 hydrogen
ports and an air slot), 10-species finite-rate chemistry and RANS transport.
Its simulation omits the plenums and imposes mass flows at the inlets. It first
establishes nonreacting flow, ignites an H2/O2 pre-detonator, opens the connection
briefly, and closes it. It reports 5-6 ms to a limit cycle and 60-72 h on 144
processors. It therefore does not demonstrate that the same fidelity/window
fits our two-hour budget, nor is it a methane/oxygen Run 937 boundary prescription.

Our Mundt transcription instead records 72 fuel/oxygen impinging pairs, 30 degrees
to the combustor axis and 2.16 mm impingement height; this is not evidence for
arbitrary tangential swirl. The startup port is separate, at z=73 mm. The earlier
main audit verifies that Mundt uses a radial instrument-port connection, unlike
the Argonne-style tangential alternative. A formed initial wave is permissible
as a declared propagation test, not a simulation of either physical startup.

## Minimal corrections to the 3D acceptance order

The old plan already listed feed sensitivity and eventual resolved jets, but it
allowed the first annular reacting preview before a specific native refill-layer
qualification. Revision 19 makes this dependency explicit without starting a
large new campaign or changing solver physics:

1. **Keep G2b first:** fix native planar propagation/boundary limitations. Do not
   compensate by increasing ignition, feed pressure or rates.
2. **G2c-a: native feed contract and cold refill.** Define the cheapest equivalent
   premixed boundary explicitly as an idealization. Use one declared feed basis
   (plenum-driven predicted flow, or imposed flow), a documented mixture/total
   enthalpy and area convention. Validate blocked/unchoked/choked states,
   pressure forces and species/mass/enthalpy fluxes in a tiny boundary test. Use
   the native mixture EOS, not the copied constant-gamma/q expressions. State
   backflow policy and lack of finite plenum recovery. For a genuinely separated
   feed, retain independent supply states rather than silently average them.
3. **G2c-b: contact and usable-refill qualification.** Run one stationary fresh/hot
   contact at two spacings, with an independent zero-transport reference; then
   test propagation in a finite fresh layer under hot products at the predicted
   refill conditions. Use .5/1/3.8 mm only as an explicitly provisional bracket
   if native refill data are not available; choose two discriminating thicknesses,
   not a sweep. The 1 mm evidence came from a smaller-engine surrogate, not a
   measured Run 937 extinction threshold. Track density, temperature, species,
   local equivalence ratio, cold fresh areal mass, premature heat release and
   shock/reaction separation. Cold refill alone is not a reacting refill pass.
4. **G4a: bounded premixed annular preview only after those checks.** Preserve a
   finite formed charge as the simplest propagation initialization and label it.
   During the run, measure phase-resolved blockage/reopening, actual usable layer
   and return time. Stop if these leave the qualified envelope. A 63.131 us
   experimental passage budget does not automatically equal a simulated full
   circuit or prove return into newly injected mixture. Require actual returns
   after the initial charge has been consumed before any sustained-wave claim.
5. **G5 / T6: injection-design claims require more.** One resolved cold impinging
   pair with appropriate species/thermal/momentum transport precedes a full
   injector array, unless an independently validated reduced mixing closure is
   used. Resolve the actual injection vectors; no arbitrary swirl. A finite
   pre-detonator pulse is a separate later increment: specify its admitted mass,
   species, momentum, energy and shutoff, then compare startup sensitivity. Do
   not reproduce an animation by imposing persistent heat or reseeding waves.

These checks can reuse 2D diagnostic definitions, but native PeleC flux/EOS/
chemistry tests and the mixture state must be checked independently. Changing
CPU to GPU changes throughput, not these physical requirements. No unresolved
solver or thermochemical gate is closed by this review.
