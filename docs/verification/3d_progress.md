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
