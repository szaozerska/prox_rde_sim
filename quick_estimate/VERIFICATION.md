# Quick-estimate implementation verification

2026-10-24. Branch `2d-quick-estimate`, based on fetched GitHub main `73d4516`.
Original dirty main checkout preserved; no CFD jobs launched.

1. Initial implementation: 10 focused tests passed in 0.184 s.
2. Added primary-paper table comparison: failed on the lower endpoint
   (calculated 0.12785 versus printed 0.18). Inspected the PDF table visually;
   retained the mismatch in `examples/paper_table_comparison.json` and THEORY.md.
   Upper endpoint 0.75407 agrees with printed 0.75. No fitted correction.
3. Final 11 checks cover implementation consistency and explicitly retain that
   unresolved physical-reference discrepancy. See the saved test log.
4. CLI examples saved with input/model hashes and complete formula traces:
   synthetic: nominal [2], possible [2,3,4], continuous capacity 2.4;
   Law design point: no candidate, continuous capacity approximately 0.409.
5. `git diff --check` passed.

The synthetic case is not an engine validation. The paper example is a design
assumption calculation, not the actual state of a measured successful run.
No numerical convergence study applies to these closed-form expressions.
