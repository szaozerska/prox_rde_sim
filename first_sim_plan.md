# RDE simulation plan — revision 13

**Status: C1–C4, C5a and the C5b–e quarter-length bounded experiment completed. C6a functional initialization/benchmark is complete. F1 saved-window reporting is complete (98 tests passed, one opt-in skipped). F2 contracts complete; next F3–F4 workflow completion. Sustained-wave investigation is assigned to a separate chat.**
The [controlled-test plan](docs/plans/controlled_2d_tests.md) records three review
passes and the C1–C6 increments. First verify multirow/direction equivalence and
formed-profile propagation, then distinguish thin-layer survival from initiation.
The [diagnostic review](docs/verification/layer_diagnostic_review.md) identified
this as a then-untested hypothesis. C3 now supports a bounded thin-layer
propagation limitation; the complete engine cause remains unresolved. The paper audit
and completed D3 references/contact/refinement evidence remain the baseline.
This session commits and pushes only **main**, for the 2D pipeline. A separate
session owns 3D development and need not wait for a successful 2D engine run.
[HANDOFF.md](HANDOFF.md) gives current commands and outcomes. Older plans and the
Git-ignored review are historical context and do not override this plan.

**Known open case: [RDE-001](docs/verification/run937_unresolved.md).** D1's 3.8 mm
and D2's 7.6 mm Run 937 starts do not demonstrate sustained detonation by 189.394
microseconds. D0-D3 completion refers to the short development increments below,
not completion of the broader numbered physics stages in section 7. Stage 1
physical-reference/refinement work is incomplete and Stage 3's sustained-wave
criterion is not met. The first working physical 2D iteration remains pending.

**Immediate deliverable:** a runnable reduced 2D Run 937 prototype, meaningful fast numerical checks, a few passages of pressure/reaction fields if the model sustains them, and short-window pressure/force diagnostics. The fuller first working iteration adds sufficient numerical/averaging evidence for pressure comparisons and qualified thrust/torque estimates. Human inspection remains the primary wave assessment. These are intermediate research models on the path to simulation of imported 3D engine geometry.

**Future requirements:** retain the ability to replace the CFD backend, resolve radial/gap physics in 3D, and import CAD assemblies or parts. The separate 3D session may begin backend evaluation now; successful operation of this custom 2D engine is not a prerequisite for that independent track. CAD import is **TO BE IMPLEMENTED after the first working iteration**; its geometry contract and independent importer can be developed in parallel now. Sections 3, 4, 8, and 9 define these requirements and their order.

Paper references mean Mundt (2023), *Geometric Scaling of Cylindrical Rotating Detonation Rocket Engine Combustors*. Use printed page numbers; PDF page = printed page + 16. Fig. 1.1 is an illustrative flow/design image, not a measured 3D validation dataset.

## 0. Functional implementation track and separate investigation

**Latest direction (October 22):** continue remaining 2D functionality on main;
the user will launch the sustaining-wave study in a separate chat. Do not block
independent functional work on RDE-001, and do not automatically launch more
layer sweeps, full engine propagation studies or chemistry/integrator changes here.
The physical validation gates still constrain claims. 3D stays on its separate track.

Functional increments after C6a, drawn from sections 4.5, 5.2 and 9:

| Increment | Deliverable | Short verification |
|---|---|---|
| **F1: saved-window reporting — implemented** | Explicit time-window selection, native mass/energy/momentum balances and annulus-exit force summary; preserve storage, missing-data reasons and transient qualifications. | Analytical constant/time-varying signals and known-flow force signs; uneven time steps and partial-window overlap; read-only saved-run smoke check. No CFD campaign. |
| **F2: minimal geometry/result contract — implemented** | Versioned SI geometry and capability metadata for the supported constant annulus, preserving source provenance and exposing omitted features for future backend/CAD adapters. | Known dimensions/areas and unit conversions; reject unsupported coreless/nonuniform/CAD geometry instead of silently reducing it. No general plugin framework or 3D work. |

| **F3: optional wall friction and qualified torque** | Explicit constant-Cf adiabatic momentum sink, native source budgets, mean-radius engine torque and optional constant-inertia roll response. Inviscid default retained. | Analytic uniform decay/heating; zero-Cf equivalence; sign reversal, coefficient/time sensitivity, angular balance including storage; saved-run/restart checks. |
| **F4: complete saved-data workflow** | Streaming field preview/animation and labelled wrapped/head-end views; windowed pressure spectrum/spectrogram; explicit reference comparison and reusable multi-run sensitivity tables; documented run/resume/report commands. | Known-signal frequency/alias/window tests, corrupted/missing input rejection, read-only outputs and a tiny complete CLI run/resume/analyze/plot acceptance test. |

**Completion boundary (latest request):** finish F2–F4 and audit the complete fast
suite plus the opt-in reactive baseline before the final push. This completes the
2D *software workflow*, including optional friction; it does not declare sustained
Run 937 detonation or predictive performance validated. Fixed-model production
sensitivity campaigns, measured-thrust/held-out validation, CAD import, alternate
CFD backends and 3D remain separately identified work. Generic comparisons can
consume those studies later without embedding per-engine plotting logic.

Review 1: metadata alone cannot enforce support; integrate geometry rejection
in the actual runner and preflight. Review 2: torque must come from applied wall
sources and independently checked storage/flux, not exit angular flux alone.
Review 3: short signals and synthetic views must not imply established frequency,
3D physics, steady pressure or camera luminosity. Keep unavailable results explicit.

C6a construction decisions, the test audit and its bounded measurements are
recorded in [the functional increment report](docs/verification/c6a_functional_pipeline.md).

F1 now provides `window_report.py --run ... --start-us ... --end-us ... --out ...`.
It uses saved native step integrals with explicit partial-step semantics, retains
storage and missing-data reasons, and writes JSON/Markdown without CFD or full
field loading. [F1 evidence and accounting review](docs/verification/f1_window_reporting.md)
include analytical force checks and reports from C6a and historical D1. Neither
report is a new propagation result. F2–F4 below finish the software workflow; the physical validation gates remain open.

### Historical controlled-test scope

**Completed authorized experiment (October 22):** C5b–e tested a declared
0.25 mm half-reaction-length surrogate (k multiplied by four, unchanged Ea/EOS).
The existing source integrator passed reactor, planar and contact checks; the
3.8 mm layer retained near-wall/middle coupling through 10 us on both meshes. See the
[predeclared protocol](docs/plans/controlled_2d_tests.md)
and [new evidence record](docs/verification/c5_short_reaction.md).
This supersedes the prior unspecified model-choice stop, not the engine gate.


