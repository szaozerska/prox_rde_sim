# 3D RDE development plan - revision 18, propagation gate and runtime evidence

This branch develops a native three-dimensional methane/oxygen pipeline.
The October 22 GPU revision below controls execution order; the T0-T7 physics
gates remain applicable to whichever backend is selected. The
2D starter remains a small independent verification and investigation backend.
A successful 2D engine run is no longer a dependency for starting 3D work.
The [inherited 2D plan](first_sim_plan_2d_baseline.md) and figure roadmap remain the reference for physics,
observables and validation; this document supersedes their implementation order.

The current reduced Run 937 does not sustain detonation. Adding dimension is not
a demonstrated cure. Do not transfer fitted constant-gamma chemistry into the
new solver and call it physical methane chemistry. GRI-Mech/SDToolbox references,
source tests, conservation definitions and paper transcriptions are reusable;
native fluxes, thermodynamics, chemistry integration and boundaries need renewed
verification in the selected native backend.

## Revision 12: literature, runtime and sustained-wave objective

The [fresh literature/runtime review](docs/plans/3d_literature_runtime_review.md)
controls the next increments. Mundt Run 937 is experimental; its Chapter 4
thermochemical/empirical calculations are not a full-engine simulation. The target
is eventual sustained-detonation screening for modified designs. The first useful
output is a qualified idealized 3D diagnostic, followed by the stability, model and
experimental validation needed for design claims. Use one PeleC GPU implementation
with small same-source CPU controls and detonationFoam as a bounded fallback.

Routine complete cases target <=2 hours including queue/output after the cached
build. Forecast integration <=90 minutes using measured reacting throughput plus
30%; stop at 120 minutes, without blind retries. This is a feasibility gate, not a
measured runtime guarantee. Retain the short G4 preview cap; after its checks pass,
a separately specified <=2 ms screening case may proceed under the review's gates.
A rotating pressure pulse, seeded wave count or continuing ignition is not a
sustained-wave pass. Check replenishment, shock/reaction coupling, disjoint windows,
mesh/dt and startup/feed/outlet sensitivity, and a documented negative control.

The user authorized an early start; the 14:30 kickoff is paused to avoid duplicate
work. The review rounds and G0/G1a are complete. Continue the bounded native controls in the isolated 3D clone; no engine is yet validated.

## GPU revision: fastest useful result

The user now provides access to about eight Modal GPUs and prioritizes turnaround
above initial fidelity. This supersedes the earlier local-only/no-cloud restriction.
Modal authentication and an eight-core CPU access probe passed. One H100 80 GB and native CPU/GPU controls are verified. Simultaneous multi-GPU
capacity/topology and reacting-engine performance remain unverified. Tiny control
runtimes are measured; engine runtime estimates are not measured results.

**Decision:** one 3D project and physical specification, CPU checks plus a GPU
production candidate; no separate CPU/GPU branches or full duplicate implementations.
Keep all work on `3d-modelling` in this isolated clone. Retain detonationFoam as the
installed fallback and geometry reference. Evaluate **PeleC** first for production,
using the same PeleC source/mechanism on CPU and GPU for small equivalence tests.
The detailed comparison and speed/accuracy analysis are in
[the GPU decision record](docs/plans/3d_gpu_decision.md).

We already use CFD software (OpenFOAM/detonationFoam). The proposed change is to a
GPU-capable compressible reacting-flow backend, not a new custom solver. Current
PeleC upstream identifies MPI+CUDA/HIP/SYCL and AMR support. Its geometry uses
Cartesian embedded boundaries, so OpenFOAM mesh files cannot be reused directly.
Reuse analytic dimensions, measurements, chemistry references and test definitions;
rebuild and verify the native geometry. Do not transfer OpenFOAM verification status.

### Immediate execution order

