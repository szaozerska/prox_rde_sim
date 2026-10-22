# Reduced annular closures after completion of the 2D workflow

Status: implementation, acceptance and matched engine comparison complete.
The original case still does not sustain rotating detonation through 189.394 us;
RDE-001 remains open. Main branch only; no CAD. Functional F1–F4
completed at b26ec9e. RDE-001 remains open. This is the user's requested follow-on
experiment, not a claim that the surface solver now resolves radial dynamics.

## Scope and equations

The independent `detonation_issue_investigation.md`, sections 10 and 13–14,
proposes per-wall friction, heat transfer and centrifugal pressure reconstruction.
Its statement that friction is unimplemented predates F3. Its curvature-loss and
inner-wall detachment proposals require radial calculations/calibration absent
here; neither gets an invented coefficient.

1. Retain the five mean-radius conserved variables and all original defaults.
   Add an opt-in `annular_closure` wall model with explicit inner/outer Cf,
   temperatures, Reynolds-analogy factor, recovery factor and centrifugal switch.
2. Reconstruct radial equilibrium, dp/dr = rho u_theta^2/r, assuming uniform
   temperature, composition and tangential/axial velocity through the gap:
   p(r) proportional to r^beta, beta = u_theta^2/(R T). Normalize by the exact
   annulus-volume mean so both mean pressure and mean density are preserved.
   This positive isothermal extension reduces to the report's thin-gap split.
   It is a quasi-steady closure, not a radial momentum equation. Never add a
   centrifugal force to circumferential momentum.
3. Per-wall source area/volume a_w = 2 r_w/(ro^2-ri^2). Drag =
   -a_w rho_w Cf_w |U| U/2. Adiabatic drag removes momentum with zero total-energy
   sink (kinetic energy becomes thermal). Optional heat exchange uses
   St_w = analogy_factor Cf_w/2 and q_w = rho_w |U| St_w cp (T_aw - T_wall),
   T_aw = T + recovery_factor |U|^2/(2 cp). Total-energy source = -sum(a_w q_w).
   Sign is retained for hot walls; never clamp heating away. No chemical-energy
   double counting. Explicit source timestep limit supplements existing caps.
4. Persist independent per-wall RK integrals and reconstructed pressures. Preserve
   mean-radius torque consistent with the solver's angular inventory; report the
   separate actual-radius traction moment with an explicit finite-gap qualification.
5. Test short analytic/quadrature/ODE cases and restart/budget/report integration.
   Then compare original D1 initialization/chemistry/grid with and without these
   closures, including a centrifugal-off case with identical wall coefficients.
   Benchmark before committing to full 189.394 us runs; do not change reference
   frequency to obtain a convenient runtime. Preserve all case inputs and evidence.

## Three pre-implementation reviews

Review 1 — physical construction: the report's linear pbar +/- split may become
negative and is not exactly volume-normalized in a finite annulus. Use the derived
isothermal positive profile and numerical-quadrature tests. It still assumes
instantaneous radial equilibration and cannot predict detachment. Geometry and
separate-jet/outlet/startup mismatches with Mundt Run 937 are unchanged.

Review 2 — energy and torque: static-temperature Reynolds analogy would omit
compressible recovery heating. Use explicit recovery temperature. Distinguish
actual-radius traction moment from the mean-radius angular conservation budget;
do not silently replace one with the other. Track heat separately from chemical
conversion. Test both positive and negative heat exchange and drag-only energy.

Review 3 — identifiability and cost: turning on friction, cooling and centrifugal
reconstruction together would confound attribution. Use matched centrifugal-off/on
wall cases plus the original inviscid baseline. Cf=0.005 per wall, analogy factor=1,
recovery factor=0.9 and Tw=300 K are declared exploratory assumptions, chosen
before results, not Run 937 fits. Include a short half/double coefficient check if
wall losses materially dominate; do not tune for a desired sustained wave.
Pressure peaks alone are not detonation: inspect shock/reaction proximity, pressure
and reaction space-time traces, source budgets, positivity, and late-time behavior.
A coarse-grid negative result applies to this case, not all 2D or radial models.

## Sources and limits

- Local independent report, sections 10 and 13–14; source paper geometry and
  Run 937 values remain the audited configuration in `rde_sim_starter/config.yaml`.
- [NASA TN D-5560](https://ntrs.nasa.gov/api/citations/19700006441/downloads/19700006441.pdf):
  Stanton number uses adiabatic-wall minus wall enthalpy. Reynolds analogy has
  restricted empirical validity; its use in this unsteady detonation is assumed.
- [NETL methane/oxygen RDE CFD validation](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf):
  fixed 300 K walls are a modeling precedent in a different calculation, not a
  measurement of Run 937 wall temperature or calibration of our coefficients.

Deferred deliberately: injector-face shear (not a radial-wall term), empirical
curvature loss, resolved radial motion, wall boundary-layer history, wall thermal
conduction, separate jet mixing and all CAD work. A report/viewer is not validation.

Verification and results: [radial closure record](../verification/radial_closures.md).
