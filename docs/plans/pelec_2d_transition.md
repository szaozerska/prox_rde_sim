# 2D reacting-flow backend transition — 2026-10-25

## Decision and preserved baseline

Select **PeleC + PelePhysics + SUNDIALS/CVODE** as the new external 2D backend.
The user authorized evaluation, integration, dependencies, bounded Modal jobs,
and publication on main. No CAD or changes to the independent 3D branch.
This replaces the *future predictive backend*, not historical evidence. The
existing `rde_sim_starter/run.py` remains executable with identical inputs and
one-step chemistry. Revert by using that command; no Git reset is required.
Baseline commit: `73d4516`. No unpublished solver changes were present.
Two unrelated working-tree edits (controlled_2d_progress.md and the untracked
independent investigation) are intentionally excluded from transition commits.

The old backend uses prescribed 1 mm half-reaction length, constant R/gamma,
a single progress variable and a fitted Arrhenius rate. Cantera/SDToolbox
reference calculations do not replace that production source. The 0.25 mm
variant is a separate sensitivity experiment. RDE-001 is unresolved.

## Candidate evaluation

| Package | Established use and 2D fit | Decision |
| --- | --- | --- |
| PeleC / PelePhysics | Compressible reacting flow, species thermodynamics, stiff chemistry, block AMR, compiled 2D/3D, CPU/CUDA/HIP; published RDE simulations | Select: open source, GPU path and shared upstream with independent 3D work |
| detonationFoam | OpenFOAM 8 gaseous-detonation solver; published rotating/oblique/cellular detonation applications; optional 2D AMR | Strong fallback; additional OF8 installation and separate CPU-oriented stack; no verified native GPU backend in inspected distribution |
| BYCFoam | OpenFOAM/Cantera RDE research solver with published 0D/1D/2D tests | Relevant methodology; reproducible source/build availability not established in this evaluation |
| ANSYS Fluent | Published methane/oxygen RDE validation with 12 species/38 reactions; 2D capable | Strong commercial reference, but no license/access established here |
| CONVERGE | Argonne-associated RDE calculations, adaptive meshes and finite-rate chemistry | Strong commercial reference, but no license/access established here |
| blastFoam | Compressible blast/multiphase/high-explosive applications | Less direct match than gaseous combustion choices |
| Cantera alone | Thermodynamics, species rates, reactor references | Keep for independent checks; not a spatial shock-capturing CFD replacement |

Sources checked 2026-10-25:
- https://github.com/Pele-Suite/PeleC (build dimensions, chemistry and CPU/GPU options)
- https://docs.nlr.gov/docs/fy22osti/82891.pdf (PeleC RDE application)
- https://doi.org/10.1177/10943420221121151 (PeleC solver paper)
- https://github.com/myguixx/detonationFoam (OF8 source, applications, build)
- https://doi.org/10.1016/j.cpc.2023.108859 (detonationFoam)
- https://www.mdpi.com/1996-1073/17/4/769 (BYCFoam)
- https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf
- https://doi.org/10.1115/1.4050590 (Argonne-associated CONVERGE study)
- https://github.com/synthetik-technologies/blastfoam

The 2022 NREL presentation explicitly uses simplified periodic 2D RDE geometry,
AMR and DRM19/LiDryer chemistry for hydrogen/methane-air blends. It reports both
stable and unsustained configurations. This is direct 2D application precedent,
not validation of pure methane/oxygen Run 937 or our pinned mechanism choice.

## Implementation boundary

Do not inject a multispecies rate routine into the old constant-property EOS.
Use native PeleC flow, species, energy and thermodynamics together. Keep workflow
adapters small, explicitly convert PeleC cgs to project SI, and preserve raw
native outputs. Never map species to the old progress variable without a stated
physical definition. Do not fabricate old native budget/torque fields.

Use the inspected source revision also used by the separate 3D checkout:
`949e2bb67386bf4b16324b06555e303ff411e179`; record all submodule pins.
Reuse build knowledge only. That checkout reports unresolved wave/thermodynamic
checks; its existence does not validate this backend. In particular do NOT copy
its diagnostic GRI temperature-inversion bound patch. Begin below the upstream
3000 K inversion bound and preserve the original thermodynamic/rate source.
GRI-Mech 3.0 is initially a reference-compatibility mechanism, not a declaration
that it is the best high-pressure detonation mechanism. A smaller literature
mechanism needs its own provenance and comparisons before selection.

## Small verifiable increments

1. **P0 — freeze and publish choice.** Preserve baseline; publish this plan and
   readme/handoff update before backend implementation.
2. **P1 — native 2D methane chemistry integration.** Pin/build a 2D executable;
   initialize a uniform premixed CH4/O2 control using upstream GRI thermodynamics;
   execute native chemistry on CPU in Modal; compare species, temperature,
   density and energy against Cantera using the exact bundled mechanism.
   Include reacting/frozen checks, time-step comparison, species order, unit and
   raw-output provenance checks. This exercises a 2D grid with uniform flow;
   it is not a propagating detonation or engine.
3. **P2 — propagation gate.** Resolve mechanism temperature validity and inverse
   thermodynamics over the full shock/product range. Then planar wave on two
   spatial resolutions, with a separate time-step check and independent CJ/ZND
   reference. Stop on critical source/EOS/conservation inconsistencies.
4. **P3 — 2D unwrapped engine adapter.** Periodic circumference, explicit feed,
   outlet and initialization, case provenance, pressure/species/heat-release SI
   exports and existing-style graphs. Premixed feed remains an approximation;
   do not call this a resolved impinging-injector model.
5. **P4 — validate utility and runtime.** Compare multiple sustained/failed
   operating points, include held-out conditions, measure one-hour feasibility
   on actual CPU/GPU resources. No runtime or sustainment guarantee from P1.

## Three planning reviews

1. Chemistry-only swapping would retain inconsistent energy/EOS assumptions.
   Fix: isolate a complete external solver, keep the old executable intact.
2. An upstream example completing is not physical acceptance. Fix: independent
   same-mechanism reactor comparison, frozen control, refinement and explicit
   source/range gates; no inference of wave sustainment from smoke tests.
3. The parallel 3D build contains diagnostic patches and unresolved results.
   Fix: pin original upstream sources, copy no patched kinetics/thermodynamics,
   prove unit/species conversions here. Bound initial cloud jobs to one CPU
   container; only request GPUs when a verified GPU executable is ready.

## Current status

P0 complete and pushed as `1868f8b`. P1 implemented and verified on 2026-10-25:
three native CPU controls and independent field analysis pass; nine adapter tests
and five original physics tests pass. [Evidence and encountered failures](../verification/pelec_2d/README.md).
P2 is next. P3–P4 remain pending; no engine/GPU runtime or sustainment claim.
The old solver and its environment are unchanged.
