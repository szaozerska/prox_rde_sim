# RDE simulation plan — revision 4

**Status: planning only.** This revision replaces the implementation instructions in revision 3. No simulation code has been changed. The unchanged [revision 3](first_sim_plan_rev3.md) is retained for comparison; the [planning review](../../sim_plan_review.md) explains its physics and implementation issues. Equations, defaults, and acceptance criteria in that archive are historical proposals, not requirements that override this plan.

**First working iteration:** a verified, reduced 2D simulation of the straight 76-FI-5 annulus, with visible shock-coupled reaction, pressure comparisons, an annulus-exit thrust estimate, and a clearly qualified torque estimate. Human inspection is the primary wave-stability assessment. This is an intermediate research model on the path to simulation of imported 3D engine geometry.

**Future requirements:** retain the ability to replace the CFD backend, resolve radial/gap physics in 3D, and import CAD assemblies or parts. CAD import is **TO BE IMPLEMENTED after the first working iteration**; its geometry contract and independent importer can be developed in parallel now. Sections 3, 4, 8, and 9 define these requirements and their order.

Paper references mean Mundt (2023), *Geometric Scaling of Cylindrical Rotating Detonation Rocket Engine Combustors*. Use printed page numbers; PDF page = printed page + 16. Fig. 1.1 is an illustrative flow/design image, not a measured 3D validation dataset.

## 1. Scope and decisions

- Reuse the small `rde_sim_starter` numerical prototype after verification. Keep useful flux, reconstruction, calibration, and plotting work; correct the deficiencies recorded in the review. Do not expand this prototype into a general CAD mesher or a new industrial 3D CFD framework.
- First solve a radially averaged, unrolled circumferential–axial domain, denoted `(x, z)`, where `x = r_m theta`. The radial direction is absent. A cylinder-wrapped display remains a visualization of this 2D solution.
- Start with 76-FI-5 / Run 937. Its relatively thin annulus is the best initial candidate among these engines for this approximation. Small, wide-gap cases are exploratory comparisons, not obligatory initial validation gates.
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

Mundt's speed convention uses the outer circumference. For `N` uniformly rotating waves and measured passage frequency `f`, compare `omega = 2 pi f/N`, `D_outer = omega r_o`, and the reduced model's `D_mean = omega r_m`. These are different linear-speed conventions, not measurement uncertainty.

### 2.2 Chemistry: distinguish physical references from the surrogate

Maintain two reference calculations:

1. Physical thermochemistry and, where needed, detailed-chemistry CJ/ZND results for the documented mixture and state. Record mechanism, thermodynamic data, solver version, and induction definition. A constant-volume ignition calculation at a selected VN state is a useful auxiliary reference, but is not itself a ZND calculation.
2. The constant-gamma, constant-gas-constant surrogate actually solved by the prototype. Fitting its CJ speed does not establish correct product thermodynamics, reaction structure, or mixing behavior.

A two-step induction/reaction model is a candidate repair for the starter's observed premature burning. Verify it before making it the production default. Use distinct progress variables for induction and reaction; conserve stored chemical energy consistently. If total energy already contains unspent chemical energy, do not add that heat a second time as an energy source.

**Correct the reaction-length specification.** With revision 3's proposed `Delta_I = Delta_R = 0.25 mm`, `k_R = u_VN/Delta_R`, and its supplied calibration, the shock-to-50%, 90%, and 95% reaction distances are approximately **0.518, 1.652, and 2.275 mm**. The full reacting region is not 0.75 mm. Integrate distance using the changing shock-relative velocity along the ZND path and report several completion fractions. Select a model and a mesh based on the resulting structure; do not impose an unsupported universal reaction-length/fill-height ratio.

Freeze chemistry parameters during mesh/time-step convergence studies. Changing reaction lengths when changing the grid is a separate model-sensitivity experiment. A fixed empirical multiple of physical induction length does not establish the cell width of an artificially thickened two-step model.

