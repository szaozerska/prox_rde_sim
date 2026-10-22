# C5a: model correction is not ready for an engine run

**Successor:** the [declared quarter-length experiment](c5_short_reaction.md)
completed its bounded C5b–e controls. The rejected physical-scale fit below remains
historical evidence; it does not prohibit the verified surrogate sensitivity.

This is a saved-reference and numerical-feasibility review after C1–C4. C4's
separate initiation outcome is recorded in the controlled progress report.
**Production chemistry, engine inputs and solver are unchanged. RDE-001 is open.**

The controlled tests establish a useful distinction: the present solver can
propagate the declared surrogate in 2D, while the 3.8 mm finite layer loses
leading shock/reaction coupling even from a formed start. This repeats on
refinement and with a face-aligned initial interface. The 15 mm formed layer
retains near-wall/middle coupling through the bounded window on both grids.
Neither result is a sustained rotating-engine calculation or a measured critical
height. A source/mesh/model correction must be justified before C6.

## Resolution of the main diagnostic questions

| Question | Evidence and remaining limit | Decision |
|---|---|---|
| Cell size alone? | Thin-layer loss repeats at 0.5/0.25 mm; aligned thin control also loses it. Thin total conversion changes by 15.6%, and numerical interface burning remains. | Simple refinement has not fixed the mechanism. Do not claim full convergence or rule out dynamic mixing. |
| Numerical error accumulation? | Native budgets close near roundoff, states stay admissible, C1 row/rotation fields agree exactly, C2 source-step sensitivity is small. | No tested bookkeeping/direction error explains the contrast. These checks do not prove complete accuracy or physical correctness. |
| Faulty initial interface average? | Cut-cell temperature/rate differs sharply between grids. Removing the initial mixed row still gives thin-layer loss. | Initial mixed cells are not a sufficient explanation; subsequent numerical contact diffusion remains. |
| Remote boundary feedback? | C3 observation regions retain checked characteristic margins. Refined thick case exceeded its original speed bound, but valid state was continued under an audited bound; its top state remains unchanged to negligible roundoff. | The original stop was a diagnostic-bound issue, not physical extinction. Isolated-control boundaries do not establish validity of the engine outlet. |
| Physical/model assumption? | The declared reaction structure is far thicker and differently shaped than the physical reference. Uniform premixing, thermodynamics, pre-detonator and expansion remain approximations. | This is an unresolved model-validity gate, not something that an added plotting feature or a 3D switch can be assumed to fix. |
| Are we overinterpreting? | Only 40 µs of layer response; initial formed charge, transient transverse structures and numerical mixing still matter. | Report bounded contrasts. No universal height threshold, unique engine root cause or stable-engine claim. |

## A cheap algebraic check rules out a simple physical re-calibration

The reproducible [audit output](c5_model_feasibility.json) uses the already saved,
pinned D3 physical reference. Run it from `rde_sim_starter/`:

```sh
../.venv/bin/python model_audit.py --evidence ../docs/verification/d3_metrics.json --out /tmp/new_model_audit.json
```

No CFD or new Cantera calculation is performed. No calibration is overwritten.
At unchanged activation energy, changing only k rescales every reaction distance
by the same factor. Current / physical distance ratios are **25.302 at 50%,
69.265 at 90%, and 81.772 at 95%**. Matching physical half-heat distance therefore
leaves the 95% distance at 0.16509 mm instead of 0.05108 mm. Matching the 95%
point instead puts the half-heat distance at 0.01223 rather than 0.03952 mm.
A scalar rate change can still be a declared sensitivity experiment; it cannot
be called a match to this entire physical reference structure.

A second algebraic check fits **both** Ea and k to the physical 50% and 95%
distances while deliberately retaining the old constant-gamma thermodynamics.
This yields Ea/(R T1)=71.61489 and k=2.17877e10/s. It is **not adopted**:

- The held-out 90% distance remains 6.29% too long. Fitting two points is not
  validation at intermediate progress or other pressure/temperature states.
- CJ speed/temperature remain 2471 m/s / 4885 K, compared with D3's
  2531.86 m/s / 3994 K. A kinetics fit cannot repair the unchanged EOS.
- On the current 0.5 mm engine grid the physical 50% and 95% distances occupy
  only 0.079 and 0.102 cells. Substituting those constants would be unresolved.
- The existing **sufficient global source cap** becomes 2.079 ps at source
  fraction 0.05, implying at least **91.09 million steps** for three reference
  intervals before any tighter flow restriction. This is about 6952 times the
  existing source-step count, not a measured runtime or an intrinsic required
  chemistry timestep. A sharper validated integrator/bound could change this.

Tightening quadrature relative tolerance from 1e-10 to 1e-12 changes fitted
parameters/cap by at most 2.1e-11 relatively. Two quick unit checks cover
constant-rate scaling, calibration nonmutation, the held-out distance, the step
count and rejection of invalid reference lengths. The full suite result is
recorded in the increment log. This establishes algebraic feasibility limits,
not a new validated reaction model.

## Paper and literature consistency

[Mundt](../../Mundt2023.pdf), printed pp. 74–78, uses physical GRI-Mech / Cantera /
SDToolbox references and an operating refill estimate; it does not validate our
one-step parameters or identify 3.8 mm as the startup charge. The paper/model
[audit](mundt_model_audit.md) preserves those distinctions and the unresolved
2.46% CJ-reference difference. CEA replication also remains pending.

[Li, Mi and Higgins](https://arxiv.org/abs/1405.7753) support testing a formed wave
with yielding confinement, using different kinetics. [Taileb et al.](https://doi.org/10.1016/j.combustflame.2020.04.018)
show why chemistry matters in another mixture's layer-quenching problem. Neither
provides a methane/oxygen Run 937 critical height or licenses an arbitrary
rate multiplier. [Strakey and Ferguson](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf)
provide a precedent for chemistry/1D checks before methane/oxygen engine use,
not direct validation of these constants.

## Gate decision and smallest next increments

**Do not advance to C6 with the algebraic candidate or an arbitrary thicker
engine fill.** C5's physical/numerical readiness gate remains open. This is an
identified inconsistency between the proposed physical scales and the existing
mesh/source treatment, not a missing visualizer or a claim that no progress is
possible. No longer engine run is justified merely by the C3 thick-layer result.

1. Choose and document one reaction-model hypothesis from physical reference
   curves, keeping fitted and held-out quantities separate. Reconcile the CJ/EOS
   reference discrepancy or quantify its accepted scope before calling a model
   physical. A declared reaction-length sensitivity may retain the old EOS, but
   must remain labeled as a surrogate experiment.
2. Verify its source treatment in cheap homogeneous reactors and saved shock
   states against an independent tightly converged ODE solution. Quantify whether
   the current global cap is unnecessarily restrictive; do not disable it to
   make a run fast. Benchmark a few steps before selecting a backend/integrator.
3. Run one short filled-profile control at fixed new chemistry, then its decisive
   mesh/source comparison. Select a locally affordable domain and duration from
   characteristic travel bounds. Only after this gate, revisit the 3.8 mm layer.
4. Return to the bounded engine comparison only if those checks support it.
   Keep the original engine case and its failed outcomes intact.

These are intentionally separate commits/gates. No solver rewrite, mechanism
sweep or detonationFoam installation is justified just to complete this audit.
The independent 3D session can use the findings without this session changing
its branch or checkout.
