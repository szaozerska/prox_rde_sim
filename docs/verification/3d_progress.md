# 3D implementation record

October 22, 2026 (PDT). Work belongs only on `3d-modelling` in a separate clone.
Original checkout: `/Users/sgfx/Desktop/Projects/prox_rde_sim`.
Planned 3D checkout: `/Users/sgfx/Desktop/Projects/prox_rde_sim_3d`.

## Preparation before the branch point

- Read current revision 8, original review, figure roadmap, D3/model audits and
  the new layer-diagnostic review. Original working tree was left untouched.
- Rechecked Mundt printed pp. 28, 29-30, 34, 37, 52 and Fig. 2.4. Inspected the
  cutaway image as well as extracted text. Table 3-2 averages the last 100 ms;
  a 0.19 ms development record does not reproduce that averaging interval.
- Read upstream detonationFoam pinned source and the official OpenFOAM 8 macOS
  installation guidance; selected an isolated Linux runtime on Intel macOS.
- Completed five sequential planning reviews in `docs/plans/3d_plan_reviews.md`.
  No original production code was changed during these reviews.
- At 01:25 PDT the prerequisite investigation commit had not appeared. All new
  text was staged under `/private/tmp/prox_rde_3d_stage`; no branch was created
  from the earlier 23:35 baseline. User subsequently confirmed the commit is coming.

## Installation findings

- No Docker, Colima, OpenFOAM or detonationFoam executable was initially present.
- Host: macOS 15.7.9, x86_64; initial free disk about 17 GiB. Homebrew supports
  fewer current Intel bottles, so the dependency installation builds Go/Lima from
  source. This is installation cost, not solver runtime.
- Downloaded upstream source at `4bd2e86003447fdb143b475f199c846146f754e3`.
- Source audit: the x-coordinate leading-shock cutoff can return EXIT_SUCCESS
  early; species are clipped nonnegative; energy uses sensible internal energy;
  adaptive stepping uses convective phi and ignores the tutorial acoustic flags.
  These are accounted for explicitly in the revised plan. No causal claim about
  RDE-001 follows from them.

## Stop conditions and evidence

Every later entry records input/source hashes, test commands, observed results,
root-cause status (demonstrated versus hypothesis), resolution/time-step/model
checks, and the next permitted step. Failed tests remain failures until fixed and
rerun. No tested cold mesh or installation example counts as a sustained engine
wave. Do not advance a dependent stage through an unresolved critical failure.

Further source inspection: `runTime++` follows the dt update in `detoCellular.H`,
so there is no demonstrated mismatch between the advanced clock and updated dt.
`calculateDt.H` only reports a convective Courant number. The audit distinguishes
these two files rather than inferring a time-order bug from their names. The
shipped tutorial also requests `libODE_DLB.so`, which is absent from the source
build; the installation smoke must diagnose this explicitly if loading fails.

## T0 - branch isolation and final baseline review

- Commit `0f435aad6b23e063a35f1017a985d5ee8ee8145d` appeared at 01:35:05 PDT.
- Created independent clone with `git clone --no-hardlinks --no-checkout`, then
  `switch -c 3d-modelling <exact SHA>`. Verified cwd, clean branch, SHA and origin.
- Set origin to GitHub and its push refspec only to `3d-modelling`. No writes to
  the original checkout and no shared mutable source imports.
- Re-read the newly published C1-C6 plan and handoff. Preserve it as a baseline
  reference, clearly labelled as the other session's work; do not claim C1-C6 done.
- Archived the inherited master plan at `first_sim_plan_2d_baseline.md`; revision
  10 now directs this branch. Five review rounds and all unresolved physics remain.

## Frozen inherited baseline verification

Command: `RDE_RUN_REACTIVE_BASELINE=1 NUMBA_NUM_THREADS=2 python -m unittest
discover -s tests -v`, in this clone's `rde_sim_starter`, using the existing Python
3.12 interpreter and dependencies read-only. **59 tests passed, none skipped,
125.849 s.** Log: `docs/verification/3d_inherited_tests.log`. This includes the
95 microsecond 1D reactive baseline; it does not resolve RDE-001.