Verify induction-event timing, partially advanced induction states, and reaction-source time integration. Clipping an induction variable after RK stages does not by itself guarantee reliable threshold crossing. Test both freshly injected and partially advanced material. No claim that an induction clock automatically eliminates numerical contact burning.

### 2.3 Injection, walls, outlet, and initial conditions

The first injector model may be a pressure-responsive equivalent premixed boundary. Document the conversion from two experimental feeds, discharge coefficient, area ratio, composition, and enthalpy. Choose either imposed flow or plenum-driven predicted flow for each case. Do not independently prescribe incompatible plenum conditions and mass flow. Any fitted discharge coefficient is recorded as calibration and then frozen for validation cases.

Check blocked, unchoked, and choked injection limits, including consistent pressure and velocity at the injection plane. State explicitly if reverse flow is suppressed; this omits injector backflow dynamics. Account for both open injector area and the remaining injector face in momentum/pressure forces.

A zero-gradient outlet **does not impose choking**. Diagnose the velocity normal to the exit, `u_z/a`, and the characteristic behavior. Check sensitivity to downstream extension/location and outlet treatment; use a physically appropriate subsonic pressure condition where needed. The pressure drop measured in the downstream duct is evidence to examine, not proof that an arbitrary numerical exit is sonic everywhere.

Begin with a smooth-wall Euler baseline. Add a separate, tested wall-friction closure for the torque estimate; optional heat loss is another model choice. For a constant annulus, lateral wall area per volume is `2/g`. If `C_f` uses the convention `tau_w = 0.5 C_f rho |U|²`, the corresponding mean momentum sink has the `C_f/g` factor. Stationary adiabatic wall friction redistributes resolved kinetic/internal energy without removing total energy; a heat-loss model has a separate energy sink.

Do not tune friction or heat loss simply to reproduce the gap trend. The closure coefficients and thermal assumptions need sensitivity studies; the starter does not presently implement these wall models.

Use periodic ignition masks and record deposited energy/geometry. Startup choices can select modes. An initial fill height obtained from measured frequency is allowed as initialization, but recovering it is not independent validation. Exclude startup from reported means only after checking histories. A second initialization is needed when mode selection materially affects the result.

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

After the first working iteration, pin a compatible environment and upstream revision, build/run the upstream example, verify simple hydrodynamic/detonation references, then construct a matched reduced 2D RDE case before adding 3D. Check the exact needed AMR/parallel/transport features in that selected version; the presence of a `dynamicMesh2D` option is not evidence of a ready 3D adaptive RDE workflow. Backend selection is provisional until this representative-case evaluation succeeds.

Sources inspected: upstream `README.md`; `applications/solvers/detonationFoam_V2.0/{detonationFoam_V2.0.C,Allwmake,Make/files,Make/options}`; tutorial `system/{controlDict,blockMeshDict}` and `constant/solverTypeProperties`. Repository: `https://github.com/JieSun-pku/detonationFoam`. Associated solver paper: Sun et al., *Computer Physics Communications* 292 (2023), 108859. No upstream build was performed during planning.

## 5. Verification, thrust, wave inspection, and torque

### 5.1 Numerical verification before predictive claims

Reproduce meaningful starter baselines before modifying physics. Check an exact nonreacting shock problem, chemical-energy conservation, reactive source timing, 1D detonation speed/structure, periodic boundaries, and a simple known-flow force case. Test failures must be explicit; a printed result alone is not a passing assertion.

Record nonfinite states, invalid density/pressure, clipping/floor operations, and associated mass/energy changes. Repeated state repair is a failed or qualified run, not hidden stabilization. Fix ghost-state conversion and boundary inconsistencies identified in the review.

Use the actual time-integrated numerical boundary fluxes and source terms, including RK weights, for conservation diagnostics. Reconstructing cell-centre fluxes after the update need not reproduce the fluxes that advanced the state. Retain finite-window storage of mass, energy, axial momentum, and axial angular momentum. Inlet/outlet equality is not expected during physical accumulation.

