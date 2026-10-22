# 3D handoff - only commit and push to 3d-modelling

Checkout: `/Users/sgfx/Desktop/Projects/prox_rde_sim_3d`.
Original 2D checkout: `/Users/sgfx/Desktop/Projects/prox_rde_sim` (do not edit).
Baseline: `0f435aad6b23e063a35f1017a985d5ee8ee8145d`, 2026-10-22 01:35:05 PDT.
Independent clone, no Git alternates/hardlinks; remote points to the same GitHub
repository. `remote.origin.push` names only the 3D branch. Check branch and cwd
before edits/commits and push explicitly with `git push origin HEAD:3d-modelling`.

The [3D plan](first_sim_plan.md) supersedes implementation ordering in inherited
2D documents. Self-review rounds are in [the review log](docs/plans/3d_plan_reviews.md).
Keep the [implementation record](docs/verification/3d_progress.md) current.

T0-T2 are complete for detonationFoam. Revision 12 prioritizes a bounded
PeleC/Modal GPU trial (G0 smoke and G1 shock controls passed; chemistry held), retaining detonationFoam as fallback. Do not
complete two full CPU/GPU engine stacks. About eight GPUs are authorized initially;
Modal CPU and one-H100 access passed. Native PeleC CUDA smoke and independent
field/budget checks passed; reacting throughput and multi-GPU scaling are unknown. See [the literature/runtime decision record](docs/plans/3d_literature_runtime_review.md).
User authorized early implementation; the 14:30 kickoff is paused. Current G1 chemistry investigation is recorded in docs/verification/pelec_g1/README.md.
Do not advance to methane/engine work through that gate. Routine cases must fit the measured two-hour gate; no full-engine runtime has
been measured. Sustained-wave design screening requires the coupling/refill,
window, numerical/model sensitivity and negative-control gates in revision 12. All physics gates remain
in the selected backend; no OpenFOAM mesh pass transfers to PeleC embedded geometry.
Homebrew installed Colima, Lima and Docker; a dedicated two-CPU/4 GiB `rde3d`
profile mounts only this checkout and its temporary staging. Do not use the
original checkout as a native-case output destination. The bounded tutorial-based installation check passed. No 3D flow or methane chemistry
validation has passed yet. Do not run a full reactive engine through missing gates.

Pinned detonationFoam candidate: `4bd2e86003447fdb143b475f199c846146f754e3`,
OpenFOAM 8. Source audit identified early success exit, species clipping and
convective-only adaptive CFL; see plan. Use fixed steps for initial native tests.

Reuse the frozen starter and D3 reference evidence. RDE-001 and the 2.46% physical
CJ discrepancy remain open. Source changes in the 2D session are not imported live.
Its C1-C6 tests distinguish directional errors, formed-profile propagation, layer
survival and initiation before choosing a model change; none were completed in
the baseline. New related evidence should be reviewed before any later merge.

The existing Python environment may be read through
`/Users/sgfx/Desktop/Projects/prox_rde_sim/.venv/bin/python`; do not install into
or alter it. All source imports/run outputs must resolve inside this 3D clone.
Bulk native outputs and downloaded/build dependencies will be Git-ignored.
