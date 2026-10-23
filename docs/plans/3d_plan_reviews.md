# Five planning reviews before implementation

October 22, 2026. Self-review rounds, not independent external peer reviews.
Each round reads the revised plan from the previous round and changes its gates.
The review does not declare a CFD result validated.

## Round 1 - scope and physical identity

Initial proposal: evaluate detonationFoam now, then build a full annulus and reuse
the 2D physics harness. Checked against revision 8, the model audit, Mundt Tables
2-1/2-2/3-2 and Fig. 2.4 (the complete relevant text and cutaway inspected).

Issues: a simple extrusion still omits core termination; the 2D engine-success
prerequisite blocks independent backend work; premixed feed and the inherited
surrogate could be misrepresented as experimental physics.

Fix: explicit separate 3D add-on; remove 2D engine-success dependency, preserve
small verification tests; make expansion a distinct geometry; label premixing
and startup assumptions; require new methane thermodynamics/source checks.
Recheck: table dimensions and downstream taps now have a place in the domain.

## Round 2 - native solver behavior and false passes

Reviewed Round 1 against the pinned upstream C++ and tutorial dictionaries.
Issues: the default tutorial exits at a shock location with EXIT_SUCCESS before
its endTime; the Euler species update clips negative fractions; sensible native
energy differs from the starter's stored-chemical-energy total. Optional DLB/2D
AMR libraries are enabled by the shipped build/tutorial.

Fix: require final-time/field verification in addition to exit status, set the
shock cutoff beyond non-tutorial domains, retain source pin and actual build
libraries, require quantified clipping/elemental conservation before methane
validation, document the energy mapping explicitly. Static mesh is the first
supported capability. Recheck: no proposed test can label an early process exit,
unmeasured repair or a raw cross-backend energy comparison as a physics pass.

## Round 3 - mesh topology, coordinates and reuse

Reviewed the amended plan's geometry and cross-backend tests. Issues: an annular
mesh ending on the axis risks collapsed cells; a sector imposes angular periodicity;
exact equality to an unrolled flow would reject legitimate curvature effects;
pressure stations beyond the inner core cannot be silently dropped.

Fix: full 360-degree connected mesh, separate downstream square/O-grid, named
core-end patch, declared Cartesian/azimuthal convention. Compare native volume and
patch areas with analytic formulas and refine angular tessellation. Use a uniform
Cartesian extrusion for the exact reduced-limit test; curved/2D comparisons are
model comparisons. Recheck: no zero-volume axis construction, no imposed N=2, and
geometry-only/coarse results are explicitly barred from chemistry claims.

## Round 4 - cost, stability and meaningful assertions

Reviewed Round 3 against upstream time stepping, host capacity and Strakey and
Ferguson's 3D/1D verification study (AIAA 2022-1113, pp. 3-4 and 9-10).
Issues: the upstream tutorial has 20,000 cells and a long write-heavy interval;
this host has 17 GiB free; a tutorial dictionary's acoustic-CFL flags are unused
by the inspected implementation. Short transients cannot match measured means.

Fix: small declared installation smoke, explicit fixed step with independent
acoustic bound, finite physical/wall-time caps, memory/disk benchmark before any
large run. Added quantitative cold-state and mesh assertions. Keep the related
study's operating point separate; retain the existing three/five-passage cap and
short-window labels. Recheck: every early step has a cheap falsifiable output;
a zero-exit simulation without required fields or stability evidence is a failure.

## Round 5 - dependency gates, reproducibility and scope

Read the entire amended plan against the existing test harness and figure roadmap.
Issues: T3/T4 were still too broad for one verifiable increment; restart and
cross-branch reuse could accidentally import changing source; paper-average and
short-window pressure comparisons needed an explicit distinction. Successful
geometry preparation could otherwise be mistaken for successful CFD.

Fix: split T3/T4 into smaller delivery gates; immutable source/image/input manifests,
refuse overwrite, finite-state and final-field checks, disabled unverified restart,
serial before MPI, cold-only capability rejection until chemistry verified. Reuse
2D code through reviewed Git history rather than a shared mutable import. Require
per-commit test evidence and open-issue disposition. Recheck: no critical issue is
waived as a future feature; unknown paper/model quantities remain explicit. The
plan is ready for implementation of T1/T2, with T3-T7 gated on actual evidence.

All five rounds completed before project implementation. Installing prerequisites
and reading upstream code proceeded during planning; neither was treated as a
validated simulation. Round 4/5 incorporate the new layer-diagnostic review: it is
a credible hypothesis and does not eliminate outlet, startup or numerical causes.


# GPU revision reviews — October 22, 2026

These additional self-reviews concern the new user priority and eight-GPU access.
They do not supersede the evidence/status of the original five rounds.

## Round 6 — backend decision and reuse

Reviewed the proposed GPU direction against current primary Modal, PeleC, MFC and
Fluent documentation. Issues: a GPU allocation does not accelerate the installed
CPU executable; two complete model branches duplicate work; GPU chemistry support
cannot be inferred from a generic GPU solver label; old claims that Fluent has no
GPU reactions would now be false.