The isolated geometry checks passed four tests in 0.033 s after transfer. Native
completion/ASCII-reader failure checks add two tests (all six passed in staging).
OpenFOAM mesh checks and the tutorial are still pending; no new physical pass
is inferred from these unit tests.

## T1 first smoke failure and cause

`runs3d/install_smoke` stopped at setFields: upstream 0/ files contain 20,000
entries, incompatible with the explicitly coarsened 400-cell installation mesh.
This is a setup error, not accumulated flow error or a chemistry conclusion.
Full checkMesh additionally found zero transverse determinants: the single-row
tutorial leaves y active while declaring only z empty. No timestep was taken.

Fix: create uniform fresh fields from the upstream profile's far-upstream mixture,
zero velocity, then the supplied setFields pressure/temperature hot patch; declare
both transverse directions empty. All deviations are in the smoke manifest.
Require the actual `Mesh OK.` marker, since checkMesh can return zero with failed
checks. Preserve the failed destination; rerun in `install_smoke_v2`. This is
installation verification only, not conservative remapping or physical validation.

## T1 - installed and verified

OpenFOAM `8-1c9b5879390b` and pinned detonationFoam built successfully, including
upstream dynamicMesh2D, dynamicFvMesh2D, DLB and flux libraries. Executable help
and dynamic linking passed. Rebuild instructions and image identity are in
`tools/openfoam/`. Compiler warnings are retained in `3d_install/build.log`.

The corrected 400-cell tutorial-based smoke passed full mesh checks and twenty
fixed 0.1 ns steps, reaching exactly 2 ns with normal End and complete final
fields. Native solver reported 5.16 CPU seconds / 5 wall seconds. All 33 species
were finite and nonnegative; max species-sum error 1.14e-12. Pressure 101325 to
9117830.54 Pa, temperature 300 to 1999.689 K. The conservative acoustic estimate
from initial/final extrema is 0.002203 (project smoke limit 0.01). This is a very
short installation check, not time/space-converged reactive physics. Upstream
clipping remains unquantified and blocks quantitative chemistry claims.

Two native reader/completion tests passed (0.009 s): early exits, missing fields,
wrong field counts, truncated/nonfinite data and nonpositive states are rejected.
Full logs, initial-input hashes and failure evidence are in `3d_install/`.
T1 permits native geometry and cold controls; T4 chemistry validation remains open.

## T2 - full 3D mesh and expansion verified

Implemented `rde3d.geometry`, `prepare` and `mesh_metrics` as a small add-on.
Geometry reads the inherited case's radii/length; the documented 152 mm outer
core adds the downstream full-cylinder volume. Named core-end wall is retained.
Full 360-degree connectivity, no cyclic sector or collapsed-axis cells. This
idealized geometry omits injector passages, ports and the facility duct/tank.

Three native cases passed `blockMesh` and `checkMesh -allTopology -allGeometry`:

| Case | Cells | Volume error versus exact geometry | Max nonorthogonality | Max skewness |
|---|---:|---:|---:|---:|
| Expansion, 64 azimuthal cells | 30,720 | 0.16056% | 32.962 degrees | 0.4534 |
| Expansion, 128 azimuthal cells | 73,728 | 0.04015% | 36.160 degrees | 0.6366 |
| Constant-annulus control, 64 | 6,144 | 0.16056% | 0.000002 degrees | 0.1181 |

Native boundary areas agree within 0.161% on the coarse mesh and 0.041% on the
finer mesh. Vector boundary closure is below 1.8e-15 relative. Angular refinement
reduces circular-face volume/area error by about fourfold; the residual is chordal
tessellation, not a wrong nominal radius. Full logs/manifests/input hashes are in
`docs/verification/3d_meshes`. No flow or reaction-resolution claim is made.

A report-reader error initially consumed punctuation after OpenFOAM's printed
volume. Root cause: an overly permissive numeric regex, not mesh generation.
Fixed it and reanalyzed the saved mesh; no CFD rerun was needed. Added a known
unit-cube area/closure test, the exact punctuation case, and a failed-checkMesh
log case. All seven 3D unit tests pass in 0.041 s.

Commands: `python -m rde3d.prepare --out runs3d/<new-name> [--ntheta 128 |
--outlet-z .0762]`, then `python -m rde3d.mesh_metrics runs3d/<new-name>`.
Use `--saved` to reanalyze existing mesh/logs without rerunning. T2 permits the
cold equilibrium test. Reactive mesh requirements remain entirely unverified.