D0–D3 and the source audits are complete as development increments. The user
has authorized the controlled C1–C6 investigation, small verified implementation
steps, documentation and publication on main. Follow the three reviewed passes
in the companion plan. Broad operating maps and unrelated figure campaigns stay
deferred. Preserve the engine duration policy below; localized controls choose
separate finite durations appropriate to their causal/relief times.

The user clarified the earlier “500–700 ns” instruction to mean **a few wave passages, with the minimum useful test duration**. Use:

- **Default: three expected wave-passage intervals**, measured from simulation start, for the 2D development check.
- **Only when useful: extend the same saved run to five intervals total**, for example if startup obscures the initial signal. Do not rerun the first three intervals or automatically extend beyond five.
- For Run 937, `f_ref = 15.84 kHz`, so one passage interval is approximately **63.1 µs**: three intervals are **189 µs (0.19 ms)** and five are **316 µs (0.32 ms)**. These are physical simulation durations, not wall-clock limits or CFD time steps. A passage is one wave crossing a probe, not one complete revolution of each wave.
- Set a finite end time from the reference/expected frequency before running. This frequency is used only to budget duration, not to impose or infer the simulated result. Record actual detected passages separately. A stalled/extinguished wave must not cause an unbounded “wait for three passages” loop.
- Stop early on invalid states or a clear failure. Keep CFL/source-accuracy restrictions and physical chemistry unchanged; reduce case count, logging and test scope to save time.

Small algebraic/source tests need no engine-length run. Use short localized 1D shock/reaction tests for fluxes and source timing, retaining the physical model; keep the full 2D check separate from the fast default test suite. Reuse its saved data for every diagnostic/plot. If insufficient clean post-startup data remain, report **inconclusive over this short window**, rather than pretending the test established a steady state.

| Development order | Required work and useful output | Explicitly deferred |
|---|---|---|
| **D0. Minimal organization and checks** | Separate files as in §4.5; freeze Run 937 inputs; fix correctness issues affecting this case; fast source/conservation/boundary checks. | General plugin infrastructure, all-engine registry, full thermochemical parameter sweeps. |
| **D1. Short propagation check** | One small 1D check, then the three-interval Run 937 2D check; inspect pressure/reaction coupling and state validity. Extend to five total only for a specific unresolved observation. | Long settling studies, multiple ignition ensembles, automatic parameter search. |
| **D2. Reusable analysis and plots** | Unrolled fields, short space–time plot/front tracks, pressure station traces/profile, and mass/energy/momentum budgets. Compute instantaneous thrust/torque diagnostics with storage where the implemented model supports them. | Full spectra/spectrogram suite, wrapped-cylinder polish, multi-engine/mode maps. |
| **D3. Focused investigation — completed** | Run 937 physical CJ/ZND and independent equilibrium heat release; six frozen/reactive contact tests at 0.5/0.25/0.125 mm; three fixed-chemistry 1D propagation grids; reference/contact/front graphs and regression checks. | Exact NASA CEA replication, full G0 curves, new 2D runs, chemistry replacement, broad convergence and engine sweeps. |

**Completed functional increment: C6a formed-engine initialization and a 2 us cost/validity benchmark.** C1 passed its 95 µs matched
propagation check. C2 passed conservative initialization and 40 µs filled-strip
propagation at three meshes plus a source-step comparison; see the
[increment log](docs/verification/controlled_2d_progress.md). C3 confirms a bounded
3.8/15 mm contrast on two grids, plus an aligned thin-interface control. C4 has
completed blast/profile comparison in the 15 mm layer: the blast is weaker but
still reacting behind its leading shock at 40 µs. Stable rotation remains unproved.
C5a found that substituting physical reaction lengths on the current mesh/source
treatment is not ready for an engine run; see the [readiness review](docs/verification/c5_model_readiness.md).
C5b–e passed the declared quarter-length surrogate controls through 10 us.
C6a verifies the engine initializer, seam, restart and budgets as functionality;
the separate study owns any bounded propagation comparison. No stable-engine
claim follows from the layer test or the 2 us benchmark. See
[controlled-test plan and three reviews](docs/plans/controlled_2d_tests.md) for
unit tests, diagnostic requirements, causal-domain checks and stopping criteria.

The nominal 3.8 mm cell-center mask changes fresh inventory and initialization
energy on refinement; use conservative cell averages in the new controls and
record the mixed interface cells. Do not silently rewrite D1/D2 or treat a changed
initializer as a pure grid comparison. The previously proposed unchanged-start
0.25 mm engine run is superseded by these cheaper causal controls. Hypothesis-
driven reaction-length changes are permitted after independent verification;
freeze each selected chemistry across its mesh comparisons.

This short run tests basic propagation and numerical behavior. It does **not** establish long-term wave stability, converged mean pressure, validated thrust, or mean mechanical torque. Label initial pressure/force overlays **transient, short-window estimates**; retain storage terms. Front tracking/arrival times are more useful than a fine-frequency FFT here. Keep the remaining evidence as follow-on work, without hiding it or trying to complete every graph overnight.

## 1. Scope and decisions

- Reuse the small `rde_sim_starter` numerical prototype after verification. Keep useful flux, reconstruction, calibration, and plotting work; correct the deficiencies recorded in the review. Do not expand this prototype into a general CAD mesher or a new industrial 3D CFD framework.
- First solve a radially averaged, unrolled circumferential–axial domain, denoted `(x, z)`, where `x = r_m theta`. The radial direction is absent. A cylinder-wrapped display remains a visualization of this 2D solution.
- Start with 76-FI-5 / Run 937. Its relatively thin annulus is the most favorable initial candidate among these engines for this approximation, by project judgment; the paper does not validate this reduction. Gap/mean radius is 0.1404, and radial dynamics are absent. Small, wide-gap cases are exploratory comparisons, not obligatory initial validation gates.
- Use simplified premixed reactive flow first. Preserve separate fuel and oxidizer data in the case definition, even if this backend explicitly converts them to one equivalent premixed feed.
- Keep measured inputs, fitted parameters, derived reference quantities, and numerical choices separate. A quantity used to fit the model cannot independently validate it.
- Show intermediate fields and histories early. Defer elaborate automatic wave classification and whole-paper mode-map replication. Retain shock/reaction coupling and numerical checks so the visual interpretation is meaningful.
- Report **axial torque and estimated roll response**, not a vehicle or structural stability verdict. Inertia, burn duration, damping, and controls are additional inputs for vehicle response.

## 2. Reference data and initial physical model

### 2.1 Freeze a reproducible first case

Record values with units, source table/page, uncertainty where available, and whether measured, inferred, fitted, or read from a plot. Do not silently treat nearby plotted operating points as an identical 320 kg/s/m² test condition.