| Increment | Work and short acceptance test | Time/resource decision |
|---|---|---|
| G0 | Inspect Modal hardware/permissions; pin PeleC, AMReX, PelePhysics, SUNDIALS, CUDA/compiler/MPI and mechanism; build a minimal upstream case; verify actual GPU execution. | Start with one H100-class GPU provisionally; use available compatible A100/H200 if that shortens turnaround. Build/cache image once. First engineering checkpoint after four active hours, stop open-ended porting. |
| G1a | Upstream tiny cold shock and zero-D reactor on CPU and one GPU, same source/inputs/FP64. Compare reference solutions, short-time fields, species and elemental/energy budgets. | Single GPU; tests target seconds to a few minutes once built. No eight-GPU request for tiny tests. |
| G1b | Full-annulus plus core-end EB geometry; analytic volume/areas, correct normals, closed cold equilibrium, directional shock. Instrument species/state repairs and their integrated mass/energy effects. | At most two angular/grid orientations/resolutions initially. T2 OpenFOAM pass does not count as this pass. |
| G1c | One fixed refinement interface before dynamic AMR: cold shock/contact crosses it; compare uniform fine reference, composite conservation and regridding corrections. Reactive crossing follows G2b, before any reactive AMR engine run. Then small restart and MPI/GPU decomposition equivalence checks. | Reuse upstream EB-C7/C8/C3 and project reference states. Avoid building a general test framework. |
| G2a | Thermo/units and closed-reactor checks for one methane/oxygen mechanism against Cantera, including compressed and hot-product/fresh mixtures. | Reduced candidates are screened against the detailed reference before use. FFCM1_Red changes ignition classification; keep full GRI for small numerical controls while mechanism suitability remains open. Do not fit rates to force survival. |
| G2b | Native 1D formed detonation: two initial grid levels and a timestep halving; speed, induction/heat-release distance and continued shock/reaction coupling. Add a third level only if needed to resolve uncertainty. | Select the cheapest numerical setup that preserves the intended diagnostic. A fast wrong propagation solution fails. |
| G3 | Short representative reacting workload on 1, 2, 4, then 8 GPUs when useful. Same cells, mechanism, precision, output and physical interval. Record startup, compute, chemistry, communication, I/O and peak memory. | Stop scaling when end-to-end time ceases improving. Choose one multi-GPU case or several independent checks from measured results. |
| G4a | Smooth full-annulus/core-expansion, ideal-gas mixture, premixed feed, inviscid adiabatic slip walls, controlled initial charge; first checkpoint at one reference passage (63.131 us). | Requires G1/G2 gates, measured resource feasibility and native boundary budgets. Exploratory only; no injector mixing, heat loss, turbulence or experimental mean claims. |
| G4b | Extend only a finite, budget-consistent case to three passages (189.394 us); at most five (315.657 us) with a recorded reason. Compare one spatial refinement and one dt/CFL reduction, preserving physical ignition inventory. | Coupling/mode stability must survive these changes before calling propagation provisionally credible. Short record cannot establish long-term sustained operation. |
| G5 | Add the uncertainty that matters most: outlet/feed/startup sensitivity first; separate injectors and transport after a one-pair check; later walls, turbulence and longer statistics. | Preserve T6/T7 requirements for Run 937 validation. No large sweep by default. |

G1 and G2 tests may overlap in preparation, but their passes are dependencies of
G4. G1c cold tests do not depend on G2; its reactive-interface extension does.
A uniform-grid exploratory case may defer dynamic-AMR tests, never its own
conservation/chemistry checks; record the resulting memory/runtime cost. G3 may
use a verified representative reacting box while annular setup is being
finished. The old T3/T4 implementations in detonationFoam are no longer duplicate
prerequisites when PeleC is selected. Their *physical checks* remain mandatory in
the selected backend. T0-T2 evidence stays valid only for the installed backend.

After the first engineering day of G0/G1, decide using evidence: continue PeleC
if basic GPU, chemistry and geometry combinations work without substantial new
solver development; otherwise return to detonationFoam on CPU and benchmark a
single larger CPU allocation. Do not spend several days writing CUDA kernels or
trying many solvers. These are decision checkpoints, not delivery-time promises.
MFC is the next researched candidate only if a specific PeleC limitation warrants
it. No automatic switch on a failed physics test: diagnose the failure first.

### Fidelity ladder and non-negotiable checks

1. Geometry/cold preview: coarse cells, short time, no chemistry claims.
2. Exploratory reacting case: premixed injection, adiabatic inviscid walls,
   thermally perfect ideal-gas mixture and tested reduced finite-rate chemistry;
   omit radiation, conjugate heat transfer, resolved jets and turbulence closures.
   Results describe that idealized model. Coarse failure/success alone cannot
   identify physical extinction/sustainment.
