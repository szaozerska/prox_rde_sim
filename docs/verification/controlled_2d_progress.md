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