| Run 937 quantity | Reference value |
|---|---|
| Geometry | `r_o = 38.1 mm`, `r_i = 33.1 mm`, `g = 5 mm`, `L = 76.2 mm` |
| Injector | 72 fuel/oxidizer pairs; nominal open-area ratio 0.110 |
| Total flow / annular mass flux | 268.65 g/s / 240.21 kg/(s m²) |
| Equivalence ratio | 1.176 |
| O₂ / CH₄ plenum pressures | 1309.5 / 1399.4 kPa |
| O₂ / CH₄ plenum temperatures | 303 / 301 K |
| Back pressure | 100.2 kPa |
| Wave count / passage frequency | 2 / 15.84 kHz |
| Reported peripheral speed / CJ reference | 1893 / 2471 m/s |
| Axial pressure stations | 0, 22.2, 34.9, 47.6, 60.3, 73.0 mm |
| Corresponding mean pressures | 368.5, 323.3, 292.3, 281.1, 255.4, 238.4 kPa |

Sources: Mundt Tables 2-1, 2-2, 3-2 and 4-1, printed pp. 28, 37, 52, 80. Preserve the additional duct readings as reference data, not as pressure conditions imposed directly at the annulus exit. Preserve injector dimensions and the other engine configurations from the paper when creating the reference dataset; the archived plan contains a useful transcription to check against the original.

Mundt's speed convention uses the outer circumference. For `N` uniformly rotating waves and measured passage frequency `f`, compare `omega = 2 pi f/N`, `D_outer = omega r_o`, and the reduced model's `D_mean = omega r_m`. These are different linear-speed conventions, not measurement uncertainty. In a simulation comparison, derive `N` and `f` from the simulation; substituting experimental wave count into simulated speed is a separate conditional diagnostic.

**Graph-reference dataset:** maintain one canonical record per experimental condition/repeat group, shared by every figure that reuses it. Chapter 3's main comparison sweeps are nominally `phi = 1.15` and mass flux `243 kg/(s m²)`; Run 937 has its own exact inputs above. Use the actual tabulated/digitized conditions, not universal 320-point substitutions. Follow the [graph roadmap](docs/plans/figure_validation_roadmap.md) for data provenance, measurement operators, figure coverage, and implementation order.

### 2.2 Chemistry: distinguish physical references from the surrogate

The paper's Eq. 1.11 is introductory theory, not a validated Run 937 one-step
parameter set. Current Ea/(R T1)=20, 1 mm half-reaction length, constant R/gamma
and the fitted rate are project choices. See the [audit](docs/verification/mundt_model_audit.md)
for the physical/surrogate comparison and unresolved reference discrepancies.

Maintain two reference calculations:

1. Physical thermochemistry and, where needed, detailed-chemistry CJ/ZND results for the documented mixture and state. Record mechanism, thermodynamic data, solver version, and induction definition. A constant-volume ignition calculation at a selected VN state is a useful auxiliary reference, but is not itself a ZND calculation.
2. The constant-gamma, constant-gas-constant surrogate actually solved by the prototype. Fitting its CJ speed does not establish correct product thermodynamics, reaction structure, or mixing behavior.

For the initial Run 937 physical reference, use Cantera with SDToolbox and the
paper's GRI-Mech 3.0 mechanism for CJ, frozen post-shock and ZND calculations.
Reproduce the CEA CJ-equilibrium heat-release convention, or identify another
package/database as an independent cross-check rather than exact CEA replication.
Record package/mechanism versions, state definitions and convergence. The
D3 calculations are now implemented in `reference.py`: a five-point CJ/heat-release
neighborhood and nominal ZND with stricter-tolerance repeat. The heat-release
result is an independent Cantera/GRI-Mech cross-check; NASA CEA was not executed.
The nominal result is 2531.86 m/s, 5.41847 MJ/kg and 3994.14 K at CJ, with a
0.03952 mm shock-to-half-heat distance. The fixed surrogate remains 2471 m/s,
5.5 MJ/kg, 4885.15 K and 1 mm. These differing structures require assessment,
not automatic retuning. The factor-29 induction proxy is 1.0644 mm, not an
observed CFD cell width. Full G0 curves and exact paper reconciliation remain
pending. Detailed chemistry has not been installed into the CFD source.

A two-step induction/reaction model is a candidate repair for the starter's observed premature burning. Verify it before making it the production default. Use distinct progress variables for induction and reaction; conserve stored chemical energy consistently. If total energy already contains unspent chemical energy, do not add that heat a second time as an energy source.

**Correct the reaction-length specification.** With revision 3's proposed `Delta_I = Delta_R = 0.25 mm`, `k_R = u_VN/Delta_R`, and its supplied calibration, the shock-to-50%, 90%, and 95% reaction distances are approximately **0.518, 1.652, and 2.275 mm**. The full reacting region is not 0.75 mm. Integrate distance using the changing shock-relative velocity along the ZND path and report several completion fractions. Select a model and a mesh based on the resulting structure; do not impose an unsupported universal reaction-length/fill-height ratio.

Freeze chemistry parameters during mesh/time-step convergence studies. Changing reaction lengths when changing the grid is a separate model-sensitivity experiment. A fixed empirical multiple of physical induction length does not establish the cell width of an artificially thickened two-step model.

Verify induction-event timing, partially advanced induction states, and reaction-source time integration. Clipping an induction variable after RK stages does not by itself guarantee reliable threshold crossing. Test both freshly injected and partially advanced material. No claim that an induction clock automatically eliminates numerical contact burning.

### 2.3 Injection, walls, outlet, and initial conditions

The paper's hardware uses 72 separate fuel/oxygen pairs, holes inclined 30 degrees
to the axis, and impingement 2.16 mm above the injector face. Its 300 K premixed
CJ/ZND calculation does not justify complete mixing at the injection boundary.
The physical inner core ends at 76.2 mm inside a longer outer core; our outlet
omits that expansion. The tabulated 100.2 kPa back pressure is not a measured
annulus-exit boundary condition. A radial pre-detonator at z=73 mm differs from
our zero-velocity hot-patch start. These are explicit closure/initialization
assumptions requiring assessment, not reproduced construction details.

The first injector model may be a pressure-responsive equivalent premixed boundary. Document the conversion from two experimental feeds, discharge coefficient, area ratio, composition, and enthalpy. Choose either imposed flow or plenum-driven predicted flow for each case. Do not independently prescribe incompatible plenum conditions and mass flow. Any fitted discharge coefficient is recorded as calibration and then frozen for validation cases.