Fix: one physical project, same-backend CPU/GPU controls, bounded PeleC trial and
installed detonationFoam fallback. Explicitly acknowledge Fluent's finite-rate
GPU capability while documenting the pressure-based formulation and unestablished
license/case availability. No custom GPU port or simultaneous alternative stack.
Recheck: backend change is conditional on measured capability, not marketing or
a claimed speedup. First revision of GPU plan/decision record saved.

## Round 7 — physical shortcuts, mesh migration and dependency ordering

Reviewed the first GPU revision against PeleC EB documentation and our geometry
arithmetic. Issues: native mesh verification cannot transfer; cut-cell species
repair can change mass/energy; uniform coarse cells do not resolve the inherited
reaction scale; the first draft placed a reactive AMR crossing test before its
chemistry verification dependency. Old text still mandated three passages first.

Fix: independent EB geometry/cold checks and quantified repairs; same physics
1D grid/dt checks; distinguish cold AMR crossing from reactive crossing after G2b;
allow uniform-grid trials to defer unneeded dynamic-AMR work. One-passage first
checkpoint, three/five-passage cap retained. Old native-field/units and local-only
wording now identifies backend scope. Recheck: no cyclic test dependency and no
coarse engine pass can substitute for propagation/chemistry verification.

## Round 8 — turnaround, scaling, acceptance and final consistency

Reviewed the amended dependency order and the complete entry-point documents.
Issues: eight GPUs need not minimize turnaround; a one-GPU case may not fit;
raw cell-state storage understates memory; generic cold criteria incorrectly
required every species to be strictly positive; per-run timeouts do not bound
queue delay or retries. Native boundary names must not imply OpenFOAM patches
exist unchanged in an EB backend.

Fix: measure queue/setup/integration/I/O separately, use the smallest fitting
allocation as a declared scaling baseline, compare against multiple independent
small runs, and retain memory headroom. Species may be zero; pressure, temperature
and density must be positive. Surface identities transfer, native topology does
not. Require predeclared tolerances/correction budgets and tested restart before
retrying costly work. Resource/time checkpoints remain explicitly unmeasured
planning decisions. Recheck: no GPU job, new chemistry pass or speedup is claimed;
README/handoff direct G0 while keeping T0-T2 evidence backend-specific.

Verification for this documentation increment: seven existing 3D unit tests pass
in 0.101 s; geometry/cell-count/CFL arithmetic and changed-document local links
checked independently; `git diff --check` passes. No CFD rerun was necessary.


# Literature/runtime revision reviews — October 22, 2026

## Round 9 — source provenance and intended use

Re-read Mundt Chapter 3/4 text and all rendered pp. 44-103, revisited methods,
and compared ten primary papers/reports with official solver documentation.
Issues: experimental Run 937 had been conflated with a CFD target; a 2D FFT and
unwrapped image do not identify simulation dimension; published GPU speedups and
a short OpenFOAM timing sample do not forecast this case. PeleC's public RDE
example reviewed here is 2D, not an off-the-shelf 3D methane/oxygen setup.

Fix: the revision 12 record separates experiments, thermo/empirical references,
full 3D literature, and abstract-only evidence. Record each study's fuel/model
and hardware limitations. User's early-start update makes sustained detonation
the eventual design-screening objective; add explicit exclusions for rotating
pressure pulses, forced ignition, and unmodelled injector mixing.
Recheck: GPU preference remains a bounded engineering decision, not a validation
claim; premixed idealized success cannot classify modified injector designs.


## Round 10 — runtime arithmetic and sustained-wave criteria

Reviewed the saved revision against the two-hour requirement and the user's
clarification that future modified-design screening is the objective. Issues:
raw throughput limits could omit the 30% safety margin; a watchdog cannot force
cloud availability; two milliseconds does not itself prove stationarity; stable
wave speed alone can conceal changed mixing, reaction coupling or refill.

Fix: separate measured and margin-adjusted throughput limits, explicit queue
cancellation, measured-period/window checks, sustained-wave classification tiers,
non-detonative experimental negative control, and startup/feed/outlet sensitivity.
Clarify resolved 1D references versus under-resolved 3D diagnostics without claiming
DNS. Recheck arithmetic: 2 ms needs <=2.077 measured wall seconds/us before the
30% margin for 90 minutes integration. A failed coupling check blocks extension;
cheap 2D tests inform, but do not automatically determine, 3D outcomes.


## Round 11 — execution consistency and minimal deliverable

Reviewed amended runtime/physics decisions and all entry-point documents. Issues:
README/handoff still said revision 11 and no CPU access; the figure catalogue's
G-numbers could be confused with native GPU gates; the old absolute preview cap
conflicted with a qualified longer screening case; a queued kickoff could duplicate
the newly authorized early start.

