# Current 3D diagnostics handoff — October 25, 2026

Active checkout: `/Users/sgfx/.codex/worktrees/3d-cfd-review/prox_rde_sim`, branch
`3d-modelling`. The original 2D checkout remains untouched.

The 32-case native diagnostic campaign is finished: 31 runs reached their target
times; one tighter CPU chemistry control exhausted its internal ODE-step limit.
Read [the concise findings](docs/verification/3d_diagnostics_20261025/README.md),
[the full result index](docs/verification/3d_diagnostics_20261025/index.json), and
[reproduction commands](docs/verification/3d_diagnostics_20261025/REPRODUCE.md).

Confirmed: PeleC's embedded-boundary species cleanup adds mass in the disturbed
reacting annulus; disabling it preserves mass but worsens negative species.
A 1 ns step passes species bounds for 1 µs, with small residual mass drift.
detonationFoam constructs species convection with volume flux while transporting
with mass flux. The isolated `modal_flux_diagnostics.py` executable corrects this;
upwind transport removes major clipping but retains a 6.1e-8 closure residual.
Tighter chemistry fails at the attempted 0.10 µs step (last completed 0.08 µs).
The original limited-linear scheme still clips after the flux correction.

Both solvers' 2 µs planar controls relax toward CJ speed (late GPU 2558 m/s;
CPU 2579/2583 m/s at 16/8 µm; reference 2531 m/s). Their reaction-zone structures
remain wrong. Plausible speed is not physical validation. Do not treat the
existing diagnostic GIFs as a sustained detonation or an engine design result.
Next: bounded/conservative transport and resolved shock–chemistry coupling,
then injector refill and startup sensitivity, followed by multi-revolution runs.
22 software tests pass; this is separate from CFD physical acceptance.

The following is historical handoff context, not the current completion status.

---

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

T0-T2 are complete for detonationFoam. Revision 18 prioritizes a bounded
PeleC/Modal GPU trial (G0 and G1a native shock/reactor controls passed), retaining detonationFoam as fallback. Do not
complete two full CPU/GPU engine stacks. About eight GPUs are authorized initially;
Modal CPU and one-H100 access passed. Native PeleC CUDA smoke and independent
field/budget checks passed; reacting throughput and multi-GPU scaling are unknown. See [the literature/runtime decision record](docs/plans/3d_literature_runtime_review.md).
User authorized early implementation; the 14:30 kickoff is paused. G1a passed against the explicitly identified generated-rate reference; details are
in docs/verification/pelec_g1/README.md. G1b/c and methane G2 remain open.
The methane preflight isolated the 3000 K GRI inverse inconsistency. A documented
5000 K inverse-bound overlay passes numerical tests but does not extend physical
thermo validity. Small declared-law methane reactor controls now pass on CPU/H100 with step and
tolerance checks; full physical/propagation/engine gates remain open. See docs/verification/pelec_g2/README.md. Routine cases must fit the measured two-hour gate; no full-engine runtime has
been measured. Sustained-wave design screening requires the coupling/refill,
window, numerical/model sensitivity and negative-control gates in revision 12. All physics gates remain
in the selected backend; no OpenFOAM mesh pass transfers to PeleC embedded geometry.
Homebrew installed Colima, Lima and Docker; a dedicated two-CPU/4 GiB `rde3d`
profile mounts only this checkout and its temporary staging. Do not use the
original checkout as a native-case output destination. The bounded tutorial-based installation check passed. No reactive 3D engine flow or physical methane-model validation has passed yet. Do not run a full reactive engine through missing gates.

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


Native geometry/static checks and regular-grid MOL direction/refinement checks
pass; see [G1b evidence](docs/verification/pelec_g1b/README.md). Full dynamic EB,
AMR and reacting-engine gates remain open.

Native formed-wave initialization is verified, but **P3D-001 / G2b fails**:
0.2 us controls run about 15–18% too fast and do not resolve the reaction distance.
An every-step audit withdraws the earlier snapshot-only first-order probe pass.
See [G2b diagnostics](docs/verification/pelec_g2b/README.md). Do not advance to an
engine run. Repair the control buffer and compare one native transport option
before considering substantial solver work; no two-hour engine runtime is established.
