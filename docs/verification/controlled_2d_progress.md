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