Fix: revision 12 override and links, accurate access status, explicit distinction
between figure backlog and native test gates, separately gated <=2 ms case, and
paused kickoff automation. Keep one active solver implementation, no new backend
framework, no full figure campaign and no dependency on unpublished 2D work.
Recheck: all changed-document local links and git whitespace checks pass; throughput
and cost arithmetic checked. No solver result or runtime is claimed by this
documentation change. Native implementation can now start at G0.


## Round 12 — numerical failure versus mechanism identity

Observed: CPU/GPU agreement and conservation did not guarantee correct ignition;
CPU could continue after a failed CVODE solve. A nominal YAML comparison mixed
integration error with two generated-rate constant conventions. Tight tolerances
with the native order-2 cap reached a substep limit.

Fix/check: fail-closed log guards, independent native operator probes, separate
nominal and generated-rate references, and unchanged numerical error criteria.
The EOS-precision hypothesis was tested and rejected as the dominant cause.
Native order 5 resolved the substep failure with faster, more accurate controls;
CPU/GPU, field budgets, peak species, timestep and tolerance checks pass. Keep
nominal-YAML differences visible and do not transfer these settings to an engine
without new checks. No physics-rate adjustment or new numerical method added.

## Round 13 — methane hot-state eligibility before expensive implementation

Source inspection finds the native DRM19 and GRI inversion bounds at 3000 K,
whereas the existing physical reference has approximately 3994 K CJ products.
An initial-guess-independent compiled round-trip check is required, along with
forward thermo, fit ranges and mechanism provenance. Test a second existing
candidate only if this first screen rejects DRM19; do not silently extend data
ranges or mistake a different mechanism's thermodynamic pass for kinetic
validation. These source/operator checks precede a methane GPU build.


## Round 14 — reduced-model agreement and thermo correction scope

Issue: FFCM1_Red's 0.04% CJ agreement conceals 11–16% reaction-length differences
and a changed cooler/high-pressure ignition classification. Fix: retain full GRI
as the paper-comparison control; do not choose a reduced production model solely
for speed. Tightened independent integration preserves the classification, so
this is a model difference, not ODE accumulation. It is not proof GRI is truth.

Issue: native GRI forward/inverse thermo is inconsistent above 3000 K. A diagnostic
two-line inverse-bound overlay fixes the numerical round trip through 5000 K,
without changing rates or coefficients. Published fit limits are still exceeded.
Fix: separate numerical-law verification from physical suitability; regression
tests prevent a corrected inverse from passing the physical fit gate. Only small
numerical reactor controls may proceed under this explicit assumption. No engine
propagation/survival conclusion is authorized by it.

Recheck: original/diagnostic compiled energy and enthalpy operators, every species'
polynomial cv extrema, independent ZND/ignition refinement and conservation, plus
16 fast 3D tests. A new reference-wrapper state-reuse error was caught by the
strict ZND peak check, corrected by resetting the frozen state, and re-run.
The two-hour target remains a measured future gate, not an estimate from controls.


## Round 15 — native geometry conventions and hydro-path coverage

Issue: a visually plausible annulus and correct total volume do not certify
wall normals, port apertures, surface closure or moving-wave accuracy. Fix: a
read-only native diagnostic hook exports the actual flux-boundary structures.
Explicitly convert the stored inward normal using the verified pressure-flux sign;
no native physics is changed. Both grids pass areas/orientation/closure and cold
budgets. Retain the nonmonotonic core-edge slice maximum: geometry L1/areas improve,
but no maximum-norm convergence or dynamic EB acceptance is claimed.

Issue: G1a's Godunov shock pass did not cover the MOL method required for EB.
Fix/recheck: seven native MOL cases now pass exact-solution grid/timestep checks,
all-axis invariance and CPU/GPU equivalence. Dynamic cut-cell corrections and
AMR remain separate prerequisites, especially because default SRD slopes are zero
and may add diffusion that could be mistaken for physical wave extinction.


## Review 16 — do not confuse thermo sensitivity with validity

Refined independent thermo substitution retains GRI forward kinetics and changes
CJ speed by 0.044% and reaction length by 3.27%; numerical refinement is <4e-6.
This supports a conditional formed-wave numerical check, not a physical-fit
pass or uncertainty bound. Keep the existing full-GRI native baseline, declare
the extrapolated polynomial law and 5000 K inverse interval, and block any
engine/design conclusion pending the remaining dynamic, model and boundary
gates. See the G2 evidence in docs/verification/pelec_g2/README.md for limitations.

## Review 17 — actual reconstruction path, local error versus global budgets

The formed-wave probe exposed local species/element defects that cold Sod and
homogeneous chemistry cannot detect. Halving dt and disabling reactions did not
remove them; actual first-order transport did. `mol_iorder` was misleading for the
pinned call path: `Diffusion.cpp` passes `plm_iorder`. Both are now explicit, with
failed and successful probes preserved. Do not equate local elemental error with
atom creation: integrated ratios conserve to roundoff. Do not accept the
first-order option until reaction coupling and wave-speed/grid checks pass.
The four-hour checkpoint retains the native GPU candidate but makes no engine
runtime promise. See docs/verification/pelec_g2b/README.md.