## Revision 11 — Modal GPU planning, not a solver result

User authorized roughly eight Modal GPUs and prioritized turnaround over initial
fidelity. Researched current primary PeleC, MFC, Fluent and Modal documentation;
read-only public PeleC HEAD query returned 949e2bb67386bf4b16324b06555e303ff411e179.
That is a candidate research snapshot, not an installed build. No Modal access,
GPU type/topology, benchmark, new chemistry result or engine run is verified.

Revised the primary plan and entry points; added `docs/plans/3d_gpu_decision.md`.
One 3D project now evaluates PeleC for GPU production with same-backend CPU
controls, retaining installed detonationFoam as fallback. No duplicate CPU/GPU
engine branches or custom GPU solver. A four-active-hour checkpoint and first-day
capability decision limit migration effort; neither promises a delivery date.

Three additional self-reviews (rounds 6-8) recorded issues and fixes: GPU support
versus actual reacting capability, cut-cell species/energy repair, nontransferable
mesh passes, AMR/chemistry dependency ordering, unresolvable coarse reaction scales,
queue/scaling/memory overhead and restart/output durability. Initial assumptions
explicitly defer jets, wall loss and turbulence; conservation, source/thermo checks,
front coupling and grid/time diagnostics stay mandatory. An unresolved numerical
failure cannot be labelled physical extinction or excused by a future feature.

Analytic volume 4.3089845447e-4 m3 yields 3.45/27.58/220.62 million fluid-volume
equivalent cells at uniform 0.5/0.25/0.125 mm. These are planning calculations, not
new meshes or approved reactive resolutions. No extrapolated wall time is claimed.
Seven existing 3D tests passed in 0.101 s; local links, arithmetic and whitespace
checked for the changed docs. Original 2D checkout remains untouched. G0 is next.


## G0 preparation — Modal client connected

Plugin catalog search returned no Modal integration. Installed the official
Modal CLI 1.6.2 into this clone's ignored `.tooling/modal-venv`, without modifying
the original 2D environment. First installation failed because cbor2 6.1.5
required Rust on Intel macOS. Retried with compatible prebuilt packages; cbor2
5.9.0 installed, CLI version and `pip check` passed. Client dependencies and
reproduction instructions are in `tools/modal/`.

Browser authentication completed; the CLI verified its token successfully and
read workspace settings and billing rates. Credentials remain outside Git and
were not read or copied into this record. Workspace settings did not expose GPU
quotas. No GPU allocation, solver build or performance measurement has run yet;
prices are not proof of capacity. G0 hardware verification remains pending.


## G0 hardware access — CPU-only Modal execution verified

On October 22 at 19:37 UTC, an explicit temporary Modal function successfully
executed a checksum test with a request/limit of 8 CPU cores, 1 GiB RAM, no GPU,
30-second function timeout and no retries. The app stopped normally. The returned
checksum matched 332833500. Remote x86_64 runtime exposed eight logical CPUs and
no NVIDIA device nodes; CPU model and cgroup limits were unavailable. Record in
`modal_cpu_access.json`; reproducible opt-in probe in `tools/modal/check_cpu.py`.
This verifies allocation/execution access, not maximum quota, MPI scaling or CFD
performance. No engine data or repository automount was uploaded.

Live billing-rate query returned CPU $0.04730/core-hour and RAM $0.008/GiB-hour:
requested 8-core/1-GiB baseline is $0.3864/hour, not a measured invoice. Only this
short access probe ran. GPU allocation and PeleC/detonationFoam remote execution
remain pending. JSON/checksum assertions and git diff whitespace checks passed.


## Revision 12 — fresh literature review and early implementation authorization

Re-extracted the complete Mundt thesis and read Chapter 3/4 methods/results;
rendered and inspected printed pp. 44-103, covering their figures. Compared ten
primary papers/reports plus official solver/Modal sources. Run 937 is experimental;
Chapter 4 mixes thermo references with empirical formulas. Published full-engine
3D studies are expensive; no inspected source proves this case fits two hours.
The detailed source/evidence table and revised gates are in
`../plans/3d_literature_runtime_review.md`.

