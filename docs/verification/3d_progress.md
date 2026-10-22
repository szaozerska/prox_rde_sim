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
