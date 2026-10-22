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