Check blocked, unchoked, and choked injection limits, including consistent pressure and velocity at the injection plane. State explicitly if reverse flow is suppressed; this omits injector backflow dynamics. Account for both open injector area and the remaining injector face in momentum/pressure forces.

A zero-gradient outlet **does not impose choking**. Diagnose the velocity normal to the exit, `u_z/a`, and the characteristic behavior. Check sensitivity to downstream extension/location and outlet treatment; use a physically appropriate subsonic pressure condition where needed. The pressure drop measured in the downstream duct is evidence to examine, not proof that an arbitrary numerical exit is sonic everywhere.

Begin with a smooth-wall Euler baseline. Add a separate, tested wall-friction closure for the torque estimate; optional heat loss is another model choice. For a constant annulus, lateral wall area per volume is `2/g`. If `C_f` uses the convention `tau_w = 0.5 C_f rho |U|²`, the corresponding mean momentum sink has the `C_f/g` factor. Stationary adiabatic wall friction redistributes resolved kinetic/internal energy without removing total energy; a heat-loss model has a separate energy sink.

Do not tune friction or heat loss simply to reproduce the gap trend. The closure coefficients and thermal assumptions need sensitivity studies; the starter does not presently implement these wall models.

Use periodic ignition masks and record discretized fresh inventory, geometry and net energy change relative to the pre-mask state; this is not a measured igniter energy. Startup choices can select modes. An operating refill height obtained from measured frequency may be adopted for initialization, but is not a paper-specified startup state, and recovering it is not independent validation. Control or quantify the charge/energy change when refining cell-center masks. Exclude startup from reported means only after checking histories. A second initialization is needed when mode selection materially affects the result.

## 3. What changing the annular gap means in 2D

For a constant straight annulus:

`g = r_o - r_i`, `r_m = (r_o + r_i)/2`, `W = 2 pi r_m`, and `A_e = W g = pi (r_o² - r_i²)`.

The area identity is exact. Replacing the radial dimension by a depth `g` does not preserve radial dynamics.

| Gap-related effect | In the first reduced 2D model? |
|---|---|
| Circumference and azimuthal path length when radii change | Yes, through `W`; this is not resolved cross-gap curvature |
| Annular flow area, total mass flow, and integrated exit force | Yes, through `A_e`, with the feed constraint stated |
| Injector area ratio `sigma = A_inj/A_e` | Yes, if injector area is retained and the ratio is recomputed |
| Changes to local injection flux caused by the chosen feed model | Yes; depends on fixed flow versus fixed plenum conditions |
| Increased wall loss per volume as gap narrows | Only through an explicitly enabled and validated closure |
| Radius weighting in torque | Approximate mean-radius treatment initially; full radial moments later |
| Radial pressure/velocity gradients and a curved front spanning the gap | No |
| Inner/outer-wall wave differences, radial reflections, transverse structure | No |
| Resolved cross-gap jet mixing, boundary layers, and wall heat transfer | No |
| Chamfers, taper, eccentricity, or locally varying `g(theta,z)` | No in the first constant-gap domain |

**An essential limitation:** hold `r_m`, `L`, chemistry, per-area injection conditions, injector area ratio, and initial local fields fixed, and turn wall closures off. Changing only the uniform depth `g` then leaves the reduced local flow equations unchanged. Pressure fields, wave speed, and modes can be identical; integrated mass flow and force scale with `g`, while specific impulse is unchanged. This is a limiting-model invariance, not evidence that real gap physics is irrelevant. Include a diagnostic check that demonstrates it.

At fixed outer radius, changing gap also changes mean circumference, so that invariance no longer applies directly. For the 25 mm engine (`r_o = 12.7 mm`):

| Gap | Mean circumference | Annular exit area |
|---|---|---|
| 3 mm | 70.37 mm | 211.12 mm² |
| 5 mm | 64.09 mm | 320.44 mm² |
| 7 mm | 57.81 mm | 404.64 mm² |

These derived geometric changes affect the reduced model, but do not restore its missing radial physics. Every sweep must state which of outer radius, mean radius, injector area, mass flow, mass flux, and plenum conditions is held fixed. They cannot all be fixed independently.

### Keep Mundt's two studies distinct

- **Radius study:** outer diameters 76.2, 50.8, and 25.4 mm; the absolute gap stays **5 mm**, while `L` follows outer diameter. Relative gap `g/r_o` increases from approximately 0.13 to 0.20 to 0.39. Radius, length, curvature, and relative confinement therefore change together. The reduced model captures circumference and length changes but cannot isolate all radial/curvature contributions.
- **Gap study:** fixed 25.4 mm outer diameter and 25.4 mm length; gaps 3, 5, 7, and 12.7 mm, the last being coreless. The same injector was used. Changing gap therefore also changes injector-to-annulus area ratio and jet placement relative to the walls. The 3 mm configuration has a relevant core chamfer near the impingement region. Do not interpret this as a pure wall-loss experiment.

Sources: Mundt §2.2, especially printed pp. 27–35, and Table 4-1 / discussion on pp. 79–80. The **coreless case is outside the first thin-annulus model's supported geometry**. An area-equivalent rectangle is insufficient evidence that its wave and torque physics are represented.

Consequently, 2D is useful for a first observable, testable simulation. Predictive comparisons of wide-gap, varying-gap, and coreless engines require the later geometry-resolving work in section 8. A failure of the reduced model to reproduce these trends should trigger a model assessment, not arbitrary chemistry retuning.

## 4. Keep the application independent of the CFD backend

**Migration decision:** build a small backend boundary now. Reusing the application should be manageable; replacing the solver and establishing equivalent physics will still require substantial work. Do not promise a drop-in library swap or identical predictions across different physical models.

The intended flow is:

`physical case + geometry → backend preparation → native solver run → native reductions/results → shared comparison and visualization`

### 4.1 Physical case and geometry contracts

A versioned case description stores SI units, coordinate system, engine axis/origin, positive azimuthal direction, geometry reference, feed definitions, ambient conditions, initial/ignition conditions, requested physical models, and diagnostic locations. Separate backend-specific settings such as mesh resolution, flux scheme, CFL, decomposition, and chemistry integrator tolerances.

Preserve separate fuel/oxidizer streams, species and thermodynamic state definitions, physical injector areas, and stable boundary/region identities. The first backend records its premixed reduction explicitly. Do not make a six-component prototype conserved-state array the universal physical case definition.

Record capabilities for each backend: supported dimension, geometry restrictions, chemistry, transport/walls, feeds, and restart behavior. Reject unsupported cases before launching. Do not silently flatten a chamfer, remove a nozzle, average a variable gap, or merge feeds. An explicitly selected reduced representation must list its omissions.

### 4.2 Minimum backend interface

