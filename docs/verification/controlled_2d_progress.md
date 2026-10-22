# Controlled 2D investigation: decisions and results

October 22, 2026. Branch: **main**. [Execution plan and three review passes](../plans/controlled_2d_tests.md).
RDE-001 remains open. Independent 3D work belongs to the other session/checkout.

## Publication baseline

- Published existing D3 reference/contact/refinement implementation and evidence,
  paper/model audit and the external-diagnostic assessment; no new physical claim.
- Plan review 1 inserted formed-profile verification before layered propagation.
- Review 2 controlled cell-average inventory, frozen chemistry and boundary causality.
- Review 3 reduced case count, separated fast tests from explicit diagnostics,
  specified combined pressure/reaction evidence and clarified main-only ownership.
- Default suite: 59 tests in 188.374 s, 58 passed and the opt-in 95 µs propagation
  test skipped. See [log](prepublication_tests.log). D3's earlier full 59-test
  result including that propagation case remains in its separate report/log.
- No production solver, chemistry or Run 937 calibration changes in this publication.
- Next: C1 multirow/directional control. No new engine run or detonationFoam install.

## C1 — multirow and direction control: passed

- Added `controlled.py strip`: closed 1D, eight-row horizontal strip, rotated
  eight-column strip, and the original open-ended 1D case. Same chemistry,
  0.5 mm spacing, source fraction 0.05 and identical accepted timesteps.
- The 95 µs run used 6574 steps and 42.406 s wall time. At every saved 5 µs
  snapshot (plus endpoints), all five primitive fields and front positions
  matched exactly, including the open-ended control. No transverse variation.
- All pressure-threshold fits over 40–95 µs gave 2455.944 m/s. Maximum scaled
  conservation residual was 3.950e-15; all four cases had zero invalid states.
- This excludes row-count/coordinate-path discrepancies exercised here. It
  neither validates nonuniform transverse dynamics nor explains layer extinction.
  Pressure-threshold motion alone is not a detonation classifier. No production
  solver, calibration or engine input was changed.
- Fast regression includes nonzero swapped momentum, reactive multistep symmetry,
  budgets, input preservation and saved-data-only plotting. Default suite: 61
  tests in 66.787 s, 60 passed and one opt-in propagation test skipped. The
  separate full C1 run supplies propagation evidence.
- Evidence: [metrics](c1_strip_metrics.json), [inputs/hashes](c1_strip_inputs.json),
  [figure](c1_strip_control.png), [test log](c1_tests.log). Native fields are in
  ignored `rde_sim_starter/runs/c1_strip/`; figures use only these saved fields.
- Review at this gate: no C1 critical inconsistency. Grid/source accuracy and
  finite-layer physics remain open; next is C2 conservative formed-profile
  construction, independent jump/inventory checks and fully filled propagation.

## C2 — conservative formed profile and filled strip: passed for the bounded control

- Constructed the current strong-branch CJ/ZND solution in the lab frame
  (`u = D_CJ - u_shock`), retaining chemical energy in total energy. The profile
  ends at progress 0.999999 and then joins the fully reacted CJ state; its finite
  tail is 23.768 mm, with a 0.09646% pressure jump at the truncation.
- Independent mass/momentum/total-enthalpy identities have maximum relative
  errors below 7e-13. Adaptive distance integration uses log remaining reactant
  to avoid the singular endpoint; independent quadrature recovers the 1.000,
  3.140 and 4.177 mm half/90%/95% reaction distances.
- First implementation issue: subtracting large conserved-antiderivative
  contributions produced progress 1+6e-14 in fully burned cells and correctly
  triggered state rejection. Root cause was cancellation in conserved-integral
  subtraction. Fixed by splitting the exactly constant fresh/burned regions
  before integration, without clipping progress or weakening state checks.
  (The integrated quantities are conserved variables, not primitive averages.)
- First table review: 1201 nodes differed from 2401 by 1.46e-4 of physical
  scales, exceeding the preselected 1e-4 tolerance. Increased to 2401 nodes;
  the independent 4801-node comparison passes. Tests check arbitrary shock/cell
  intersections against quadrature and invariant integrated inventory across
  0.5/0.25/0.125 mm cells. No chemistry tuning.