Planning issues/fixes are documented in self-review rounds 9-11: source provenance,
GPU-speedup transfer, timing-margin arithmetic, sustained-wave false positives,
negative controls, conditional longer observation and stale document/schedule
state. Initial PDF rendering stalled due to an unwritable fontconfig cache; stopped
only this task's render processes and used a temporary writable cache. All 60
pages then rendered. No copyrighted PDF copies or temporary images added to Git.

User authorized early implementation, superseding the 14:30 wait. Paused only this
chat's kickoff automation to prevent a duplicate start; other chat's automation is
untouched. Work remains in isolated 3d-modelling. G0 starts with a pinned native GPU
trial, CPU controls, and detonationFoam fallback. Sustained-wave design screening
is the objective; short diagnostic outputs are intermediate, not a completed
physical validation. Local documentation links, arithmetic and diff whitespace
checks passed. No CFD job ran during the literature review.


## G0 hardware access — one H100 allocated successfully

Bounded 30-second GPU probe passed at 20:20:17 UTC. Modal allocated one NVIDIA
H100 80GB HBM3 (81559 MiB reported), driver 610.57.04, compute capability 9.0.
CUDA driver initialization and device enumeration passed. Temporary app
`ap-sDAMXUchI80hG4L26p2OBR` completed/stopped. This is not kernel/CFD throughput,
multi-GPU scaling or eight-device capacity evidence. No engine data uploaded.
Probe source and JSON are reproducible; importing the script launches no job.

Fetched/pinned PeleC 949e2bb67386bf4b16324b06555e303ff411e179 and its recursive
submodules in ignored .tooling/PeleC. Source inspection found no true 1D build: use
transversely uniform thin 2D/3D domains for physical 1D controls, verify transverse
uniformity, and retain the native dimensional kernels. No custom flux code needed.


## G0 — native PeleC CUDA smoke passed

Pinned PeleC/submodule lock is `tools/pelec/source_lock.json`; CUDA 12.8.1 image is
pinned by amd64 digest. CPU build used GCC 13.3.0, nvcc 12.8.93, CMake 3.28.3,
3D/FP64, CUDA architecture 90, no MPI/OMP/particles. Build took 350.92 s on the
requested 16 CPU cores / 64 GiB; cached Modal image `im-V2C5LChGVbI5m0zzVwbH7u`.
The upstream Sod executable initialized CUDA on one H100, reached t=0.002, and
exited cleanly in 1.031 s including startup/output. This tiny nonreacting case
is not a reacting-engine performance proxy.

Independent native-field checks passed: all requested fields finite, positive
density/pressure/temperature, correct final time and mesh, zero measured mass and
energy drift, zero transverse motion/nonuniformity, and the expected wall-pressure
impulse. The nondimensional Sod pressure scale maps to extremely small Kelvin
values with the GammaLaw gas constant; it is a mathematical gas-dynamics control,
not physical methane thermodynamics. Native binary/inputs/field artifacts are in
ignored runs3d/pelec_smoke_02; compact evidence is in pelec_g0/.

Issues and fixes:
- Modal build callback was imported by module name even with automatic source
  upload disabled. The first attempt failed before compiling. Explicitly upload
  only `build_native.py`; preserve no shared/private workspace mount.
- Upstream `--describe` crashed before AMReX initialization. Source main.cpp calls
  writeBuildInfo before Initialize; that path calls AMReX Print. This points to an
  initialization-order defect; no debugger-confirmed exact fault site is claimed.
  Normal initialized execution and plot job_info work. Preserve the failure code;
  use build manifest/job_info instead, with no numerical-source patch.
- Strict unused-input validation caught inactive AMR ref_ratio/regrid_int from the
  upstream input after max_level=0. Removed those settings; kept strict checking.
- First analysis report hit a NumPy boolean serialization error, corrected by
  converting check values to Python booleans. Reanalysis passed.
- Initial Matplotlib cache generation was slow; use the isolated writable cache
  for subsequent analysis rather than recreating a temporary cache each run.