The interface needs only these responsibilities initially:

- Check support and prepare a run directory/case with immutable inputs and provenance.
- Execute, monitor progress, and stop a run; restart using that backend's own checkpoint format where supported.
- Expose time histories and field snapshots or readers, including a partial running result.
- Compute agreed integral observables from native faces/volumes and export their definitions and units.

Use one real backend first, wrapping the starter. Avoid implementing a broad plugin framework before a second backend exists. Keep numerically intensive time stepping inside the native solver; do not require Python callbacks on every CFD step. Cross-backend checkpoint conversion is not promised.

### 4.3 Results that can represent both 2D and 3D

Shared results include time, mesh/coordinate metadata, pressure, density, temperature where defined, three-component velocity with a declared basis, optional species, diagnostic time series, forces, moments, and model provenance. Progress/induction variables are optional model-specific fields, not mandatory detailed-chemistry species.

Support cell/face/point field location, connectivity, boundary IDs, and changes of mesh topology. An array shaped `[ny,nx,6]` cannot be the application-wide storage contract. Retain native OpenFOAM or other backend output and stream selected fields; do not convert every future 3D result into one in-memory NPZ array.

Define common measurements in physical coordinates: pressure stations, circumferential sample rings with stated radius and axial location, integrated exit force, wall torque, and mass/energy/angular-momentum budgets. Compute integrals on the native mesh. Resampled display slices are unsuitable for authoritative force accounting. Record whether a pressure comparison is a local wall/probe value or a circumferential/radial average.

Declare energy/enthalpy reference conventions and pressure type. Detailed species models and the prototype's stored-chemical-energy variable are not interchangeable numerical fields.

### 4.4 Concrete implications for detonationFoam

Inspected source: JieSun-pku/detonationFoam, branch `detonationFoam_V2.0_OF8`. Its README targets OpenFOAM 8; its executable dispatches Euler, Sutherland-transport Navier–Stokes, and mixture-average-transport Navier–Stokes modes. Integration should generate native cases, launch the compiled solver, monitor it, and read/reduce its outputs. It is not a Python chemistry package imported in place of `solver.py`.

The supplied tutorial inspected is a 1D ammonia/oxygen detonation case, not a configured Mundt methane/oxygen RDE. It is useful for installation verification, not a ready-made replication case. Its mesh/conditions and chemistry must not be copied as target-engine inputs.

| Work likely reusable | Work requiring backend-specific implementation or renewed verification |
|---|---|
| Physical cases, source/uncertainty tables, geometry manifest | Mesh construction, boundary naming/mapping, native case dictionaries |
| Run management and progress UI | Process launch, parallel execution, native output and restart adapters |
| Definitions of pressure, thrust, torque, wave diagnostics | Native integrations, chemistry/energy conventions, field extraction |
| Plotting, visual inspection, measured-versus-predicted reports | Injector/outlet/wall conditions and their physical validity |

The application integration should be bounded if these contracts are respected. The CFD migration risk remains appreciable: detailed chemistry, transport, numerical diffusion, and boundary conditions can change the predicted solution. Revalidate the physics after migration.

On the independent 3D track, pin a compatible environment and upstream revision, build/run the upstream example, verify simple hydrodynamic/detonation references, then construct a matched reduced 2D RDE case before adding 3D. Check the exact needed AMR/parallel/transport features in that selected version; the presence of a `dynamicMesh2D` option is not evidence of a ready 3D adaptive RDE workflow. Backend selection is provisional until this representative-case evaluation succeeds.

Sources inspected: upstream `README.md`; `applications/solvers/detonationFoam_V2.0/{detonationFoam_V2.0.C,Allwmake,Make/files,Make/options}`; tutorial `system/{controlDict,blockMeshDict}` and `constant/solverTypeProperties`. Repository: `https://github.com/JieSun-pku/detonationFoam`. Associated solver paper: Sun et al., *Computer Physics Communications* 292 (2023), 108859. No upstream build was performed during planning.

### 4.5 Required file separation; keep the workflow simple

**Physics, tests, and plotting must be separate files.** Use the existing starter directory, one small `tests/` folder, and ordinary function calls. Keep numerical analysis separate from both simulation and rendering so plots can be changed without rerunning CFD.

Proposed layout when coding begins:

```text
rde_sim_starter/
  physics.py             # Equation of state, chemistry, physical wall/source laws
  solver.py              # Fluxes, reconstruction, time stepping and boundary application
  calibrate.py           # Reference/calibration calculations; returns data, no plotting
  run.py                 # Thin one-case CLI: load inputs, execute, save results
  analyze.py             # Pure numerical reductions from saved or supplied results
  plot.py                # All figure/animation rendering; never advances the solver
  config.yaml            # Initial Run 937 inputs; snapshot with every run
  tests/
    test_physics.py       # Energy/source timing and physical limiting cases
    test_solver.py        # Short 1D numerics, boundaries and discrete balances
    test_analysis.py      # Force reductions and known-signal tracking checks
  runs/<run_id>/          # Immutable inputs, fields/probes, metrics and figures
```

Reuse existing functions and move only what crosses these boundaries; fold the useful checks in the current `test_1d.py` into `tests/test_solver.py` rather than maintaining duplicate test paths. Physics/solver code must not import tests or plotting. Tests call production functions and assert results; they do not contain a second solver. `analyze.py` computes metrics without rendering; `plot.py` may call that analysis on saved data. Imports must not start simulations, tests, calibration runs or figures.

Use one lightweight test runner (standard-library `unittest` is sufficient), one run entry point, and one plotting entry point. Proposed commands below are a **future CLI contract**, not implemented commands:

```text
cd rde_sim_starter
python -m unittest discover -s tests
python run.py --case config.yaml --test-passages 3 --out runs/run937_short
python plot.py runs/run937_short
```

The optional five-interval check resumes the saved run to a total duration limit. `plot.py` produces the selected fields, profiles and report from that run; it never launches another simulation. Do not introduce a workflow engine, job service, abstract plugin registry, per-figure scripts, or per-engine plotting modules. Keep the future backend contract as a small set of functions/metadata until a second backend is implemented.

## 5. Verification, thrust, wave inspection, and torque

### 5.1 Numerical verification before predictive claims

Reproduce meaningful starter baselines before modifying physics. Check an exact nonreacting shock problem, chemical-energy conservation, reactive source timing, 1D detonation speed/structure, periodic boundaries, and a simple known-flow force case. Test failures must be explicit; a printed result alone is not a passing assertion.

Record nonfinite states, invalid density/pressure, clipping/floor operations, and associated mass/energy changes. Repeated state repair is a failed or qualified run, not hidden stabilization. Fix ghost-state conversion and boundary inconsistencies identified in the review.