3. Numerical credibility: compare grid and timestep at fixed physical model;
   investigate source tolerance, clipping and boundary budgets separately.
4. Run 937 validation: explicit injection/mixing, wall/outlet/model sensitivity,
   experimental measurement operators and appropriate statistical windows.

Relax initial model detail and output volume, not final-time verification, acoustic
stability, thermo consistency, mass/element/energy accounting or heat-release/front
coupling. Retain FP64 initially; mixed precision requires a separate numerical
check and is not the first optimization. Never silently thicken chemistry or
increase dt past a stability/accuracy bound. Any surrogate is a separate declared
model and cannot establish physical methane detonation behavior.

PeleC EB documentation describes default species clipping/renormalization with
changes to density, momentum and energy. Measure repairs before reactive claims;
changing solver does not remove this gate. Its default robust state redistribution
can lower near-wall order. Start from the documented robust option, record it,
and check geometry/grid-orientation sensitivity. Do not enable higher-order EB
reconstruction merely for its label. Count fluid volume fractions, face apertures,
finest valid AMR cells and coarse/fine flux corrections in native budgets.

For the first coarse/fine exploratory comparison use project decision thresholds
of 5% for tracked mean front speed and 10% for window-mean wall pressure/total heat
release, with the same post-ignition window and a consistent front/mode definition.
These are triage thresholds, not experimental uncertainties or proof of convergence.
If the mode, front coupling, or survival outcome changes, classification is unresolved
regardless of scalar agreement. A noisy/too-short window is inconclusive. Keep the
physical CJ discrepancy open rather than accepting a match to one target by tuning.

### Modal execution and resource policy

Up to eight GPUs total initially. Use one job per container; launch one MPI rank
per GPU for multi-GPU jobs, explicitly verify rank/device mapping and communications.
First use a single machine; eight unrelated one-GPU containers are not automatically
an MPI cluster. Modal documents up to eight colocated GPUs for supported types,
with longer scheduling waits often above two. Do not require multi-node RDMA now.
CPU RAM/cores must be requested explicitly; GPU count does not specify host capacity.

Record real device names, driver/toolkit, topology, compiler flags, CPU allocation,
source/submodule hashes, mechanism and immutable input IDs. Request no concurrency
beyond eight devices across all jobs. Different checks use disjoint output paths
under a dedicated 3D run prefix. Upload a frozen source snapshot; never mount or
modify the parallel 2D checkout. Credentials remain outside repository/manifests.

Use local job scratch for active solver files, then persist completed diagnostics
and checkpoints to Modal storage. Confirm output durability before declaring a pass.
Give every pilot a finite timeout (initial benchmark attempts <=15 minutes after
build; longer runs only from a recorded throughput forecast). Timeouts/preemptions
are incomplete, not negative physics results. Retries must not restart an expensive
run blindly or overwrite evidence. Enable continuation only after same-backend
restart equivalence is tested; persist a completion manifest last.

Optimize time to a usable answer: scheduling + image startup + setup + integration
+ output + checking. Benchmark simulated microseconds per wall-second and total
turnaround, not just GPU utilization or AI throughput. Use leftover GPUs for the
next discriminating test, not speculative parameter sweeps. Compact probes and
budgets each step; sparse full fields. Preserve enough fields to diagnose coupling.

## Small increments and gates

| Step | Deliverable | Required evidence before advancing dependent work |
|---|---|---|
| T0 | Independent checkout, exact upstream baseline, revised plan | Branch is `3d-modelling`, baseline committed after 2026-10-22 01:15 PDT; five documented plan reviews. |
| T1 | Pinned OpenFOAM 8/detonationFoam environment | Build, executable loading, bounded upstream tutorial, return code and final time checked; installation is not physical validation. |
| T2 | Parametric full annulus and core-end expansion mesh | Analytical geometry, positive volumes, closure, correct boundaries; OpenFOAM `checkMesh`; no wedge/sector mode restriction. |
| T3 | Cold 3D flow and native accounting | Constant-state preservation, oriented shock test, mass/energy/force sign tests; finite states and finite run cap. |
| T4 | Methane/oxygen chemistry and 1D propagation | Mechanism/thermo conversion audit, closed reactor against Cantera, fixed-model grid/time sensitivity, shock/reaction coupling. |
| T5 | Controlled 3D premixed annulus run | Reproducible startup inventory/energy, feed/outlet limits, short fields/probes/native budgets, cold baseline and T4 gates passed. |
| T6 | Separate impinging injectors and transport | One injector-pair cold mixing test first; mesh/flux/species/enthalpy checks, then full-annulus mapping. |
| T7 | Run 937 physical comparison | Resolve startup/outlet/model sensitivity; compare pressures and angular wave measures; record disagreement without tuning to the answer. |