G1 reference preparation caught a nonzero closed-reactor energy residual at the
upstream LiDryer initial 1000 K (6.41e-8 normalized). Tightening relative ODE
tolerance from 1e-10 to 1e-12 did not remove it; starting at 999 K retained it,
while starting at 1001 K reduced it to ~1e-10 or below. Independent thermodynamic
evaluation across the 1000 K polynomial join gives 6.43e-8, identifying the fit
discontinuity as the dominant cause. Preserve the failed reference and investigation.
Use a declared 1001 K control for strict energy validation, without altering the
mechanism or loosening the 1e-8 energy threshold. That reference passes energy,
element/density and tolerance-refinement checks. This is hydrogen test chemistry;
methane requires its own native/reference checks and thermo-join audit.

Three artifact-integrity tests passed: reject checksum corruption/path escape,
preserve failed status, refuse overwriting evidence. G1 CPU/GPU/refinement/zeroD
controls start only after the G0 field checks pass. No 3D engine flow has run.

G0 fast-suite environment correction: invoking the full 3D suite with the isolated
Modal client failed importing PyYAML (that environment intentionally contains only
client dependencies). Re-ran with the existing read-only project Python environment;
all ten tests passed. No packages or files in the 2D checkout were changed.


## G1 — shock passed; chemistry held at an independently detected inconsistency

Three native shock grids, separate timestep halving and CPU/GPU comparison passed
with decreasing exact-solution errors, finite states and conservation. Detailed
criteria, timings and visually checked plot are in [G1 evidence](pelec_g1/README.md).

The chemistry checks rejected a no-op default reactor, then found ignition-history
errors despite passing conservation and CPU/GPU agreement. Absolute-tolerance
refinement improves the history but does not yet meet its criterion. A compiled
operator probe separates generated-rate constant conventions from integration
error; preserve both nominal YAML and source-derived diagnostic references.
A very tight test exposed ignored CPU CVODE return status and partial chemistry
advancement with a continuing flow clock. New fail-closed log checks and regression
tests reject that signature. No methane/engine work proceeds. An A/B diagnostic of
the upstream tighter EOS inversion mode is running; root cause is not yet claimed.

All thirteen fast 3D tests pass after adding the observed solver-error regression.
No changes were made to the parallel 2D checkout. GPU-first remains one bounded
native implementation with CPU controls and the installed detonationFoam fallback;
these failures do not establish a GPU hardware limitation.


## G1a resolution — numerical controls pass with supported native options

The strict EOS inversion A/B did not resolve the failure and is not adopted.
The order-2 cap plus tight tolerance/long zero-D intervals caused excessive CVODE
substeps; allowing order 5 completed CPU/GPU controls quickly. Tightening tolerances
reduces all-step ignition error by about 84x at the 5-us step. Full peak species,
energy/element budgets and separate timestep checks pass. Final strict CPU/GPU
controls and the independently matched generated-rate reference are recorded in
[G1a evidence](pelec_g1/README.md). Nominal YAML differs by 10.6 ns in ignition
time; that model difference is retained, not relabelled as numerical success.

The source/probe review for G2 identified a distinct hot-state issue: native
DRM19/GRI temperature inversion extrapolates above 3000 K, below Run 937 reference
product temperature. Methane case construction waits on that preflight. Native
annulus/AMR, propagation, sustained-wave and runtime gates remain open.


## G2 preflight — mechanism and inverse-thermo issues separated

[Evidence and decisions](pelec_g2/README.md): original GRI/DRM hot-state inverse
round trips fail; an explicit diagnostic GRI bound correction passes numerical
energy/enthalpy checks, without extending physical fit validity. FFCM1_Red has
similar CJ speed but materially different ignition/length behavior; it is not
selected as the sustained-wave default. The independent closed-reactor reference
passes to 0.5 us and stays below the declared 5000 K polynomial interval. Native
control construction uses a small upstream zeroD initializer overlay, not custom
flux/chemistry integration. Physical methane/engine gates remain open.

Reproducible CJ/ZND/ignition driver added, preserving the starter's default GRI
reference. A mutable Cantera phase reused between ZND refinements was caught by
the peak-validity check; resetting to the stored VN state fixes it. Failed output
is retained. Sixteen 3D unit tests pass in 0.273 s, including three observed thermo
regressions. Compiled GRI source rates also match the explicitly source-derived
Cantera representation to 3.8e-14 normalized; nominal YAML differences are retained.