Use the actual time-integrated numerical boundary fluxes and source terms, including RK weights, for conservation diagnostics. Reconstructing cell-centre fluxes after the update need not reproduce the fluxes that advanced the state. Retain finite-window storage of mass, energy, axial momentum, and axial angular momentum. Inlet/outlet equality is not expected during physical accumulation.

For the overnight test stage, apply §0's three-interval default and five-interval maximum; run only the targeted sensitivity check needed for an identified concern. Full fixed-model grid, source-tolerance, outlet and averaging-window studies are follow-on validation. Measure cost before choosing later production runs. Passing a short test establishes only the behavior it actually exercises, not completed CFD validation.

### 5.2 Thrust estimation and validation

For a planar annulus exit, the first reported exit momentum/pressure contribution is

`F_exit = integral_Ae [rho u_z² + (p - p_ambient)] dA`.

If normal viscous traction is modeled, include its consistent contribution. This is an **annulus-exit thrust estimate**, not automatically the force on an entire installed engine. A whole-engine definition needs its chosen control volume, inlet momentum, external/base pressures, nozzle/duct surfaces, and storage terms. Compare the exit estimate with a consistent injector/wall/control-volume balance; do not add overlapping force definitions together.

Use `I_sp = mean(F)/(mean(mdot_propellant) g0)` with the same force definition, averaging interval, and propellant streams. Separate mass-flow prediction error from specific-impulse error.

Validation order:

1. Known-flow force case and discrete conservation with storage retained.
2. Fixed-model mesh/time-step/outlet/window sensitivity.
3. Mundt Run 937 pressure and wave comparison as supporting flow evidence. Mundt does not provide a measured thrust value to validate against.
4. A separately specified force-measurement experiment with matched geometry, operating point, ambient conditions, and force definition.
5. A held-out condition with fitted parameters frozen, before claiming predictive accuracy.

A candidate is Bennewitz et al., *Experimental validation of rotating detonation for rocket propulsion*, Scientific Reports 13, 14204 (2023), DOI `10.1038/s41598-023-40156-y`. Its nominal 76.2 mm engine cases at 0.272 kg/s and equivalence ratio 1.1 report 387 ± 2.22 N at AFRL and 367 ± 5.10 N at Purdue. Preserve each facility's result and exact setup separately; do not attach these force values to Mundt Run 937. Complete apparatus/control-volume matching before using either as a quantitative target.

The first working iteration may report an estimate before measured-thrust validation is complete. Report the discrepancy and the achieved limits when validation is attempted; do not force success by retuning chemistry, discharge, and friction on the validation point.

### 5.3 Human-readable wave assessment

Provide pressure and reaction-progress/heat-release animations, a circumferential space–time plot, tracked front paths, wave-count/speed estimates, and visible extinction or mode-change markers. Show simulated duration and averaging window. Demonstrate continuing shock-associated heat release after ignition; a moving pressure pulse alone does not establish detonation.

Distinguish passage frequency, wave count, angular speed, and linear speed. Check FFT harmonics with front tracking or arrival times. A heat-release view is synthetic and is not a calibrated camera-luminosity model. Do not transfer the paper's 58% camera-power criterion directly to it as a validated classifier.

Use “no sustained detonation detected” when appropriate. An Euler model with local chemistry but no physical heat/species diffusion does not establish a validated deflagration regime. Any off-front burning metric is initially a proxy; a fixed 2 mm distance from a probe peak cannot reliably distinguish a long reaction tail from contact burning.

### 5.4 Torque and roll response

Use the same axis/origin/sign convention for wall forces and angular flux. For a fixed control volume with no other applied gas torque,

`tau_engine = Phi_L,in - Phi_L,out - dL_gas/dt`,

where `L_gas = integral_V rho r u_theta dV` and `Phi_L` denotes advective angular-momentum flux. Include additional pressure/viscous torques on open control surfaces when the chosen geometry makes them nonzero. Independently integrate torque from modeled gas tractions on engine surfaces.

In a smooth axisymmetric inviscid annulus with zero injected angular momentum, the engine has no azimuthal wall traction, and a statistically stationary average cannot continuously export net angular momentum without an opposing torque. Local swirl and a rotating wave can still exist. Do not infer a sustained engine torque from a short transient exit flux alone.

For iteration 1, a wall-friction closure supplies a model-dependent torque estimate. Check the angular balance including storage, reversed-direction symmetry, and coefficient sensitivity. Let the torque sign emerge. Mean-radius moments are approximate; for uniform shear the inner/outer wall moment weighting is not exactly `r_m`, particularly at wide gaps.

Sawada et al., *Torque Around Axial Direction on Rotating Detonation Engines*, JPP 38(1), 59–70 (2022), DOI `10.2514/1.B38374`, is a potential later benchmark. Its 8.8% azimuthal-shear/thrust ratio is specific to its experiment, not a universal calibration rule. Obtain the complete geometry and conditions before claiming matched validation. Until then, label target-engine torque unvalidated.

With a specified constant inertia, `d omega_vehicle/dt = tau_engine/I` provides an illustrative roll response. Structural survival, vehicle orientation stability, and control authority require additional models. The rotating detonation's wave speed is not bulk gas speed or vehicle roll speed.

## 6. Visibility and reproducibility from the beginning

Each run stores immutable physical inputs, backend configuration, model/reference versions, geometry identity, numerical resolution, fitted-parameter provenance, and diagnostic definitions. Analysis reads this saved record, not a subsequently edited shared configuration.

From the first 2D run, provide a periodically refreshed field preview, progress/state-validity report, and low-volume probe/force histories. Save restart checkpoints and selected snapshots incrementally. Choose cadence from measured cost and desired frequency resolution; avoid buffering all fields in memory.

Useful views: unrolled pressure plus reaction fields; a space–time plot; axial pressure against experiment; mass/energy/momentum balances; and thrust/torque histories with averaging windows. Add wrapped-cylinder and synthetic head-end views once the basic field display works. Label their 2D origin. Support partial analysis while a long run continues.

## 7. Milestones and intermediate results

**Scheduling:** §0 and the controlled-test companion record completed D0–D3 and the authorized C1–C6 investigation. The separate 3D track may proceed independently; the historical stage ordering below does not block its backend evaluation. The table below retains the full project sequence. The current prototype does not claim completion of stages 0–4; Stage 1's physical-reference subset has progressed, but its refinement assessment and Stage 3's sustained-wave criterion remain open.

Stages gate the claims made from their output, not every useful parallel activity. A failed coarse mesh does not prohibit studying a better-resolved mesh. CAD contract work and importer development can proceed in parallel without delaying the first CFD result.

