# Controlled 2D investigation — execution plan

October 22, 2026. Companion to master-plan revision 13.
**This session commits and pushes only `main`.** The separate session owns
`3d-modelling` in its separate checkout. The final reference to that branch in
the overnight instruction is interpreted in light of the explicit main-only
assignment; this session must not change, merge or push the other branch.

## Current gate

C1–C4 and C5a are complete within their stated scopes. **C5b–e's declared
quarter-length surrogate experiment is complete:** both meshes retain wall/middle
shock-associated reaction through 10 us. **C6a functional initializer/benchmark is complete:** 2 us, 556 steps, zero
invalid states; 86 distinct passing tests and one opt-in skip. The latest instruction
assigns sustained-wave studies to a separate chat; no three-interval engine
study is launched here. See the [new results and decision](../verification/c5_short_reaction.md).
This status supersedes earlier running/conditional language in the dated reviews
below. No stable rotating-wave milestone is claimed.

## Purpose and evidence

Separate implementation error, detonation-profile initialization, finite-layer
propagation, and blast-initiation adequacy before changing the engine model.
The [diagnostic review](../verification/layer_diagnostic_review.md),
[paper audit](../verification/mundt_model_audit.md), and
[D3 results](../verification/d3_investigation.md) supply the starting evidence.
These idealized controls test the Run 937 surrogate at its documented state;
they are not new experimental reproductions. The critical layer height is unknown.
The reported 3.8 mm operating refill estimate is not a measured startup condition.

