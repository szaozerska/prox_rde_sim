# F3: optional adiabatic wall friction and qualified engine torque

The default remains inviscid. To select the new model, set `model.walls:
constant_cf` and an explicit nonnegative `model.wall_cf`. There is no fitted or
implicitly enabled coefficient. A nonzero coefficient with `inviscid` is rejected.

For the plan's convention `tau = 0.5 Cf rho |u|²` and lateral wall area per volume
`2/g`, the cell momentum source is `S_m = -(Cf/g) rho |u| u`, for both resolved
velocity components. Density, reacted mass and total energy have no wall source.
Resolved kinetic energy lost to stationary adiabatic friction becomes internal
energy. Heat loss and injector-face shear are not included.

The source is evaluated at both existing SSP-RK2 stages, and its actual weighted
integral is saved with the native budgets. A separate `dt <= 0.1/max(Cf |u|/g)`
cap resolves drag decay. This is not a new chemistry integrator. An explicit zero
coefficient executes the same arithmetic path as the existing inviscid solver.

Engine torque in the reduced model is `-r_mean * integrated gas theta source /
duration`. The window report independently compares it with angular influx minus
outflux minus angular storage. These estimates describe the same torque and
must not be added. The summary's mean covers the whole saved duration; use an
explicit window report for other averages. Checkpoints retain source accumulators
and reproduce uninterrupted replay exactly.

## Limits, including the independent report's radial discussion

This is a mean-radius, gap-averaged closure, **not the full proposed 2.5D tier**.
No radial momentum, radial velocity, centrifugal pressure split, curvature-loss
model, heat loss or distinct inner/outer wall states has been added. Cylindrical
plots add no physics. Torque magnitudes are not calibrated against Mundt or Sawada.

The model uses `r_mean` consistently for both angular inventory and torque.
For equal physical shear on two walls, the exact traction moment divided by this
mean-radius estimate is `(r_o²+r_i²)/(2 r_mean²) = 1+(g/(2 r_mean))²`.
We do not apply that correction to only one side of the reduced angular balance:
that would make the inventory/torque approximations inconsistent. Distinct wall
states and full radial moments belong to a separately derived extension.

## Reviews and tests

1. Sign and factor review: the two-wall `2/g` cancels the stress convention's
   factor of 1/2; the engine receives the opposite torque to the gas source.
2. Energy review: friction is not an energy sink in this stationary adiabatic
   closure. Exact uniform-flow decay gives `u(t)=u0/(1+Cf |u0| t/g)` and a pressure
   rise equal to `(gamma-1)` times the lost kinetic-energy density.
3. Accounting review: compare independently integrated face fluxes and inventory
   storage, test reversal and zero-Cf equivalence, then replay saved step durations
   across a restart. Do not infer torque from exit swirl alone.

All seven focused tests passed. They check the exact decay/heating relation,
second-order time refinement, coefficient sensitivity, sign reversal, both
momentum components, decay cap, invalid coefficients, bitwise zero-Cf baseline,
and saved-run/restart/angular balance. Full F3 regression: **109 passed, one opt-in skipped**, in 406.818 s on the shared host. It excludes the separately
in-progress F4 analysis tests; see [f3_tests.txt](f3_tests.txt) and
[f3_wall_tests.txt](f3_wall_tests.txt). The long reactive baseline remains for final
workflow acceptance. These are numerical/implementation checks, not torque validation.

No Run 937 propagation or parameter-tuning campaign was launched. Source changes
require the original revision/environment to resume older checkpoints; read-only
analysis of their version-2 native data remains supported.
