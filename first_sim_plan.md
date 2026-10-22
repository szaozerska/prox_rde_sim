# 3D RDE development plan - revision 10, five reviews complete

This branch develops a native three-dimensional methane/oxygen pipeline. The
2D starter remains a small independent verification and investigation backend.
A successful 2D engine run is no longer a dependency for starting 3D work.
The [inherited 2D plan](first_sim_plan_2d_baseline.md) and figure roadmap remain the reference for physics,
observables and validation; this document supersedes their implementation order.

The current reduced Run 937 does not sustain detonation. Adding dimension is not
a demonstrated cure. Do not transfer fitted constant-gamma chemistry into the
new solver and call it physical methane chemistry. GRI-Mech/SDToolbox references,
source tests, conservation definitions and paper transcriptions are reusable;
native fluxes, thermodynamics, chemistry integration and boundaries need renewed
verification in detonationFoam.

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
Use one small Python add-on to prepare native OpenFOAM cases and read results.
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
remain authoritative. Resampled slices are for display. Preserve native OpenFOAM
fields rather than stuffing 3D meshes into the starter's conserved-state arrays.

Run 937 has two co-rotating waves at 15.84 kHz and 1893 m/s outer-periphery speed.
Compare omega=2*pi*f/N, D_outer=omega*r_outer; do not compare that speed directly
with an unrolled mean-radius speed. Do not fix N=2 in a simulation classifier.
An acoustic pressure pulse alone is not detonation. Require continued heat release
coupled to the front after ignition ends. Mundt supplies no measured thrust/torque.

## Test budgets and stop rule

Default unit tests require no container and finish in seconds once dependencies
are warm. Backend smoke tests are explicit and bounded. A future engine check
starts with three reference intervals, 189.394 microseconds, at most five total
315.657 microseconds for a documented unresolved observation. Frequency budgets
time only. Tiny cold/chemistry tests use much shorter durations. No large sweeps.

If a critical inconsistency appears, stop dependent advancement. Record symptom,
files/inputs, evidence, candidate causes, discriminating test and disposition:
(1) spatial resolution; (2) accumulated temporal/roundoff/source errors;
(3) physical or boundary assumption; (4) explicitly deferred capability.
A promised future feature cannot waive a correctness failure needed now.

## Native solver audit and energy convention (review 2)

Pin detonationFoam commit `4bd2e86003447fdb143b475f199c846146f754e3`
from branch `detonationFoam_V2.0_OF8`. Its default build includes optional
2D dynamic mesh and DLB libraries. Build the upstream dependency graph as shipped
for the installation test; do not infer 3D AMR support from those library names.
Use static meshes first. The provided reactive tutorial uses NH3/H2/O2/AR,
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
Use a full 360-degree connected multiblock annulus (no cyclic sector to impose
wave count). Include named injector, innerWall, outerWall, coreEnd and outlet
patches. For the expansion, fill the axis with a square/O-grid downstream rather
than collapsed zero-volume cells. Core-end wall area is pi*ri^2. Validate volume
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

## Cost, time stepping and test acceptance (review 4)

This host is Intel macOS with about 17 GiB free at the first check. Use a dedicated
Colima profile with two CPUs, 4 GiB RAM and a 12 GiB sparse disk initially, leaving
capacity for the parallel 2D session. No GPU/cloud spending. Build and runtime
logs record versions, wall time, memory/disk evidence and exact commands.

The upstream `calculateDt.H` reports a flux-based convective Courant number;
the tutorial's `useAcousticCourant`/`maxAcousticCo` entries are not read by this
solver. Cold gas at rest is not protected by a convective-only CFL. First native
checks therefore use a conservative fixed time step, with a separately evaluated
acoustic bound using |U|+a and cell face/volume scales. Adaptive stepping requires
an audited acoustic implementation before use. Do not relax time/source accuracy
to make an under-resolved engine run cheaper.

Proposed budgets (wall-time caps are failures/timeouts, not numerical passes):
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

Cold state acceptance: pressure/temperature/species finite and positive, constant
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

T3 is delivered as three small commits if needed: static equilibrium; directional
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
before launching. In particular, a cold smoke cannot be silently used as the
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

T0 complete. Separate clone based on `0f435aad6b23e063a35f1017a985d5ee8ee8145d`,
committed 2026-10-22 01:35:05 PDT. T1 installation and T2 mesh preparation are in
progress; no 3D reactive model has been validated. The new C1-C6 controlled 2D
plan was re-read after branching; its source/formed-profile/layer controls can
provide additional evidence later, without changing this frozen checkout.