No CAD importer, plugin registry, scheduling system or new custom 3D flow solver.
Use a small Python add-on and thin backend-specific case files. Keep the existing
OpenFOAM preparation; add only the PeleC case/launcher needed by G0-G4. No universal
backend abstraction or cross-solver checkpoint conversion.
Retain the existing starter without changing its production numerics.

## Reference geometry and case

Use Mundt (2023), printed pp. 28-37 and 52 (PDF page = printed +16): outer radius
38.1 mm, inner radius 33.1 mm, annulus length 76.2 mm; outer core length 152 mm.
The inner core ends at 76.2 mm and downstream gas occupies a full cylinder.
Represent that expansion explicitly. A constant annulus is a verification case,
not the full experimental domain. The dump tank/0.25 m duct remain omitted and
outlet-location sensitivity is required. Include outer-wall pressure stations
85.7 and 98.4 mm downstream as diagnostics, not imposed exit pressures.

Run 937: phi 1.176, nominal total mass flow 0.26865 kg/s, reference mass flux
240.21 kg/(s m2), ambient pressure 100200 Pa. Separate oxygen/methane plenums:
1309500/1399400 Pa and 303/301 K. These are reference inputs; choose mass-driven
or plenum-driven boundary conditions, never both independently.

72 injector pairs; circular hole diameters 0.79/1.24 mm (fuel/oxygen), inclined
30 degrees to +z and meeting 2.16 mm above the face at radius 35.6 mm. Rounded
hole diameters and nominal total area ratio 0.110 need not give identical areas.
Record which area convention drives each model. Resolved holes are a later step;
a uniform premixed feed must explicitly declare its approximation.

The experimental pre-detonator is at z=73 mm, clocking 210 degrees. The paper does
not supply a complete inlet history. A controlled numerical ignition is allowed
as a documented assumption, with integrated initial mass and energy retained;
its energy is not a measured ignition energy. The 3.8 mm refill estimate is not
a measured startup charge. Do not change startup inventory silently on refinement.

## Shared physics and comparisons

Reuse existing D3 physical CJ/ZND data, contact and grid studies, and the audit.
Physical and surrogate references remain separate. The physical CJ result
2531.86 m/s differs from the paper's 2471 m/s by 2.46%; keep that discrepancy open.
No arbitrary kinetic thickening or grid-dependent rate changes. Verify mixed
hot-product/fresh states as well as neat fresh gas. Source splitting and thermo
reference conventions can change results even when a 1D speed appears correct.

Reuse the figure roadmap's measurement operators, pressure/reference arrays,
known-signal wave tests, and force/budget definitions. Native face/volume integrals
remain authoritative. Resampled slices are for display. Preserve native backend
fields (OpenFOAM or AMReX plotfiles/checkpoints); do not force them into the
starter's conserved-state arrays. Audit backend units, species ordering and
formation-energy conventions before comparing physical integrals.

Run 937 has two co-rotating waves at 15.84 kHz and 1893 m/s outer-periphery speed.
Compare omega=2*pi*f/N, D_outer=omega*r_outer; do not compare that speed directly
with an unrolled mean-radius speed. Do not fix N=2 in a simulation classifier.
An acoustic pressure pulse alone is not detonation. Require continued heat release
coupled to the front after ignition ends. Mundt supplies no measured thrust/torque.

## Test budgets and stop rule