Compare fixed-model grids, time steps/source tolerances, outlet choices, and averaging windows. Examine both local structure and integral quantities. No predetermined runtime or compulsory speedup is an acceptance condition; measure cost before choosing production run length, output cadence, and mesh.

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

Stages gate the claims made from their output, not every useful parallel activity. A failed coarse mesh does not prohibit studying a better-resolved mesh. CAD contract work and importer development can proceed in parallel without delaying the first CFD result.

| Stage | Work and visible result | Exit evidence |
|---|---|---|
| **0. Case and interface definition** | Freeze Run 937/reference provenance; record reduced geometry limits; specify versioned case, geometry, backend, and results contracts. Prepare the separate thrust benchmark specification. | Inputs, fitted quantities, force definition, and omitted physics are unambiguous. CAD/backend developers have a stable starting contract. |
| **1. Physics/numerical baseline** | Reproduce starter baselines; separate physical/surrogate references; verify source timing and corrected reaction profiles. Show 1D profiles and shock paths. | Credible conservation, detonation structure/speed, and fixed-model refinement; errors explicitly reported. |
| **2. Feed/outlet and force accounting** | Nonreacting fill/outlet cases and simple force case; native-flux budgets with storage. Show pressure/filling and budget histories. | Feed limiting cases and force signs close consistently; outlet assumptions have a defined check. |
| **3. First visible 2D wave** | Run 76-FI-5; live pressure/reaction fields, checkpoints, front tracking, space–time plot. Add/test wall friction separately for the initial torque estimate. | Sustained shock-coupled burning after ignition without hidden repairs; force and angular budgets checked. Exact paper wave count is not a gate to further investigation. |
| **4. First working iteration** | Fixed-model resolution/time/outlet/window checks; Run 937 pressure/wave comparison; thrust and qualified torque estimates; reusable viewer/report. | Numerical sensitivity is quantified; measured-versus-predicted discrepancies and missing physics are visible. This is the milestone after which CAD integration and backend implementation enter the main application. |
| **5A. CAD import — TO BE IMPLEMENTED** | Implement/import the geometry manifest, preview and validate a known assembly, connect a supported reduced case. Independent contract/importer work may have started during stages 0–4. | Known annulus dimensions/areas agree with the manual case; omitted features are explicit; unsupported geometry cannot silently run in 2D. See section 9. |
| **5B. Established CFD backend evaluation** | Pin/build candidate such as detonationFoam; verify upstream/simple cases; create matched reduced RDE case through the adapter. | Reproducible environment, mapped physical conditions, readable results, and checked force/energy conventions. Choose backend based on evidence. |
| **5C. Validation and reduced-model limits** | Run measured-thrust and held-out cases; friction sensitivity; separate radius/gap sweeps and the depth-invariance check. | Report achieved accuracy and which discrepancies require richer physics. Full mode-map agreement is not required. |
| **6. Parametric 3D annulus** | Resolve `r,theta,z` on a full annulus, initially with controlled/simple feed. Compare with reduced 2D, then test gap/curvature and transport effects. | 3D numerical/physical sensitivity is assessed and added effects are identifiable; see section 8. CAD is not a dependency for the first parametric 3D case. |
| **7. CAD-driven 3D engine** | Connect preserved CAD fluid volume and boundaries to meshing/backend; add real injector geometry/mixing and relevant exit features in controlled increments. | Imported geometry, boundary roles, meshing, loads, and matched experimental comparisons are verified. |

Stages 5A–5C are parallel tracks where practical, not a requirement that CAD wait for every thrust or torque validation study. Stages 6–7 are explicit project requirements for predictive gap/geometry studies, not cosmetic visualization upgrades.

## 8. 3D physics track

**TO BE IMPLEMENTED after the first working iteration and backend evaluation.** Start from a parameterized straight annulus so radial-physics development does not depend on completion of CAD import.

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
