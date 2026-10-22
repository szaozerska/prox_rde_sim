# Radial-wall closure verification and controlled engine experiment

Implementation complete; long comparison running. RDE-001 remains OPEN. No CAD.
The [reviewed plan](../plans/radial_closures_2d.md) records three reviews, equations,
assumptions, literature and the omitted radial dynamics/curvature calibration.

## Verification before engine comparison

- Full acceptance: **130 tests passed, zero skips**, 301.054 s, including the
  opt-in inherited reactive propagation case. Log: `radial_full_tests.txt`.
- Final focused run: **10 passed**, 12.220 s. Includes eight radial physics/I/O
  tests, one wave-diagnostic test and expanded import isolation. Two are newly
  added after full-suite discovery: **132 distinct tests passed** in total.
- Independent checks: volume-weighted radial-pressure quadrature and derivative;
  thin-gap and zero-swirl limits; zero-loss bitwise equivalence to the original
  solver; reduction to the previous two-wall drag law; a coupled full-energy,
  drag, cooling and reacting ODE with independent radial quadrature; second-order
  timestep convergence; heat-flow sign reversal; adiabatic energy conservation;
  stiff-source step limiting; separate wall budgets, actual-radius traction
  geometry, strict parameter/field validation and exact checkpoint replay.
- Initial ODE test at a finest 0.25 us timestep had normalized error 2.81445e-7,
  exceeding its 2e-7 threshold. Refining all three timesteps by two satisfied the
  unchanged threshold and convergence-ratio checks. This was resolved by measured
  temporal refinement, not by loosening the tolerance or changing chemistry.
  The initial log is retained as `radial_initial_tests.txt`.
- Short radial engine benchmark: 2 us, 139 steps, no invalid states, completed.
  Elapsed 43.987 s includes compilation and concurrent acceptance testing; it is
  not a clean steady-state throughput measurement. This benchmark is not a
  sustained-wave result. Its saved source predates the final summary wording fix;
  the two long comparison runs use identical final source fingerprints.

## Construction and accounting review

Use local **gas tangential velocity**, not detonation-wave speed, in centrifugal
balance. The reconstructed pressure and density preserve their annular means.
Uniform temperature/velocity/composition and instantaneous radial equilibration
are closure assumptions. Transport remains on the mean-radius (theta,z) surface;
no radial acceleration/reflection, boundary layer or inner-wall detachment evolves.
The injector continues to see the mean pressure; separate radial jet coupling is
not claimed. All coefficients and temperatures are saved explicitly.

Stationary adiabatic drag has no total-energy sink. Heat exchange uses recovery
enthalpy and retains either sign. The new source is summed into the native RK
energy budget separately from chemical conversion. Independent per-wall RK
integrals survive restart. The actual-radius traction moment is available as a
separate reconstruction; it must not replace the mean-radius moment in the
solver's angular inventory/balance. No friction or heat fit to Run 937 is claimed.

## Controlled experiment (results pending)

Original D1 physical geometry, equivalent feed, original 1 mm half-reaction length,
0.5 mm grid, 3.8 mm fill and original hot patch are fixed. No ignition or chemical
retuning. Both new cases use Cf_i=Cf_o=0.005, Tw_i=Tw_o=300 K, analogy=1,
recovery=0.9, chosen before the results. Compare:

1. Historical inviscid D1: context, different implementation provenance retained.
2. `run937_wall_control.yaml`: per-wall drag/heat with centrifugal reconstruction off.
3. `run937_radial.yaml`: identical settings, centrifugal reconstruction on.

Only cases 2 and 3 are a current-source matched intervention pair. Both run the
original three-reference-interval duration, 189.394 us; the reference frequency
sets only duration, never imposes actual wave count. Native states are local in
`rde_sim_starter/runs/radial_wall_control` and `radial_active`.

Read-only `radial_study.py` retains absolute reaction magnitudes, pressure contrast,
pressure-face to half-peak reaction distance at two axial stations, common-scale
space-time plots, final reconstructed wall pressures, configuration differences,
implementation hashes and native window budgets. Distance alone is not proof of
shock/reaction coupling, especially when the absolute reaction signal vanishes.
A failed coarse case cannot establish that radial physics is irrelevant or that
no 2D model can sustain a wave. No outcome is asserted before inspection.