Default unit tests require no container and finish in seconds once dependencies
are warm. Backend smoke tests are explicit and bounded. A future engine check
has a first checkpoint at one reference interval (63.131 microseconds), then
three intervals, 189.394 microseconds, at most five total
315.657 microseconds for a documented unresolved observation. These durations
budget observation time, not validation. Revision 12 separately permits a qualified
<=2 ms screening case after the preview, numerical and runtime gates pass. Tiny
cold/chemistry tests use much shorter durations. No large sweeps.

If a critical inconsistency appears, stop dependent advancement. Record symptom,
files/inputs, evidence, candidate causes, discriminating test and disposition:
(1) spatial resolution; (2) accumulated temporal/roundoff/source errors;
(3) physical or boundary assumption; (4) explicitly deferred capability.
A promised future feature cannot waive a correctness failure needed now.

## Installed detonationFoam audit and energy convention (review 2)

Pin detonationFoam commit `4bd2e86003447fdb143b475f199c846146f754e3`
from branch `detonationFoam_V2.0_OF8`. Its default build includes optional
2D dynamic mesh and DLB libraries. Build the upstream dependency graph as shipped
for the installation test; do not infer 3D AMR support from those library names.
Use static meshes first for this backend. PeleC AMR has the separate G1c gate.
The provided reactive tutorial uses NH3/H2/O2/AR,
not methane/oxygen, and tests installation only.

The source has a leading-shock x-position exit which returns success before
endTime, plus nonnegative species clipping. A return code of zero is insufficient.
Require the requested final time and complete final fields; explicitly set the
shock-position cutoff beyond the domain for non-tutorial runs. Before quantitative
reactive cases, instrument species corrections (minimum raw fraction and volume-
integrated correction, including inert-species closure); fail on material repair.
Conservation of elemental mass must be checked as well as total species sum.

Native energy is sensible internal energy plus kinetic energy, with chemistry
heat source. The starter stores unspent chemical energy in its conserved total.
Do not add the starter's q source to the native solver or compare raw energies.
Closed reactor comparisons use temperature/species and a consistently reconstructed
total including formation energy. Export the convention in every manifest.

## Geometry and reduced-limit tests (review 3)

Coordinates: right-handed Cartesian x,y,z; engine axis +z; positive azimuth is
atan2(y,x), counterclockwise looking downstream. Native velocity remains Cartesian.
For OpenFOAM, use a full 360-degree connected multiblock annulus (no cyclic
sector to impose wave count). PeleC instead needs the same physical volume via
embedded geometry, validated independently under G1b. Maintain identifiable
injector, innerWall, outerWall, coreEnd and outlet surfaces for diagnostics.
In OpenFOAM these are named patches, and the expansion uses a square/O-grid
downstream rather than collapsed zero-volume cells. Core-end wall area is pi*ri^2. Validate volume
pi*(ro^2-ri^2)*L + pi*ro^2*(Lout-L), annular inlet and circular outlet areas.
Cell faces approximate curved boundaries; compare integrated mesh measures with
analytical targets at two angular resolutions, and expect refinement of the error.

First cold geometry checks use deliberately coarse meshes. They do not resolve
the physical 0.03952 mm half-heat distance. A 3D visual preview is geometry evidence,
not a reactive result. The constant-annulus verification configuration omits the
expansion explicitly; reject expansion-only diagnostics when absent.

An extruded Cartesian strip with uniform third direction should reproduce the
same native planar solver's solution to roundoff/discretization tolerance. A curved
annulus is not exactly the starter's unrolled rectangle: curvature introduces real
differences. Do not require exact curved/unrolled equality or change physics to
force it. Reuse reference states and measurement functions, not cross-backend
checkpoints or mandatory equal conserved-array shapes.

## Local fallback cost, time stepping and test acceptance (review 4)

This host is Intel macOS with about 17 GiB free at the first check. Use a dedicated
Colima profile with two CPUs, 4 GiB RAM and a 12 GiB sparse disk initially, leaving
capacity for the parallel 2D session. Modal GPU use is now authorized as above.
Keep this local fallback small. Build and runtime
logs record versions, wall time, memory/disk evidence and exact commands.