| Stage | Work and visible result | Exit evidence |
|---|---|---|
| **0. Case and interface definition** | Freeze Run 937/reference provenance; record reduced geometry limits; specify versioned case, geometry, backend, and results contracts. Prepare the separate thrust benchmark specification and graph-reference registry (**G0** below). | Inputs, fitted quantities, force definition, and omitted physics are unambiguous. CAD/backend developers have a stable starting contract. |
| **1. Physics/numerical baseline** | Reproduce starter baselines; separate physical/surrogate references; verify source timing and corrected reaction profiles. Show 1D profiles and shock paths; begin Chapter 4 thermochemical reference plots (**G0**). | Credible conservation, detonation structure/speed, and fixed-model refinement; errors explicitly reported. |
| **2. Feed/outlet and force accounting** | Nonreacting fill/outlet cases and simple force case; native-flux budgets with storage. Show pressure/filling and budget histories. | Feed limiting cases and force signs close consistently; outlet assumptions have a defined check. |
| **3. First visible 2D wave** | Run 76-FI-5; live pressure/reaction fields, checkpoints, front tracking, space–time plot (**G1**). Add/test wall friction separately for the initial torque estimate. | Sustained shock-coupled burning after ignition without hidden repairs; force and angular budgets checked. Exact paper wave count is not a gate to further investigation. |
| **4. First working iteration** | Fixed-model resolution/time/outlet/window checks; Run 937 pressure/wave checks (**G1–G2**); thrust and qualified torque estimates; reusable viewer/report. | Numerical sensitivity is quantified; measured-versus-predicted discrepancies and missing physics are visible. This qualifies the 2D iteration; independent 3D/backend work need not wait for it. |
| **5A. CAD import — TO BE IMPLEMENTED** | Implement/import the geometry manifest, preview and validate a known assembly, connect a supported reduced case. Independent contract/importer work may have started during stages 0–4. | Known annulus dimensions/areas agree with the manual case; omitted features are explicit; unsupported geometry cannot silently run in 2D. See section 9. |
| **5B. Established CFD backend evaluation** | Pin/build candidate such as detonationFoam; verify upstream/simple cases; create matched reduced RDE case through the adapter. | Reproducible environment, mapped physical conditions, readable results, and checked force/energy conventions. Choose backend based on evidence. |
| **5C. Validation and reduced-model limits** | Run measured-thrust cases and friction sensitivity. Add radius-study sweeps (**G3**), back-pressure profiles (**G4**), then the 51-FI-5 map (**G5**). Begin derived Chapter 4 comparisons (**G7**) and retain the depth-invariance check. | Report achieved accuracy and which discrepancies require richer physics. Maps may be exploratory; full mode-map agreement is not required. |
| **6. Parametric 3D annulus** | Resolve `r,theta,z` on a full annulus, initially with controlled/simple feed. Compare with reduced 2D, then extend gap/curvature comparisons and pressure/back-pressure cases (**G6**, extended **G4**). | 3D numerical/physical sensitivity is assessed and added effects are identifiable; see section 8. CAD is not a dependency for the first parametric 3D case. |
| **7. CAD-driven 3D engine** | Connect preserved CAD fluid volume and boundaries to meshing/backend; add real injector geometry/mixing and relevant exit features. Complete supported gap/operating maps (**G6**), derived comparisons (**G7**), and held-out tests (**G8**). | Imported geometry, boundary roles, meshing, loads, and matched experimental comparisons are verified. |

Stages 5A–5C are parallel tracks where practical, not a requirement that CAD wait for every thrust or torque validation study. Stages 6–7 are explicit project requirements for predictive gap/geometry studies, not cosmetic visualization upgrades.

### 7.1 Added workstream: graph validation against Chapters 3 and 4

The [figure-by-figure roadmap](docs/plans/figure_validation_roadmap.md) is part of this plan. It covers **all 35 Chapter 3 figures, Table 3-3, and all 31 Chapter 4 figures**. For the deadline, implement only the necessary Run 937 reference subset and G1 field/front/pressure/budget views; defer G2 spectral work and the G3–G9 campaigns. Implement common measurement, reduction, and plotting functions in the separate files specified in §4.5, then select the engine and dataset through configuration. Do not create a separate simulator or plotting function for every figure.

| Step | Calling/reduction/plotting work, in order | First comparison and later reuse |
|---|---|---|
| **G0. Reference data and thermochemistry** | Reference registry; case lookup; CJ/heat-release reference curves, then ZND induction/cell-size proxy; distinguish predicted, fitted, and imposed values. | Small Run 937 reference neighborhood first; Fig. 4.3, then 4.4, then 4.2. Expand before equivalence-ratio sweeps. |
| **G1. Run 937 direct checks** | Sample physical pressure stations and a circumferential ring; compute stationary means, pressure profiles/residuals, front paths, passage frequency and wave count. | Table 3-2; Fig. 3.2 right; Figs. 3.4–3.5 as qualitative structural comparisons. These are the first additional accuracy checks. |
| **G2. Frequency diagnostics** | Reuse ring/probe data for 2D FFT, rolling frequency, spectra and spectrograms, with explicit sample/window lengths. | Figs. 3.6–3.7; only frequency-level comparison to plenum PCB Figs. 3.8–3.10 initially. |
| **G3. One-dimensional sweeps** | Generic sweep runner → cached per-run metrics → trend/overlay plots. Mass-flux sweep first, equivalence-ratio sweep second. | 76-FI-5 first, then 51-FI-5, then a qualified 25-FI-5 subset. Figs. 3.19–3.27; build the simple 76 mm map, Figs. 3.11–3.12, from those same runs. |
| **G4. Back-pressure response** | Reuse pressure-profile plotter with ambient-pressure sweeps and front-pressure normalization. | Fig. 3.35 before complex maps; then a sparse Table 3-3 comparison, expanding after the relevant 25 mm physics is supported. |
| **G5. 51-FI-5 averaged map** | Extend the sweep runner to sparse operating-point lists, repeat groups, human-reviewed mode labels, and measured/predicted categorical panels. | Fig. 3.13, p. 55: 12–20 selected points first; denser/transition samples and broader coverage later. Reserve off-sweep holdouts. |
| **G6. Gap study and remaining maps** | Reuse the same trend/map functions; add geometry-specific cases and capability checks. | 25-FI-5 baseline → limited 25-FI-7 sweep → chamfered 25-FI-3 → coreless 25-FI-12.7. Figs. 3.14, 3.16–3.18, 3.28–3.34. Predictive wide-gap/coreless comparisons require suitable 3D physics. |
| **G7. Chapter 4 derived comparisons** | Shared derived columns and scatter specifications; add graphs as their input data become available. | Early: pressure collapse 4.1, fill-height comparison 4.5, energy supply 4.19 and pressure–energy relation 4.21. Then geometric/cell-size/per-wave plots. Full all-engine panels follow G6; Fig. 4.15 can be checked earlier from references alone. |
| **G8. Independent off-sweep checks** | Freeze model parameters; run reserved operating points; reuse maps and compute discrepancy/coverage summaries. | Figs. 4.30–4.31 and the pressure/frequency predictions discussed on p. 103. |
| **G9. Optional later measurement models** | Add feed/plenum dynamics, instrumentation or thermal/structural models only if these become explicit project scope. | Full transients/spectral amplitudes in Figs. 3.1–3.3 and 3.8–3.10; Fig. 3.15 is a damage photograph, not a first CFD benchmark. |