- Unforced, transversely uniform strips propagated for 40 µs at all three
  spacings. The 20–40 µs pressure-threshold fits are 2478.153, 2472.973 and
  2472.072 m/s against the surrogate CJ speed 2471 m/s. Cell-quantized fronts
  make the shortest fit window noisier; this is not a formal convergence order.
- Final near-front peak rates are 0.276/0.273/0.261 per µs, with pressure-to-rate
  peak separations 1.50/0.75/0.875 mm. Peak pressures are 19.26/20.10/20.64 MPa.
  Saved profiles show continued attached reaction, not just a moving pressure
  pulse. Uniform transverse invariance remains exact. Eight rows are used on
  each mesh, so transverse width changes; this is a uniform-strip control and
  inventories are compared per transverse area, not as equal total charge.
- Halving source fraction from 0.05 to 0.025 at 0.5 mm preserves all sampled
  front positions. Across saved fields the maximum scaled density/pressure
  differences are 0.00384/0.00184, and chemical conversion changes by 0.00301%.
  This supports the selected step for this control, not arbitrary new chemistry.
- No invalid states. Maximum normalized native-budget residual across all four
  runs is 1.95e-14. The predeclared 4000 m/s axial characteristic bound is checked
  against intermediate and accepted states; observed maxima are below 3185 m/s.
  At 40 µs the reaction region remains >69 mm from the left causal bound and
  the front >30 mm from the right bound. Open left-boundary mass inflow exists,
  but its physical signal cannot reach the measured front/reaction region in
  this window. The bound is a characteristic check, not a proof of zero
  floating-point influence through the numerical stencil. No imposed driver.
- Runs took 9.0/16.9/48.8/20.7 s. [Metrics, native budgets, hashes and histories](c2_formed_metrics.json);
  [saved-field figure](c2_formed_control.png); [test log](c2_tests.log). Native
  fields remain in ignored `rde_sim_starter/runs/c2_formed_*`.
- Paper consistency: this verifies the declared surrogate, not Mundt's physical
  chemistry or Run 937. The paper's physical lengths, separate injection and
  real pre-detonator remain distinct (audit §§2–5). Layer-control precedent
  motivates the test, but supplies no transferable critical-height threshold.
- Default suite: 64 tests in 31.349 s; 63 passed, one opt-in propagation test
  skipped. Four explicit C2 runs provide the separate propagation evidence.
- Gate review: no critical initializer/filled-strip inconsistency remains. C3
  may now test 3.8 and 15 mm layers; no engine run or C4 initiation claim yet.

## C3a — coarse finite-layer comparison: completed, refinement gate still open

- Added exact conservative area fractions for a formed wave in a 3.8 or 15 mm
  layer, with 1500 K, p1, fully reacted gas above it. The bottom is reflecting;
  top is remote/reflecting, axial ends transmissive. No injector, outlet-pressure
  closure, imposed driver, or engine geometry change is used. Same local formed
  profile in both layers; integrated initial charge/energy scale with layer height.
- Unit checks preserve the integrated layer volume, all five conserved totals
  and initialization excess across 0.5/0.25/0.125 mm grids. This removes the old
  cell-center inventory confound, not numerical contact diffusion. The 3.8 mm
  interface cuts one row. The saved 15 mm `mixed_row_count=1` is a floating-point
  edge classification (fraction differs from one only by roundoff); geometrically
  that interface lies on a face. No state clipping is applied.
- Both 0.5 mm cases completed 40 µs / 2771 steps. Wall times were 320.8/386.0 s.
  No invalid states; budget residuals <4.7e-16 / 1.1e-15. Actual characteristic
  maxima remain below the predeclared 4000/3000 m/s axial/transverse bounds.
  All sampled front/reaction regions remain outside remote-boundary cones; the
  conservative top margin is 10 mm at 40 µs.
- **3.8 mm:** the leading pressure front and main reaction separate. The gap
  grows from about 1 mm early to 20–25 mm by 32 µs; at 40 µs the strongest
  reaction is about 26–30 mm behind the tracked fronts (the 30 mm search window
  limits the upper-row value). Wall pressure falls to 2.74 MPa. The wall-row
  peak rate within 2 mm behind the leading front falls from ~2.57e5/s initially
  to ~10/s at 40 µs. A strong detached reaction/contact structure remains, so
  this is loss of leading shock/reaction coupling, not cessation of all burning.