The upstream `calculateDt.H` reports a flux-based convective Courant number;
the tutorial's `useAcousticCourant`/`maxAcousticCo` entries are not read by this
solver. Cold gas at rest is not protected by a convective-only CFL. First native
checks therefore use a conservative fixed time step, with a separately evaluated
acoustic bound using |U|+a and cell face/volume scales. Adaptive stepping requires
an audited acoustic implementation before use. Do not relax time/source accuracy
to make an under-resolved engine run cheaper.

Local fallback budgets (wall-time caps are failures/timeouts, not numerical
passes; Modal trial limits are specified in the GPU revision above):
unit/geometry tests <10 s warm; each cold backend check <120 s; upstream reduced
installation smoke <120 s; a local reactor <60 s; 1D propagation and the first
reactive engine benchmark have measured cost gates before extension. Set finite
physical end times and keep initial/final fields plus low-volume diagnostics.
A short upstream smoke deliberately reduces its grid and duration and disables
adaptive time stepping; identify all deviations and do not call it reproduction
of the published tutorial's detonation result.

Geometry acceptance: no negative/zero volumes, no disconnected or non-manifold
cells, three geometric/solution dimensions, required patches nonempty, expected
cell count and boundary areas, `checkMesh` success. Record nonorthogonality and
skewness; use <70 degrees and <4 respectively as project screening limits, not
paper-validated universal accuracy thresholds. Analytical area/volume error must
be <1% at the first selected angular grid and decrease on angular refinement.

Cold state acceptance (both backends): pressure/temperature/density finite and
positive; species finite and nonnegative, with unit sum. Constant
state relative deviations <1e-9 and speed <1e-8 m/s over the short static test.
Use failures to distinguish geometric balance errors from time accumulation;
these tolerances verify a simple equilibrium, not turbulent accuracy. Reactive
speed/profile tolerances follow independent reference and refinement uncertainty;
do not invent experimental error bands. Save failing evidence as well as passes.

A related 3D methane/oxygen study used a 12-species mechanism and 2.1-85.2 million
cells, and verified 1D numerics first (Strakey and Ferguson, AIAA 2022-1113).
Its phi=1.16/0.267 kg/s point is distinct from Run 937; reuse verification lessons,
not its boundary values or performance as a Run 937 target. Its longer statistical
windows do not justify silently extending the current short development cap.

## Final execution contract and remaining uncertainties (review 5)

Use `rde3d/` for case/geometry preparation, native-process handling and pure
reductions, `rde3d/tests/` for assertions, and `tools/openfoam/` for the pinned
container build. The existing `rde_sim_starter/` remains independently runnable.
No new runtime dependency is needed for preparing geometry or checking manifests.
Any new 3D rendering reads saved data and stays separate from physics.

For the CPU fallback, T3 is delivered as three small commits if needed:
static equilibrium; directional
shock/extrusion controls; native flux/storage checks. T4 is split into mechanism
conversion/zero-D checks and then 1D propagation/refinement. Geometry preparation
can be inspected while a build runs, but cannot claim backend validation until
T1 and `checkMesh` complete. Stop at the first critical dependent inconsistency.
Record an open issue rather than substituting a different solver without review.

Native completion requires exact pinned source/image IDs, immutable input hashes,
requested/actual end time, return code, all required fields and finite-state checks.
Existing output directories are refused. Timeouts preserve partial results and
are marked failed/incomplete. Restart is disabled until a same-backend restart
equivalence test passes; no starter/OpenFOAM checkpoint translation. Backend
capability validation rejects unsupported requested chemistry, feed or geometry
before launching. Record reference tolerances and numerical-correction budgets
before running each new test, not after inspecting its result. In particular, a
cold smoke cannot be silently used as the
reactive Run 937 model. Serial verification precedes decomposition/MPI tests.

Before every commit: run the tests appropriate to that increment, record commands,
runtime and findings in `docs/verification/3d_progress.md`; update this plan's
status with what is actually verified. Push only `3d-modelling`. Never modify the
other session's main checkout or its uncommitted investigation. Do not merge main
into this branch while a native run is active; freeze one explicit baseline SHA.
Later reuse of 2D changes is a reviewed merge/cherry-pick, not a live shared import.