**51-FI-5 map: deferred beyond the deadline.** The earlier effort estimate (2–4 person-days for a sparse comparison, another 1–2 person-weeks for broader coverage) describes follow-on work, not tonight's scope. Three-to-five-passage tests make individual development checks shorter but do not establish an averaged operating map. The roadmap retains longer-run campaign estimates as explicitly deferred context; no 3 ms or 10 ms campaign is part of the current test stage.

**Interpretation rules:** pressure/frequency comparisons test simulated observables; imposed feed conditions are setup checks; Chapter 4 thermochemistry and input-derived correlations are reference/postprocessing checks. Do not present them all as independent CFD validation. Keep human wave inspection as planned, with “uncertain,” “unsupported,” and “numerically failed” outcomes distinct from physical extinction.

**New source correction:** Fig. 3.35's high-flux blue reference is **160 kg/(s m²)** in its legend and in the original paper's Fig. 17 (Mundt et al., AIAA 2023-1104). The dissertation's p. 70 prose says 180. Use the figure/original-paper value and retain the discrepancy in provenance. Keep the four curves' individual equivalence ratios and back pressures.

## 8. 3D physics track

**Independent track: backend evaluation may start now in the separate 3D session.** Start from a parameterized straight annulus so radial-physics development does not depend on completion of CAD import.

Use a domain retaining azimuthal variation and axial refill/exhaust. Axisymmetric `(r,z)` removes the rotating-wave degree of freedom. A radial–azimuthal slice can study selected curved-front phenomena but omits axial refill/exhaust. Neither replaces the intended full RDE calculation.

Start with a full 360-degree annulus for unrestricted wave-count comparisons. A periodic sector imposes repetition and restricts possible modes; use it only for an explicitly constrained study.

Introduce complexity in identifiable steps: curved 3D geometry with simple controlled feed, radial resolution study, appropriate transport/wall models, then resolved injector mixing and relevant chamfers/exits. Adding radial cells alone does not supply physical boundary layers, diffusion, or heat transfer. Assess reaction and radial resolution, time-step/source accuracy, wall treatment, and computational cost for each model.

Compare 2D and 3D at matched physical conditions and explicitly matched chemistry where possible. First use 76-FI-5, then wider relative gaps. Separate a controlled gap sweep from a faithful reproduction of Mundt's coupled geometry/injector changes. Recompute thrust and torque on actual surfaces/volumes with physical moment arms. A richer model requires its own verification and experimental comparisons.

Preserve `r_i(theta,z)`, `r_o(theta,z)` or general CAD surfaces for future nonuniform gaps. The first backend cannot represent these by merely changing one scalar gap. Nonaxisymmetric surfaces can introduce pressure torque in addition to wall shear; the 3D load model must include the relevant tractions.

## 9. CAD import track and parallel development handoff

**Status: TO BE IMPLEMENTED. Integration follows the first working iteration. Geometry contract design, parser research, and an independent importer may start in parallel now.** No CFD solver changes are required just to begin this work.

Agree the geometry manifest in stage 0. Proposed contract requirements:

| Contract item | Required information |
|---|---|
| Identity and provenance | Schema version, source files/hashes, format, assembly/part identity, units, conversion to SI, tolerances |
| Coordinates | Transforms, engine axis and origin, axial/azimuthal sign conventions |
| Full representation | Preserved solids/surfaces, assemblies, and connected fluid volume(s); do not discard geometric details after extracting radii |
| Physical regions | Stable IDs/roles for fuel and oxidizer openings, injector face, inner/outer walls, exit, and other relevant boundaries |
| Derived quantities | Areas, volumes, gap distribution and minimum clearance, with extraction method/tolerance |
| Optional reduced representation | Constant `r_o`, `r_i`, `L`, injector areas and calculated `g`, `A_e`, `sigma`, only when valid; explicit approximations and omitted features |
| Meshing handoff | Geometry and boundary identities usable by a backend-specific mesher; native mesh/case formats remain adapter responsibilities |

Proposed initial exchange format: STEP for solid/assembly geometry. Evaluate the actual CAD kernel and meshing library during implementation; no package choice is finalized here. If STL is supported, account for its tessellation and missing intrinsic unit/semantic information. CAD geometry alone does not supply propellants, plenum conditions, wall temperatures, roughness, or the intended inlet/outlet roles; keep these explicit in the case or user-confirmed mapping.

The importer must distinguish the gas volume from surrounding solid parts, identify connected passages, preserve feature/boundary correspondence, and expose a geometry preview. Check units, tolerances, gaps/leaks, intersecting parts, and small passages that might be lost during healing/meshing. A successful file parse is not a usable CFD domain by itself.

Acceptance sequence: import a known annulus; compare dimensions, volume and boundary areas with analytic/manual values; map physical regions; generate the same supported reduced case and compare its inputs/results within declared geometric tolerance. Then test a representative chamfer/variable-gap/injector assembly. Retain these features for 3D; the first 2D backend must reject unsupported geometry or require an explicitly chosen reduced approximation with the omissions recorded.

This boundary allows a CAD developer to work independently of both the starter solver and OpenFOAM dictionaries. Deliver a versioned manifest plus source geometry and a preview; the CFD backend consumes those through its own meshing and case-preparation adapter.

## 10. Claims this plan permits

The first iteration can show a computed rotating, shock-coupled reaction; compare simplified pressures/wave measures; and estimate annulus-exit thrust and model-dependent torque with numerical sensitivity. It cannot yet establish accurate arbitrary-CAD predictions, fully resolved gap physics, validated physical deflagration limits, measured target-engine torque, or vehicle/structural stability.

The path to those stronger geometry and performance claims is explicit: usable reduced simulation → independent CAD/backend tracks and force validation → verified parametric 3D → CAD-driven 3D with relevant transport, injectors, boundaries, and matched experiments.