- **15 mm:** strong shock-associated reaction remains near the wall and middle
  at 40 µs, with pressure/rate peak separations 1.5/2 mm and rates 2.83e5/1.86e5/s.
  Upper-layer response is more disrupted (6 mm separation). A transient wall
  pressure peak of 32.33 MPa indicates transverse dynamics; it is not a steady
  pressure target. Inspect the fields and histories, not one peak or fit.
- [Native metrics, provenance and near-front postprocessing](c3_layer_coarse_metrics.json);
  [3.8 mm fields](c3_layer_038_coarse.png); [15 mm fields](c3_layer_150_coarse.png).
  Figures were inspected. Native fields are in ignored `runs/c3_layer_*_050/`.
- Literature/physics review: this conditional difference is consistent with
  yielding-confinement effects studied by [Li, Mi and Higgins](https://arxiv.org/abs/1405.7753),
  whose reaction law differs. It does not transfer their critical dimensions or
  prove a Run 937 extinction threshold. Mundt's 3.8 mm refill estimate is not a
  measured startup layer, and the paper does not validate this thickened chemistry.
- Numerical review: heat release along the hot/fresh interface exists ahead of
  the main wave; numerical mixing remains a candidate contributor. The saved
  `layer_heat` diagnostic uses row centers, while initial inventories and native
  budgets use conservative integrals. Do not treat that row-center diagnostic
  as an exact integral below a cut interface.
- Default suite: 67 tests in 52.304 s, 66 passed and one opt-in skipped, including
  the short 2D driver/budget check and saved-field-only rendering. [Log](c3_tests.log).
- **Gate decision:** repeat these two decisive cases at 0.25 mm with identical
  chemistry, physical domain, initial conserved charge and duration. Those runs
  are underway. C3 is not yet closed; no formal critical-height bracket, stable
  rotating wave, chemistry change or C4 initiation conclusion is claimed.

### Cross-document consistency review

Updated the open issue, handoff and starter status to remove stale claims that
the C1/C2 controls and coarse layer comparison had not been run. Added direct
CLI reproduction commands. This documentation-only synchronization changes no
inputs or source; the 67-test result above remains applicable. Refinement is
still in progress and RDE-001 remains open.

### C3 initial-interface audit and verifiable correction

The [initialization audit](c3_interface_initialization.json) confirms conserved
charge matches across grids to roundoff, but the thin layer's cut-cell
temperature/rate changes from 435.36 K / 2.315 s^-1 to 843.99 K / 1127.47 s^-1.
That sensitivity prevents treating equal inventory as equal local ignition
conditions. No changes were made to the running refinement cases.

Added explicit `--align-interface` to the layer diagnostic. Its nested vertical
mesh puts the interface on a face, with the same fresh-layer height and formed
wave excess charge. The small additional remote product buffer is recorded and
its contribution to total conserved inventory is independently checked. No
clipping, source suppression, solver change or chemistry tuning is involved.
Nine targeted control tests passed in 21.761 s, including aligned-interface
purity and inventory checks across three meshes; [log](c3_alignment_tests.log).
The bounded aligned run is still pending. The execution plan records the
vertical-spacing qualification and keeps C4 gated on the combined C3 evidence.

Resource decision: this Mac has four physical CPU cores. The 15 mm fine run was
temporarily stopped without discarding state to let the thin fine run finish;
it must be resumed. Its native scheduling record will accompany its eventual
results. Wall times from overlapping/paused runs are not clean performance data.

### C3b — 3.8 mm refinement completed

At 0.25 mm the thin layer again loses leading shock/reaction coupling by 40 µs.
The wall-row pressure maximum is 2.76 MPa, versus 2.74 MPa at 0.5 mm. The
24–40 µs front fit is 1296.875 m/s versus 1337.5 m/s; wall-to-global-reaction
peak separation is 25.75 versus 26 mm. Peak reaction within the inclusive
2 mm window behind the leading wall front is 6.13/s versus 9.95/s, while
the detached main reaction remains about 1e5/s. Refinement does not rescue
this formed thin-layer case. Integrated chemical conversion falls from 3546.17
to 2994.50 J per metre of depth (15.6%); this is qualitative agreement in
coupling loss, not full convergence of the reacting flow.

The upper-row global reaction peak lies 31.5 mm behind its front, outside the
30 mm search window. The saved local-search metric consequently jumps to a
weaker secondary structure at 13.75 mm; that is **not** recoupling. This was
resolved by inspecting full fields and calculating global as well as local
reaction maxima. Probe centers differ slightly between meshes; do not infer
a convergence order from the row-specific values.

The run completed 2771 steps, zero invalid states, maximum normalized budget
residual 1.23e-15 and positive boundary-cone margins. Integrated initial conserved
quantities match the coarse case to roundoff. [Native/derived metrics](c3_layer_038_refined_metrics.json),
[inspected figure](c3_layer_038_refined.png). Its source hash matches commit
`83dd544`; it was not changed by the later alignment helper. No source or
chemistry change was made for this refinement, so prior tests remain applicable.

The thick refinement has been resumed after the recorded scheduling pause.
The extra aligned thin control is running with one Numba thread while the
thick refinement uses two. C3's combined gate and C4 remain pending. The
2449 s elapsed thin-run time includes contention; it is not a clean benchmark.

### C3c — aligned thin layer completed; initial cut cell is not sufficient explanation

The face-aligned 3.8 mm control completed 40 µs with zero invalid states and
maximum normalized budget residual 5.19e-16. It also loses leading coupling:
wall-row pressure 2.741 MPa, 24–40 µs front fit 1306.25 m/s, 25.5 mm gap to
the global reaction maximum, and only 13.23/s peak rate in the inclusive 2 mm
front window. This closely resembles the original and refined thin outcomes.
Removing the initial mixed row does not rescue the formed wave. Subsequent
HLL contact mixing remains present, so this does not exclude numerical mixing
or validate physical kinetics. The vertical-spacing/remote-buffer qualification
is retained. [Metrics](c3_aligned_metrics.json), [inspected figure](c3_aligned.png).

### C3d — refined thick run stopped at a diagnostic bound; corrected before C4

- The 0.25 mm, 15 mm layer reached 23.555864 µs / 1631 steps. Its observed
  transverse characteristic speed reached 3000.020623 m/s, just above the
  predeclared 3000 m/s bound; the driver correctly stopped. This was not a
  negative/invalid state or an observed detonation failure. Wall/middle reaction
  remained near the fronts. Native budget residual stayed <1.30e-15.
- Root cause of this stop: the coarse-derived travel-speed allowance was too
  small for the refined transverse dynamics. This is a diagnostic-domain
  assumption to correct, not evidence of accumulated conservation error or a
  missing 3D mechanism. The failed assumption and original run are preserved
  in [stopped metrics](c3_thick_stopped_metrics.json).
- All five primitive variables in the top four rows were exactly unchanged
  at every saved time. Replacing the bound with 3200 m/s gives a 54.62 mm top
  margin at the stop and 2 mm at 40 µs; axial bounds/margins are unchanged.
  This revised bound is declared before continuation and remains checked at
  every intermediate/accepted step. It changes neither fluxes, source terms,
  timestep limits nor the physical boundary condition. Stop again if exceeded.
- Added narrow layer continuation with case/calibration/numerical-fingerprint
  checks, preserved fields/history/native flux and source totals, and exact
  conserved-state checkpoints for new runs. The older C3 file stores float64
  primitives; its conserved state is reconstructed through the unchanged EOS,
  without clipping. Actual restored integrated totals match the saved totals
  exactly in all five components. [Audit](c3_thick_continuation_audit.json).
- Twelve targeted tests passed in 17.890 s, including exact checkpoint recovery,
  legacy per-cell roundtrip/next-step equivalence, invariant old field history,
  continuation budgets, changed-calibration rejection and travel-bound rejection.
  [Log](controlled_continuation_tests.log). The original report/data remain
  immutable; continuation writes `runs/c3_layer_150_025_continued/`. Its prefix
  causal margins are recomputed under the new, more conservative speed bound.
- C3 remains open until the continued run reaches the agreed window or a new
  critical inconsistency is assessed. C4 has not been launched as a full study.

### C4 software preparation while C3 runs

Implemented the explicit blast comparator with conservative 10 mm patch / 20 mm
product-strip geometry, 2×CJ pressure, CJ temperature and zero momentum, matching
the existing engine-start constants. Independent box integrals check its
initial inventory on three grids. Short source/flow, budget and saved-only
rendering checks pass as part of the 12-test control set above. This is software
readiness, not a C4 physical result. A hotter blast has larger declared travel
bounds: 5000/3500 m/s, with a 550 mm axial domain, initial front at 200 mm and
150 mm of products above the layer. Compare displacement from the respective
initial front. Boundary types/medium stay the same; the larger remote domain
keeps the intended comparison outside boundary influence. The plan records
these choices before the conditional full run.

## C3e — refined thick endpoint and combined gate: bounded contrast verified

- The checked 15 mm continuation completed 40 µs / 2771 total steps. No invalid
  states; maximum native-budget residual 1.295e-15. Observed characteristic
  maxima 3576.17/3099.16 m/s stay below the declared 4000/3200 m/s bounds.
  Final left/reaction, right and top margins are 57.375, 39.625 and 2 mm.
  The top four rows retain initial density, pressure, transverse velocity and
  progress exactly; axial velocity differs only by 8.7e-281 m/s. This is a
  consistency check alongside the finite-speed bound, not a new boundary model.
- All saved prefix fields/times are bit-for-bit equal to the original stopped
  run. Its 3000 m/s bound failure remains preserved. Budgets include the full
  original trajectory; continuation did not reset time, source or boundary flux.
- At 40 µs, wall/middle global rate peaks are 0.75/1.75 mm behind the leading
  pressure fronts, at 2.77e5/1.73e5 s^-1. Wall pressure is 27.43 MPa. The upper
  row is less tightly coupled (8 mm peak separation); the field shows transverse
  structure. Late 24–40 µs wall/middle/upper pressure-front fits are
  1862.5/2000.0/2206.25 m/s. These are threshold tracks, not steady detonation
  speeds or experimental matches. No arbitrary fit to Mundt's velocity is made.
- Combined with the 0.5 mm result, this verifies **qualitatively different
  bounded responses** at 3.8 and 15 mm under this surrogate. The refined and
  face-aligned thin controls also lose coupling. This is not a converged critical
  height, proof of indefinite thick-layer survival, or proof that initial formed
  charge has ceased influencing the transient. Numerical contact burning remains
  visible; the thin conversion integral still changes by 15.6% on refinement.
- [Metrics/provenance](c3_thick_refined_metrics.json), [inspected figure](c3_thick_refined.png),
  and ignored native `runs/c3_layer_150_025_continued/` preserve the evidence.
  The full suite, including opt-in 95 µs reactive baseline, passed **71/71** in
  185.552 s; [log](controlled_full_tests.log). No production numerics changed.
- **Gate:** C3 is sufficient for the narrowly conditional C4 comparison at
  15 mm. Run one 0.5 mm blast comparator through 40 µs, with its already declared
  remote-domain margins. Compare shock/reaction fields, displacement relative to
  initial front, budgets and unequal initialization inventories. Do not rerun the
  engine or change chemistry from this result alone.

## C4 — specified blast versus formed start at 15 mm: completed, long-term outcome unresolved

- The 0.5 mm blast control completed 40 µs / 2771 steps in 1082.6 s under
  concurrent test load. No invalid states; maximum native-budget residual
  4.48e-16. Axial/transverse characteristic maxima 3122.33/3122.31 m/s remain
  below 5000/3500 m/s. Final observation margins: 35.75 mm left/reaction,
  82.25 mm right and 10 mm top. Top pressure/density/progress/normal velocity
  remain unchanged; axial velocity differs by only 1.9e-209 m/s.
- Strong reaction remains behind the advancing right-going front, but the blast
  response is weaker than the formed controls: at 40 µs wall/middle pressure
  maxima are 6.53/6.47 MPa; rate peaks are 1.28e5/1.32e5 s^-1, 4 mm behind
  their pressure fronts. Rates within 2 mm are 2.20e4/1.95e4 s^-1. Late
  wall/middle pressure-front fits are 1587.5/1650 m/s (upper row 1962.5 m/s).
  Wall pressure and near-front reaction weaken late in the window. Do not label
  this either a settled detonation or completed extinction from 40 µs alone.
- The intended clean contrast, "formed persists but blast has no continuing
  shock-associated reaction", was **not established**. The blast does produce
  continuing nearby reaction in this thick layer. This does not verify the
  original 3.8 mm engine startup or eliminate an initiation limitation there.
  C3 independently shows thin-layer loss even from a formed start, so changing
  only the igniter is not a demonstrated solution to the engine problem.
- Initial excess total energy above each unignited medium is 69,310.06 J/m
  depth for the formed case versus 3,756.94 J/m for the blast; axial momentum
  is 19.427 versus zero in per-depth units. The long initial formed product
  column matters; no equal-energy or critical-ignition-energy claim is made.
  The blast also launches a left-going disturbance. Total conversion is not a
  directly matched measure of forward-wave yield.
- Added saved-data `plot.py --layer-comparison ... --out NEW`: front displacement,
  reaction separation, front-relative pressure and a 2 mm near-front rate. The
  reaction search retains the initial shock minus 30 mm as a fixed lower edge,
  so it excludes the departing reverse wave without moving a narrow window past
  detached reaction. Always cross-check full fields. Zero rates are omitted on
  the logarithmic line plot, not assigned an artificial rate.
- A synthetic stronger reverse-wave signal tests that this selection cannot
  silently substitute the opposite wave. Rendering is tested with solver
  stepping disabled and unchanged source fields; mismatched chemistry is rejected.
  Twelve controlled tests passed in 40.947 s. One final rendering check passed
  after improving the zero-rate display. [Logs](c4_plot_tests.log).
  An initial test command ran from the repository root and could not import
  `plot`; rerunning from the documented `rde_sim_starter/` directory resolved
  that invocation error without changing import behavior.
- [Metrics/provenance](c4_blast_metrics.json), [inspected fields](c4_blast.png),
  [direct comparison](c4_comparison.png). Ignored native data and exact checkpoint
  are in `runs/c4_blast_150_050/`. No production chemistry/engine input changed.
- **Decision:** finish this bounded comparison without claiming long-term
  initiation success/failure or adding a blind refinement/long-run campaign.
  Review the model/source/resolution gate in C5 before selecting an engine
  change. The existing paper audit and physical-reference discrepancies remain
  applicable; neither 15 mm startup nor these artificial kinetics are validated
  by Mundt's operating refill-height estimate.

## C5a — physical-model/source/mesh feasibility review: completed; C6 blocked by readiness gate

- Added a small, saved-evidence-only `model_audit.py`; it neither runs CFD nor
  changes calibration. Rate-only changes cannot match the physical 50/90/95%
  distances simultaneously: the required factors are 25.302/69.265/81.772.
- A bounded algebraic Ea/k fit to physical 50%/95% distances (current EOS fixed)
  yields Ea/(R T1)=71.61489, k=2.17877e10/s. It is explicitly **not adopted**.
  Held-out 90% distance error is +6.29%; CJ thermodynamics remain unchanged.
  Physical 50%/95% lengths span only 0.079/0.102 of a nominal 0.5 mm cell.
  The current sufficient global source cap would be 2.079 ps, at least 91.09
  million source-limited steps over three reference intervals. This is a cap/
  resolution feasibility result, not a measured runtime or proof that chemistry
  inherently needs that timestep. Tight quadrature changes results by <2.1e-11.
- [Readiness review and next small gates](c5_model_readiness.md) combine resolution,
  accumulation, initial/dynamic mixing, boundary and model evidence. The paper
  does not validate the thickened one-step model, and C3/C4 do not uniquely
  identify the complete engine root cause. The physical-reference CJ discrepancy
  and EOS mismatch remain explicit.
- **Decision:** no unsupported engine model change is promoted and C6 is not
  launched. The next work must select a documented reaction-model hypothesis,
  verify an affordable source treatment and resolved local controls, then revisit
  the thin layer. Arbitrary fill/ignition increases or rate tuning would bypass
  the inconsistency instead of resolving it. detonationFoam is not needed for
  the completed controls; any future backend choice follows a small benchmark.
- Two audit tests passed in 1.833 s; strict independent quadrature audit passed.
  The full suite passed **73/73 in 203.681 s**, including the opt-in reactive
  baseline and side-effect-free imports. [Log](c5_tests.log). Final plotting-only
  refinements then passed the controlled 12-test set and one last display check
  as recorded under C4. Production solver/physics/engine/calibration/config remain
  unchanged; existing D1/D2 numerical checkpoints keep their fingerprint.
- The current status, handoff, issue and master/controlled plans now agree on
  completed C1–C4, completed C5a assessment, and the open C5 model-readiness gate.
  Every completed increment is committed/pushed to main; the 3D branch is untouched.