Mundt pp. 9, 13, 26, 34, 74–78 distinguish introductory kinetics, interface
burning, physical ignition/injection and physical references. Relevant control
precedent: [Li, Mi and Higgins](https://arxiv.org/abs/1405.7753), formed waves in
layers with yielding confinement, using a different reaction law;
[Taileb et al.](https://doi.org/10.1016/j.combustflame.2020.04.018), chemistry-dependent
layer quenching in hydrogen–oxygen; and
[Strakey and Ferguson](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf),
1D verification preceding 3D methane–oxygen calculations and a hot-kernel start.
No critical-height threshold or initialization parameter is copied from these
other mixtures/models as if it were measured for Run 937.

## Small increments and gates

| Increment | Implementation and bounded experiment | Required checks before proceeding |
|---|---|---|
| **C1. Multirow/direction control** | Reuse the existing 1D blast case at 0.5 mm in a short multirow strip; compare transversely uniform fields and a rotated version. Same gas and common accepted timesteps. A 95 µs propagation comparison is opt-in; fast checks exercise only a few source/flow steps. | Field equality/transposition to floating-point tolerance, transverse invariance, conserved budgets, no invalid states, matched front histories. Any discrepancy stops C2 pending investigation. Passing excludes these tested indexing/boundary errors, not all 2D bugs. |
| **C2. Formed-profile control** | Initialize the existing surrogate's steady CJ/ZND profile conservatively, with correct lab-frame momentum and chemical energy, then propagate it in a fully filled strip. Use a finite tail and an explicit downstream fresh state. | Independent mass/momentum/energy jump checks, integrated reaction lengths, cell-average convergence, positive/admissible state, and bounded unforced propagation. Verify driver/boundary separation and grid sensitivity before interpreting layered failures. A threshold pressure track alone is insufficient. |
| **C3. Layer response** | Put that verified profile into a fresh layer with 1500 K products above it. Start with 3.8 and 15 mm at fixed 0.5 mm spacing. Add 7.6 mm only if it helps bracket different outcomes; use 30 mm only if the thick control is inconclusive and its longer relief time/domain are justified. Repeat only decisive cases at 0.25 mm. | Conservative inventory, recorded interface/igniter energy and momentum, sufficient duration after transverse relief, no driving or remote-boundary contamination, continuing shock/reaction association or documented decay. Report a bracket only when supported; otherwise report bounded response/inconclusive. A thinner failed case with a surviving thicker case establishes a model limitation under these conditions, not the entire engine root cause. |
| **C4. Initiation isolation** | At a thickness where the formed wave persists, compare an explicitly specified blast patch. Preserve the medium and boundaries; record differences in igniter energy and momentum. | A failed blast with a surviving formed wave distinguishes initiation from propagation for that controlled case. If no formed wave persists, do not launch this step yet. |
| **C5. Supported 2D model decision** | Combine controls with saved Run 937 fields/budgets and physical reference evidence. Select one justified change to startup, numerics, boundary closure or chemistry; document why before coding. | No arbitrary tuning, no simultaneous unrelated changes. Any revised chemistry passes reactor/source, contact and 1D checks at fixed parameters before engine use. Any changed initializer requires a comparable coarse baseline. |
| **C6. Bounded engine check** | Apply the verified change to an explicitly named Run 937 variant, preserving the original baseline. Three reference intervals; a justified same-run extension to five total remains the limit. | State validity and native budgets; spatial/temporal qualifications; front speed relative to local upstream state, reaction association, replenishment, and normal exit characteristics. Distinguish sustained detonation, unsuccessful initiation, later decay and insufficient duration. No long-term or experimental-average validation claim from this short run. |

## Review pass 1: causal isolation

Initial proposal: multirow control → layer-height sweep → blast/profile comparison.
Issue: a poorly initialized formed wave could fail in every layer and falsely
implicate confinement. Fix: insert C2's fully filled formed-profile propagation
and conservative/jump checks before any layered run. Keep physical validation
separate from implementation checks. C4 is conditional on a successful C3 control.

## Review pass 2: numerical comparability and causality

Issue: cell-center masks change fresh charge and ignition energy under refinement;
changing kinetics with the grid would add a second confound. Fix: integrate initial
conserved variables over cells, record actual inventories, and keep the same
chemistry within each spatial comparison. At a cut interface, record initial
numerically mixed cells and their effect rather than claiming zero diffusion.

Issue: thick layers need longer transverse communication time; short runs can
make them look sustainable before losses reach the full layer. Remote boundaries
or an imposed driver can also fake persistence. Fix: select domain and finite
end time from characteristic travel scales before each run, record boundary
signals and conservative causal-distance bounds, and extend/rebuild the control
only with a documented reason. A numerical-transmissive boundary is not assumed
nonreflecting or causally isolated. No claim of convergence from two meshes.

## Review pass 3: scope, measurement and stopping rules

Issue: four heights at two meshes plus engine runs would be an unnecessary
campaign. Fix: start with two heights; select follow-ups from evidence. A single
small reusable diagnostic module and existing plotting/reduction modules suffice;
no workflow framework, generic plugin registry or new solver is needed.

Issue: fitting a pressure ridge can mistake a blast for a detonation. Fix: retain
pressure, progress, reaction rate, front-relative separation, local upstream
state and speed, chemical conversion and native conservation together. Inspect
fields and several time windows. Publish ambiguous or boundary-contaminated
results as such, rather than tuning a classifier to claim success.

Issue: the instruction names both branches and previous plan deferred 3D behind
2D success. Fix: `main` remains this session's 2D branch; the independent 3D
session can prepare its backend now. No 3D success claim or cross-branch push is
part of these controls. detonationFoam installation is authorized if needed, but
is not a dependency for C1–C4 using the existing solver.

## Test/runtime policy and commit record

- Fast default tests: algebraic conservation/jump relations, finite-volume
  inventory, transpose symmetry, valid input limits and a few timesteps.
- Bounded propagation/layer runs are explicit opt-in diagnostics. Save raw fields,
  inputs, hashes, runtime and failures. Reuse saved outputs for graphs; do not
  rerun CFD for plotting or put the height campaign in every unit-test invocation.
- Use two Numba threads initially. Benchmark the first control before enlarging
  its domain, grid or case list. Favor shorter meaningful experiments over broad
  grids of parameters. Enforce finite step/time limits and state rejection.
- At each gate, review resolution, timestep/source accuracy, numerical mixing,
  initialization and boundary causality, physical assumptions, and whether the
  proposed conclusion exceeds the sampled duration. If a critical inconsistency
  remains, repair or document the blocked inference before the next increment.
- Before each commit: record changes, checks, results, limitations, identified
  causes versus hypotheses, and the selected next action in the verification
  report/handoff. Check the current branch is `main`; commit only task files and
  push `HEAD:main` without force. Preserve the other session's branch and checkout.

## Gate update after C2

C1 and C2 passed their bounded checks; see the increment log. C3 uses the same
0.45 m axial domain, shock initially at 0.16 m and a 40 µs cap. Add 130 mm of
hot products above the layer, with a remote reflecting top (no pressure driver).
Check an axial characteristic bound of 4000 m/s and transverse bound of 3000 m/s
against all RK intermediate/accepted states; stop if exceeded or if their cones
reach the 30 mm front/reaction region. At 40 µs the top cone has a 10 mm margin.
The nominal h/a_VN relief times are 4.16 and 16.41 µs for 3.8 and 15 mm: 40 µs
covers initial transverse communication for both, but cannot prove asymptotic
survival. Use conservative cell fractions for the cut layer. Initial products
are at p1, 1500 K, progress 1, zero velocity; the formed profile occupies only
the lower layer. This discontinuity launches the intended transverse release.
This is an isolated propagation control, not the experimental startup history.

## C3 coarse gate review

The two initial heights give a useful contrast. Repeat both at 0.25 mm before
adding heights or comparing ignition. The thin case's main reaction detaches;
the thick case remains strongly coupled near the wall/middle over the bounded
window, with transverse structure. Inspect all saved fields and near-front
rates, since global burning persists even when the leading shock loses coupling.
Explicitly retain numerical interface mixing as an unresolved contributor.
Do not add 7.6/30 mm merely to populate a sweep, and do not change chemistry
until the refinement evidence is assessed.

## C3 review: initial interface averaging

The 3.8 mm cut row starts at 435.36 K / 2.315 s^-1 on the 0.5 mm grid,
but 843.99 K / 1127.47 s^-1 on the 0.25 mm grid, despite conserved totals
agreeing to roundoff. This is a subcell averaging effect, not a calibration
change; it must not be omitted from interpretation. The 15 mm interface is
already face-aligned apart from roundoff.

Add **one** face-aligned 3.8 mm control at nominal 0.5 mm before C4. Eight
lower rows give dy=0.475 mm; 274 product rows give a 130.15 mm buffer. The
fresh-layer height and formed-wave excess mass/momentum/energy are unchanged.
The extra 0.15 mm of products lies beyond the conservative causal bound.
This changes vertical spacing by 4.85% as well as initial cell phase, so it is a
combined startup-averaging/vertical-mesh sensitivity, not a pure phase experiment.
Refinement of this aligned geometry, if justified, subdivides the same domain.
It removes initial mixed cells but does not suppress subsequent HLL contact
diffusion or reaction. Check whether the leading shock still separates from
reaction; select any further comparison from the result, not an automatic sweep.

C4 remains conditional on the C3 evidence. Its blast comparator must retain the
documented 10 mm patch, 2×CJ pressure, CJ temperature, zero initial momentum and
20 mm of 1500 K products behind it. Record its different conserved inventory
relative to the formed wave; do not call it an equal-energy comparison.

## Refined-thick bound review and continuation gate

The first refined 15 mm run stops at 23.555864 µs because its maximum transverse
characteristic speed exceeds 3000 m/s by 0.020623 m/s. State/budgets remain valid,
and the saved top four rows are unchanged. Continue its checked saved state with
an explicitly recorded 3200 m/s bound: the same domain retains 2 mm of top
margin at 40 µs. Preserve the failed-bound record. No physical/numerical
parameters change. Reject continuation if calibration/source hashes differ,
state/inventory recovery fails, or the revised cone reaches the measured region.

The aligned thin control also loses coupling, so no further initial-interface
phase sweep is justified now. C4 still waits for the refined thick endpoint.
The prepared C4 blast uses 5000/3500 m/s bounds with L=550 mm, initial front
x=200 mm and 150 mm product buffer; this gives room for its hotter expansion.
Those are remote-domain changes, not changes to the local mixture or boundary
types. Compare front displacement from initialization and record the different
initial conserved inventory. A bound stop is a protocol issue to assess, not
a detonation-failure label. Full production chemistry remains unchanged.

## C3 closure and C4 execution decision

C3's refined thick endpoint confirms near-wall/middle shock-associated reaction
through 40 µs, while all three thin controls lose leading-front coupling.
Advance only the bounded qualitative gate: no steady state, critical height or
complete spatial convergence has been established. The original bound stop was
a diagnostic-domain issue and its audited continuation is complete.

C4 now runs once at 15 mm and 0.5 mm. Its baseline is the saved formed control;
compare front displacement, global/near-front reaction, native budgets and
causal margins. Both starts have the same fresh/product thermodynamic states
and boundary types, but deliberately different initial energy/momentum and
remote-domain sizes. Any failed blast conclusion is limited to this grid/window;
if it changes the C5 decision, assess whether one refinement is necessary before
using it. No parameter sweep or unsupported engine change follows automatically.

## C4 closure: weaker reacting blast, no startup-only remedy established

The 15 mm blast reaches 40 µs with valid budgets/causal bounds and continuing
reaction behind the leading shock. It is weaker and slows more than the formed
starts; its late pressure/reaction trends do not establish eventual survival or
extinction. Thus the proposed "formed succeeds / blast fails" discrimination is
not obtained over this window. No engine igniter change is selected from it.

Proceed to C5's **decision and feasibility review**, keeping chemistry/engine
inputs frozen. Review the physical reaction structure and cost of resolving it
before adopting constants. C6 stays gated. No extra height or ignition-energy
sweep is justified by the completed comparison.

## C5 review and decomposition: do not promote unresolved constants

The physical reference is not a uniform rescaling of the inherited surrogate.
A two-distance Ea/k fit is underresolved on the engine grid and makes the current
source cap impractical (91.09 million steps for the bounded engine window).
It also leaves a held-out shape error and the existing thermodynamic mismatch.
The candidate is retained as algebraic evidence only; no engine inputs change.

Split the remaining C5 work into small, verifiable gates:

| Next increment | Verification before the following increment |
|---|---|
| C5b: one documented reaction-model hypothesis, with fitted/held-out physical quantities | Reconcile or explicitly scope CJ/EOS differences; record whether the choice is physical or only a surrogate sensitivity. No parameters selected by successful engine appearance. |
| C5c: source-treatment feasibility on homogeneous reactors and representative shock states | Independent converged ODE comparison, chemical/total-energy consistency, admissible states and runtime sample. A sharper timestep bound/integrator must be verified, not bypassed. |
| C5d: short filled-profile propagation at fixed chosen chemistry | Independent jump/profile checks, source-step comparison and decisive mesh comparison before a thin-layer test. Domain/time selected from causal bounds. |
| C5e: revisit the decisive 3.8 mm layer, then choose a justified engine variant | Reaction association, numerical mixing, native budgets and causal margins combined. C6 remains conditional on that assessment. |

No immediate solver rewrite, broad mechanism/height sweep, new engine startup or
3D switch is justified by this assessment. This stop honors the instruction not
to advance past a critical model/numerical inconsistency. It is not a claim that
the original implementation task or sustained-wave goal has been completed.


## C5b–e: declared quarter-length surrogate

Authorized October 22 after independent-report review. This is a model
sensitivity, not physical-chemistry calibration or a prediction of Run 937.
Select L50=0.25 mm before observing results; multiply inherited k by four and
keep Ea, gamma, R, q, p1 and T1 fixed. L90/L95 become about 0.785/1.044 mm;
physical L50 is still about 6.3 times shorter. Do not modify production defaults.

1. Verify homogeneous cold, warm and shock-heated reactors against independent
   DOP853 solutions at source fractions .05 and .025 (progress error <2e-4,
   energy invariance and approximately second-order decrease where measurable).
   Check profile jump residuals <1e-8 and lengths by independent quadrature.
2. Filled formed wave: 0.125/0.0625 mm, 10 us, and half source step on the coarse
   mesh. Require valid states, budgets <1e-10, positive causal margins, late
   speed within 2% of model CJ and source-step speed change <1%. This verifies
   the surrogate, not the experimentally fitted CJ value. Diagnose any failure.
3. Moving contacts, frozen/reactive at both meshes, 5 us with original 300 m/s
   advection and 1500 K products. Quantify numerical mixing/burning; do not use
   a contact integral as a bound on engine losses. Require valid budgets and
   boundaries matching their homogeneous reactor evolution, zero frozen heat release and pressure preservation.
4. Only after these checks: one formed 3.8 mm layer at each spacing, 10 us.
   Domain length 112.5 mm, initial shock 40 mm, hot-product buffer 32.5 mm,
   observation width 7.5 mm, snapshots every 1 us. These are one-quarter of
   C3's remote lengths; layer height is 3.8 mm, not exactly scaled 3.75 mm.
   Bounds 4000/3200 m/s, checked against RK states, leave 0.5 mm top margin.
   Evaluate pressure/reaction separation, local upstream state, late front
   slopes, heat conversion, initial mixed cells, budgets and causal margins.
   Failure is useful evidence; do not automatically change k or extend the run.

Review 1 — isolation: changing chemistry and integrator together confounds the
cause. Keep SSP-RK2 and the conservative source-slope cap unchanged. Its new cap
is about 3.61 ns; the old 91-million-step estimate is irrelevant to this case.

Review 2 — runtime/causality: the old 450 mm domain is unnecessarily expensive
at this spacing. Scale only the remote domain and diagnostic window to the
10 us bound, preserve local states, and record every dimension. Bound violation
stops interpretation. This is about 2.4 original-layer acoustic relief times;
it cannot establish asymptotic survival. Two cells per L50 on the coarse mesh
are a starting point, not sufficient evidence of multidimensional convergence.

Review 3 — inference: C3 and scale similarity motivate the selected length but
do not establish a critical h/L50 of 15 or a universal margin. A successful
10 us result warrants a review of the next discriminating experiment; the final
gate review below selects C6a instead of an automatic longer layer rerun.
A failed or materially contradictory result requires diagnosis first. Inspect native
fields alongside summary tracks. Do not import the independent report's wrong
outlet timing or its comparison of source slope with reaction rate.

Use `short_reaction.py verify --out NEW` then
`short_reaction.py layer --verification VERIFY_DIR --out NEW` from the starter.
The second command requires successful saved verification with matching source
fingerprints. Large runs remain opt-in, never default unit tests. Preserve all
old baselines and independent report edits. Publish outcomes on main only.


C5 verification correction: the first reactive-contact gate compared fresh far
fields with their frozen initial pressure. Nonzero 300 K Arrhenius reaction
produces a predicted ~1.43e-6 relative pressure rise by 5 us. Keep the stopped
verification record; compare all five far-field primitives against an independent
homogeneous ODE, with 1e-9 scaled tolerance. A synthetic boundary perturbation
must fail that check. Reuse matching completed CFD cases; do not rerun them or
relax the physical-state checks. Solver and chemistry are unchanged.


## C5b–e gate review that selected C6a (now completed)

Both meshes complete the predeclared window with valid budgets and continuing
near-wall/middle reaction. See [results](../verification/c5_short_reaction.md)
for the nonconverged upper layer, transient pressure pulse, initial contact
mixing, unequal time/grid comparison with old C3 and retained physical-model limits.
These are qualifications of a successful bounded experiment, not a new arbitrary
stop on all implementation. No sustained engine or unique-root-cause claim.

Next implement one conservative, periodic formed-wave engine initializer for
an explicitly named 0.25 mm reaction-length / 0.125 mm grid case. Verify seam
behavior, correct lab-frame momentum, initial inventories and energy accounting,
state validity and checkpoint/native-budget behavior. Run a separately labelled
2 us cost/validity benchmark only after those checks. Use measured cost to select
the bounded three-interval engine experiment or a separately verified source
integration improvement; freeze chemistry in either path. An additional longer
layer control is conditional on a specific new ambiguity, not an automatic sweep.
The existing three/five-interval policy remains the engine study limit.

## Latest assignment: functional work proceeds independently

The user assigned the sustained-wave investigation to a separate chat. C6a is a
functional initializer, persistence and bounded cost/validity check, not a
survival test. It does not decide that RDE-001 is fixed. See the
[C6a implementation and test review](../verification/c6a_functional_pipeline.md).
F1 saved-window reporting is now implemented; see its [accounting review and
results](../verification/f1_window_reporting.md). F2 contracts, F3 optional drag/torque and F4 saved-data workflow are implemented; see the [completion matrix](2d_workflow_completion.md) and [final acceptance](../verification/f4_workflow_completion.md).
The separate study owns any C6 propagation experiment; preserve the three/five
interval limits when that experiment is selected. No automatic longer layer
control, integrator rewrite, chemistry change or parameter sweep is authorized
by a passing benchmark. This assignment supersedes the earlier next-study
suggestions above without deleting their evidence or qualifications.