G2 numerical-control completion: the declared GRI polynomial-law closed reactor
passes CPU/H100, timestep and tolerance checks. H100 18.22 s, serial CPU 155.16 s,
half-step H100 21.74 s; no engine throughput claim. Native/source-derived reference
errors are <3.4e-9 across these controls, with full field budgets and species checks.
Nominal-YAML identity still fails its strict threshold for documented generation
constants; it is not silently relabelled as a pass. Shared saved field times were
added after the comparison rejected insufficient overlap in automatic subsamples.
The inherited hydrogen control reanalysis passes. Five reference tests pass from
the correct cwd; an earlier incorrect-cwd import failure is recorded.

G1b cold geometry work now uses the existing native implicit-function parser and
Sod/GammaLaw executable. No geometry CFD source rewrite is needed. This independent
control must still verify volume/connectivity/equilibrium and later surface
areas/normals, directional fluxes and corrections; it does not advance through
the unresolved methane physical-model gate.


## G1b geometric/static subset and native MOL regular-grid controls pass

[Evidence](pelec_g1b/README.md): native annulus volume errors decrease from
6.64e-5 to 8.36e-6; all actual boundary-area errors decrease. One connected fluid
region, correct signs/normals/ports and surface/volume closure pass. Cold mass,
energy and species budgets show zero measured drift. The local core-edge slice
maximum increases slightly (0.286% to 0.334%) while integrated error decreases;
both meet 1%, and the unresolved maximum-norm behavior is documented.

A source-aware review caught the Godunov-versus-MOL coverage gap. Seven native
MOL shocks now pass three-grid, timestep, x/y/z, CPU/GPU and conservation/impulse
checks. Plots were visually reviewed. These are geometric/static and regular-grid
passes; moving cut-cell shocks, local repair budgets, AMR and engine results are
not claimed. No files in the parallel 2D checkout were changed.


## 2026-10-22 — refined hot-thermo sensitivity

Refined independent thermo substitution retains GRI forward kinetics and changes
CJ speed by 0.044% and reaction length by 3.27%; numerical refinement is <4e-6.
This supports a conditional formed-wave numerical check, not a physical-fit
pass or uncertainty bound. Keep the existing full-GRI native baseline, declare
the extrapolated polynomial law and 5000 K inverse interval, and block any
engine/design conclusion pending the remaining dynamic, model and boundary
gates. See the G2 evidence in docs/verification/pelec_g2/README.md for limitations.

## 2026-10-22 — formed-wave initialization and transport root cause

Independent reference tolerance and exact conserved-profile integration resolved
initial trace-species/quadrature issues; native imported averages match <3.3e-17.
Short native reacting probes found a higher-order transport defect, reproduced
without chemistry and not cured by dt/cell halving. Global elemental ratios still
conserve; local deviations are spatial error. The source passes `plm_iorder` to
MOL, so changing `mol_iorder` alone is ineffective. Explicit actual first-order
reconstruction passes the original 2 ns field gates with no native clipping.
Full G2b remains open. Detailed attempts, controls and limitations are recorded in
docs/verification/pelec_g2b/README.md; a bounded longer diagnostic is in progress.


## 2026-10-22 — P3D-001 propagation gate remains failed

Three 0.2-us native controls complete but fail speed/reaction-distance accuracy;
dt halving does not fix the error and cell halving does not converge. Independent
boundary balances exclude a large unexplained mass/energy change. Every-step
state checks catch transient negatives and supersede the earlier snapshot-only
first-order probe pass. The finer case also fails the conservative buffer margin.
No engine was launched; no sustainment or two-hour engine claim is made. Keep the
full GRI reference, fix the control buffer and compare one native transport option
before more implementation. See docs/verification/pelec_g2b/README.md for recorded
causes, hypotheses, literature, timings and all failed controls. Nineteen fast tests
pass, including the new fail-closed intermediate-state regressions.

## Saved-wave movies and launch guide

