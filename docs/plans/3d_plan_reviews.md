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
