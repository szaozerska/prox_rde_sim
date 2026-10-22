# Radial-wall closure verification and controlled engine experiment

**Completed: the requested reduced radial closures did not restore sustained
rotating detonation in the original D1-style case through 189.394 us.** RDE-001
remains OPEN. Numerical verification passed; the sustaining-wave criterion did
not. No CAD changes.
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

## Controlled experiment — completed

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
no 2D model can sustain a wave. The conclusions below follow inspection of the
completed runs, not their numerical validity alone.


## Results and interpretation

Both new runs completed 189.393939 us, **13,165 accepted steps**, zero invalid
states. The nominal 0.5 mm mesh is 447 by 152 cells. Input configurations differ
only in `model.radial.centrifugal`; numerical source, calibration, initial saved
fields and every accepted timestamp/timestep match. The historical D1 run remains
context with its own older implementation provenance. The matched intervention
is wall control versus radial active.

| Quantity | Historical inviscid D1 | Wall control | Centrifugal active |
|---|---:|---:|---:|
| Final domain-maximum pressure [kPa] | 450.731 | 438.154 | 438.144 |
| Final near-injector maximum reaction rate [1/s] | 0.008635 | 0.008987 | 0.008989 |
| Final whole-domain maximum reaction rate [1/s] | 87,924 | 86,630 | 86,616 |
| Final median heat-release height [mm] | 18.323 | 18.662 | 18.662 |
| Whole-run chemical-to-thermal conversion [J] | 87.2670 | 85.6669 | 85.6653 |
| Whole-run heat transferred to radial walls [J] | 0, model disabled | 9.58020 | 9.58223 |
| 100–180 us mean annulus-exit force contribution [N] | 482.54698 | 458.81775 | 458.81401 |
| 100–180 us maximum scaled conservation residual | 4.41e-14 | 4.33e-14 | 4.36e-14 |

Near-injector values refer to the actual cell center **z=0.751974 mm**; the second
sample ring is z=3.258553 mm. Requested 1 and 3.5 mm locations are snapped to the
native mesh and their actual coordinates are saved. Force is the transient
annulus-exit momentum/pressure contribution, not measured whole-engine thrust or
a steady performance validation.

The centrifugal intervention changes late-window exit force by **-0.003737 N
(-0.000814%)**, final maximum pressure by **-10.69 Pa (-0.00244%)**, and total wall
heat loss by **+0.002023 J (+0.0211%)**. Reconstructed wall pressures are nevertheless
distinct: the largest saved (outer-inner)/mean split is **44.68% at 8 us**, falling
to a domain maximum of **2.95%** at the end. This is consistent with a locally
appreciable radial pressure split but weak feedback through the chosen wall laws.

Pressure pulses persist. Their near-injector reaction signal falls from roughly
47,500/s at 20 us to 11/s at 40 us and about 0.009/s at the end. Full-height fields
show continued burning along the fresh/product interface higher in the channel;
this is **loss of sustained shock-coupled rotating detonation, not extinction of
all combustion**. By the end, the reaction median is near 18.7 mm. The existing
spatial-overlap diagnostic has zero heat release above 2*p1 = 755,833.945 Pa at
the endpoint; this threshold is a diagnostic, not a universal detonation criterion.

A deliberately retained diagnostic warning: at the endpoint, the strongest
pressure face is only half a cell from a half-peak reaction cell on the lower
ring. That apparent proximity is meaningless by itself because the absolute rate
is only ~0.009/s. Normalizing a nearly vanished signal could falsely suggest
coupling. Absolute rates, full-height structure, time history and native budgets
are therefore inspected together. No automatic classifier declares a successful
wave from either pressure peaks or proximity.

This experiment does not establish the root cause of RDE-001, exclude later
startup recovery beyond this window, or rule out effects from resolved radial
flow, inner-wall detachment or calibrated curvature dynamics. It tests one
coarse, original-chemistry/ignition setup with explicitly assumed wall parameters.
No coefficient fitting/sweep was undertaken to manufacture a sustained wave.
The new wall-loss fraction is about 11% of chemical conversion over this window;
these closures do not dominate the energy balance. Quantitative wall/torque
prediction still requires coefficient and thermal-boundary validation.

## Inspectable evidence and reproduction

- [Pressure/reaction space-time comparison](radial_comparison/comparison.png):
  common logarithmic pressure and reaction scales; absolute units retained.
- [Full-height final pressure, reaction and progress](radial_comparison/final_fields.png).
- [Endpoint inner/outer/mean pressure](radial_comparison/final_wall_pressures.png):
  at z=0.751974 mm, t=189.393939 us; read each pressure axis's numerical labels.
- [All inputs, hashes, per-frame metrics and native window reductions](radial_comparison/metrics.json).
- [Matched-input/timestep and separate-source audit](radial_comparison/pair_audit.json).
- Full console records: `radial_wall_control_run.txt`, `radial_active_run.txt`.

The final renderer reuses the already-tested full-height thermal diagnostics,
saves their threshold and source hash, and includes whole-domain fields to avoid
single-probe conclusions. Two read-only analysis/import tests were repeated after
that integration; the renderer was smoke-checked on saved fixtures and all three
final figures were visually inspected. Pressure history uses a shared logarithmic
scale so the initial hot patch does not hide later weak structures. All native
input, summary and history hashes match their postprocessing provenance.

From `rde_sim_starter`, with local saved run directories present:

```sh
../.venv/bin/python radial_study.py --runs runs/d1_run937 runs/radial_wall_control runs/radial_active --out ../reports/new_radial_comparison
```

Native results remain local and Git-ignored; the compact evidence/figures are
committed. Two threads per engine run, concurrent on the shared host: elapsed
32.81 min for wall control and 36.70 min for centrifugal active. These are actual
shared-host timings, not clean hardware benchmarks. The physical source stayed
frozen at f12cca1 throughout; later edits only improve read-only diagnostics and
documentation. No further engine studies are running for this increment.