Known unresolved physics carried forward: RDE-001; physical CJ discrepancy;
uncertain ignition history; equivalent premixed versus impinging feeds; turbulence,
wall heat loss and near-wall resolution; downstream facility/outlet sensitivity.
A preliminary smooth inviscid mesh/flow case only verifies its stated idealization.
For T7, include outer-wall and front-wall pressure measurements with instrument
clocking from Table 2-2. Keep the paper's 100 ms averaging window distinct from
our microsecond development record; direct quantitative mean agreement remains
unestablished until convergence/window and model checks justify it.

References: [Mundt thesis](Mundt2023.pdf), [model audit](docs/verification/mundt_model_audit.md),
[D3 investigation](docs/verification/d3_investigation.md),
[figure roadmap](docs/plans/figure_validation_roadmap.md),
[detonationFoam source](https://github.com/JieSun-pku/detonationFoam/tree/4bd2e86003447fdb143b475f199c846146f754e3),
[OpenFOAM 8 macOS setup](https://openfoam.org/download/8-macos/),
[Strakey and Ferguson](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf).

## Baseline and current status

Revision 15 incorporates native-control, cold geometry and methane preflight evidence. G0 and G1a shock/closed-reactor
controls passed on CPU and one H100; native geometry/refinement G1b/c and methane
G2 remain open. The generated-rate reference distinction and order-5 chemistry
configuration are recorded in [G1a evidence](docs/verification/pelec_g1/README.md). Reacting throughput,
multi-GPU capacity/scaling and G2-G5 physics remain unverified. Do not complete a
duplicate full detonationFoam pipeline. See [G0 evidence](docs/verification/pelec_g0/result.json).

T0 complete. Separate clone based on `0f435aad6b23e063a35f1017a985d5ee8ee8145d`,
committed 2026-10-22 01:35:05 PDT. T1 installation and T2 parametric mesh checks passed; no 3D reactive model has been validated. The new C1-C6 controlled 2D
plan was re-read after branching; its source/formed-profile/layer controls can
provide additional evidence later, without changing this frozen checkout.


## Revision 13 execution refinements

Use independently integrated references matching the pinned generated rates for
numerical error, and keep nominal-mechanism representation differences separately
visible. Never fit constants to native trajectories or experimental wave speeds.
G1a exposed and guarded against no-op chemistry and ignored CPU CVODE failures.
Native order-5 chemistry passes the small strict controls; the default order-2
cap was inefficient for their long zero-D intervals. This is a supported native
option, not a new CFD solver or an overall fifth-order hydrodynamic claim.

Before choosing a methane mechanism, directly test native u(T,Y), cv(T,Y), and
T(u,Y) against Cantera at fresh and product states, including the approximately
3994 K existing Run 937 reference. A compiled audit finds DRM19 and native GRI
forward thermodynamics agree with Cantera, but their inverse switches to linear
extrapolation above 3000 K. Do not pass a mechanism on low-temperature checks only,
raise the inversion bound silently, or confuse polynomial extrapolation with
validated high-temperature thermochemistry. A second existing candidate may be
screened to resolve this incompatibility; no broad mechanism search or invented
reduction is required. Its kinetics, provenance and high-pressure scope must
pass before any native methane propagation or engine case.


## Revision 14 — methane law consistency before an engine choice

The [G2 preflight](docs/verification/pelec_g2/README.md) rejects selecting FFCM1_Red
from CJ agreement alone: independent refined ignition screens change event
classification. This does not establish GRI as experimental truth. Full GRI is
the paper-comparison baseline for small controls; measure its native cost before
considering a reduced production mechanism. No CPU/GPU branch split is needed.

The pinned GRI inverse uses a 3000 K bound while forward thermo and the paper-model
reference extrapolate polynomials to hotter states. An explicit two-line build
overlay extends only the inverse numerical interval to 5000 K. Compiled energy
and enthalpy tests pass, but published thermo fit limits remain unchanged. Keep
`numerical_consistency_passed` separate from the still-failing full physical
preflight. The overlay is permitted only for numerical controls of the declared
law. It cannot authorize engine/design conclusions through the physical gate.

Before G2b/engine interpretation, document a defensible high-temperature thermo
choice/sensitivity and mechanism applicability at the relevant pressure, mixture
and temperature. If changing those assumptions changes propagation or extinction,
report model uncertainty rather than one design verdict. GRI/paper consistency,
independent integration and experimental validity are distinct checks.

The 0.5-us homogeneous postshock methane numerical control now passes:
independent reference refinement, native CPU/GPU agreement, whole-history and
peak-species checks, and separate timestep/tolerance sensitivity. Same native
PeleC/CVODE physics and the existing analyzer are reused. G1b/c geometry and cold
refinement controls remain independent work; neither is waived. Native runtime
for a small reactor is not a 3D engine throughput estimate.


## Revision 15 — geometry evidence and the hydro-path distinction

The [G1b geometric/static subset](docs/verification/pelec_g1b/README.md) passes on
1/0.5-mm native EB grids, with actual native surface areas/normals/port apertures
and closure checked. The core-edge maximum slice error is nonmonotonic but below
1%; integrated error, volume and all boundary areas improve. Keep this local
observation visible in later moving-wave refinement. Stored native normals use
an inward convention; use the verified flux-sign conversion in diagnostics.

Original G1a shock controls used Godunov hydro. Seven new regular-grid MOL controls
now pass exact-reference, three-grid, timestep, x/y/z rotation and CPU/GPU checks
for the method used with EB. Do not transfer this pass to dynamic cut-cell fluxes.
G1b local correction accounting and G1c AMR remain open. Default zero SRD slopes
are robust but can add near-wall diffusion; moving-shock/refinement checks must
assess that before interpreting an engine's extinction as physical.


## Revision 16 — bounded propagation under an explicit model limitation

Refined independent thermo substitution retains GRI forward kinetics and changes
CJ speed by 0.044% and reaction length by 3.27%; numerical refinement is <4e-6.
This supports a conditional formed-wave numerical check, not a physical-fit
pass or uncertainty bound. Keep the existing full-GRI native baseline, declare
the extrapolated polynomial law and 5000 K inverse interval, and block any
engine/design conclusion pending the remaining dynamic, model and boundary
gates. See the [G2 evidence](docs/verification/pelec_g2/README.md) for limitations.

## Revision 17 — native transport diagnosis and engineering checkpoint

Native GPU chemistry, static EB geometry and regular-grid MOL controls work
without developing new CFD physics; retain PeleC as the GPU-first candidate and
the installed detonationFoam fallback. Do not create separate engine branches.
The [formed-wave evidence](docs/verification/pelec_g2b/README.md) isolates a
higher-order composition/positivity defect for the steep methane profile. The
first-order saved fields appeared to pass, but revision 18 withdraws a full
probe pass after the every-step audit. Wave-speed/grid accuracy is not accepted. G2b, dynamic EB, AMR and engine gates remain open.

The four-active-hour engineering checkpoint does not justify a full engine launch:
full-GRI small-case step cost already warns against treating it as an established
two-hour production recipe. Retain it as a reference. Measure the bounded wave
extension before choosing tolerances or chemistry reductions; preserve the same
physical diagnostic and check sensitivity. A CPU solver switch or requesting
eight GPUs does not by itself resolve reaction-length/CFL and model-cost limits.
No tuning of heat release or continuing ignition may manufacture sustainment.

## Revision 18 — failed propagation is a stop gate, not a design result

P3D-001 remains open: at 0.2 us, first-order MOL produces 15–18% excessive speed
and collapses the reaction distance. Halved dt leaves the result almost unchanged;
the 4 um grid does not converge to the reference. Every-step checks additionally
catch transient negatives missed by snapshots, and the finer case exceeds the
conservative buffer estimate. See the [complete evidence](docs/verification/pelec_g2b/README.md).
No engine progression or sustained-wave claim is permitted.

Next: increase the planar-control buffer at fixed physical spacing, then one
bounded native higher-order transport comparison. Godunov on a regular grid is
only a diagnostic; its pass cannot be transferred to MOL/embedded walls. Avoid
custom flux development. Use the installed CPU fallback for an equivalent bounded
control if native GPU support requires substantial repair. Keep full GRI as a
verification reference, not a promised <=2-hour production configuration.
Measured 0.2-us control costs are 332/457/540 seconds, excluding queue/build; no
64-core or eight-GPU engine timing is inferred from these. Preserve the physical
model and accuracy gates when optimizing tolerances or screening reduced chemistry.