Added `tools/pelec/animate_wave.py` and `tools/pelec/QUICKSTART.md` in response to
the request to watch and launch the current workflow. The committed movies use
the existing 4 um / 0.1 ns fine-grid native run, not a new cloud simulation.
There are two views: full-domain pressure/temperature propagation against the CJ
front, and a frame following the measured pressure front against independent
ZND pressure/temperature/heat fraction. The planar transverse means are labelled;
no annular rotation or new simulation values are synthesized. All 21 recorded
frames retain their actual physical timestamps. Fixed axes, nearest-neighbour
strip rendering, step profiles and no temporal interpolation avoid smoothing
away errors. The existing failed propagation status is printed in both movies.

Verification: both GIFs decode to 21 frames, loop, and have the prescribed 6.75 s
playback (longer initial/final holds). Initial/middle/final decoded frames were
visually inspected for labels, scales and clipping. All six source file hashes
match the recorded manifest. Trying an existing output directory raises
FileExistsError without changing any artifact. All 19 existing fast add-on tests
passed in 0.069 s; `git diff --check` passed. No solver or physics code changed.

Modal CLI 1.6.2 confirms the active `prox` profile/workspace when network access
is permitted; the sandbox-restricted lookup could not resolve the workspace.
The documented native launch flags were checked against the local entrypoint's
help. The guide distinguishes solver completion, numerical checks, physical
checks and local replay, and gives the observed 5.5/7.6/9.0 minute short-control
solver times without extrapolating them to a full engine. No paid cloud job was
started for this visualization update. P3D-001 / G2b remains open.

## Cross-branch injection/startup review

Fetched main `73d4516` and `2d-modelling-detwave-sustaining-fix` `6875f02` into
this clone; read source, configuration and committed failure studies without
modifying either 2D checkout. The first fetch approval timed out; the permitted
single retry succeeded. Compared the full `physics.py` hashes: both branches
share the corrected injector law. Distinguished that historical opening-plane
bug from later contact-burning and actual-refill-layer findings.

Added `docs/plans/3d_injection_startup_audit.md` with a side-by-side implemented
physics table, immutable evidence links and remaining limits. Re-read the cached
Argonne manuscript and verified its recorded PDF hash; inspected geometry and
methods page renders. The current 3D movie has no engine injector or physical
ignition sequence. Revision 19 adds native feed/refill/contact and finite-layer
qualification before an annular reacting preview; it preserves the unresolved
G2b propagation gate and separates formed-wave initialization from a finite
pre-detonator discharge. No solver, input constants or cloud job was changed.
Documentation links and `git diff --check` verified; no CFD rerun or extra unit
test is needed for this source/documentation review.


## October 24–25: native compact-chemistry 3D prototype

Latest user authorization explicitly requested both native solvers, modest Modal
resources and diagnostic GIFs. Implemented separate PeleC and detonationFoam
workflows, actual 3D field rendering, attributed 13-species/38-reaction FFCMy-12
conversion, homogeneous/planar controls, radial impinging inlet mouths and finite
tangential startup. GPU reached 10 microseconds in 431.9 solver seconds; CPU
reached 1 microsecond in 84.7 solver seconds. The requested millisecond sustained
circulation has not been achieved. Negative species, CPU clipping/closure and
planar speed/structure failures are retained as failures. A disconnected local
client interrupted one job; a detached retry completed. No other checkout changed.

The [concise report and evidence](3d_prototype_20261024/README.md) state assumptions,
measured runtimes, limitations and the next isolating controls. Reproduction is in
`tools/CFD_PROTOTYPE.md`. Native physical failures are not superseded by the 19
passing unit tests. Both full native engines exist as exploratory workflows; neither
is a validated engine model or a demonstrated 1–2-hour screening tool.


## October 25, 2026 — native failure isolation

Completed a 32-case campaign (31 target-time completions and one native ODE-step-limit failure), on at most one H100 and one separate 16-core CPU worker. Preserved native logs, checksums, input configurations, field-derived wave profiles, and comparison plots in [the diagnostic record](3d_diagnostics_20261025/README.md).

Identified PeleC cleanup-induced mass drift and timestep-sensitive negativity. Identified and tested detonationFoam's volume-/mass-flux inconsistency using an isolated patched executable; first-order upwind removes major clipping, but stricter closure and chemistry robustness remain unresolved. Longer planar runs approach CJ speed while failing reaction-zone structure checks. No engine validation or sustained-wave claim was added. The latest software suite passes 22 tests, and preparation reproduces the tested GPU inputs byte-for-byte.
