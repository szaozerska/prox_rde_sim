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
P2 is implemented as a diagnostic harness but has NOT passed propagation acceptance.
P3–P4 remain pending. GPU controls have run; no long engine or sustainment claim.
The old solver and its environment are unchanged.

## Long-run visualization request (2026-10-25)

Target Run 937 plus 51-FI-5 and 25-FI-5 controlled geometry variants, each to
2 ms with unwrapped and cylinder-wrapped pressure/flow-structure GIFs and
sustainment diagnostics. Additional geometries are not mislabeled as measured
operating points. See `cfd/pelec/engine/cases.json` and the P2 README.

P2 now screens the unmodified upstream FFCM1_Red thermodynamic/kinetic package
because the P1 GRI inversion interval does not cover detonation products. This
is a conditional mechanism change, with the prior implementation preserved.
Compare native regular-grid Godunov and MOL here; neither the separate 3D
controls nor a successful executable exit can authorize engine runs.
Require numerical propagation evidence before the requested long campaign;
record failed checks and do not conflate a long animation with validation.

## P2 results and revised next steps — 2026-10-25

[Full evidence, failed checks and diagnostic movie](../verification/pelec_2d_propagation/README.md).
Eight planar GPU controls and one hot uniform GPU control completed. The hot
chemistry agrees with independent Cantera. First-order reconstruction and a
smaller time step remove observed negative final species in a lab-frame control.
They do not establish correct wave propagation. The 2/1 µm MOL lab-frame controls
preserve elements and EOS but show substantial transient overdrive and reaction
zone contraction. Exact Galilean repeats exceed 5000 K and fail local element
composition and energy/EOS checks. These are unresolved numerical/model-range
issues, not evidence that a physical Run 937 engine fails to sustain detonation.

**Requested deliverables remain pending:** Run 937 and the 51-FI-5 / 25-FI-5
geometry variants, 2 ms histories, unwrapped/wrapped GIFs, and sustainment plots.
The case catalog and SI animation renderer are scaffolding. No new engine
boundary adapter has been compiled or accepted. The unfinished native adapter
is retained only in ignored `runs_cfd/engine_adapter_draft`, not published as a
working engine. No radial momentum dynamics were added by this increment.

Review 1: output snapshots alone missed an intermediate negative mass fraction.
Fix: require complete every-step histories in addition to field checks.
Review 2: conserved total mass/energy and sum(Y)=1 did not detect changes in
local elemental composition. Fix: add local C/H/O/N conservation checks for this
uniform-element planar problem; their applicability must change for separate
fuel/oxygen streams.
Review 3: a steady CJ tolerance over 0.2 µs can reject physical methane/oxygen
pulsations. Keep the original failure recorded; do not equate it with a proven
solver defect or silently relax it. Also test exact coordinate boosts. Those
repeats revealed independent state/range failures, so P3 remains blocked even
if the steady-CJ screening criterion is eventually revised.

Small next increments, in order:
1. Isolate transport from reaction using the same saved initial profile, frozen
   chemistry, and the same lab/moving-frame settings. Instrument where element
   composition first changes. Distinguish numerical species flux/coupling from
   initialization or measurement error. Stop on unexplained source/budget changes.
2. Once state, element and thermo-range checks pass, extend the buffered planar
   window and refine space/time independently. Assess time-dependent shock and
   heat-release separation and time-averaged speed over multiple induction times.
   Define unsteady acceptance before interpreting new results. Do not impose a
   steady wave by continuously resetting it or extend thermodynamic fit ranges
   without a justified mechanism/reference change.
3. Compile and verify the engine inlet, outlet, periodic seam and finite launch
   separately; export actual SI native fields. Then execute the requested 2 ms
   cases and produce both GIFs and fuel/inflow/wave histories. The two smaller
   cases remain controlled geometry variants, not invented experimental runs.

Do not launch a large engine sweep merely because its animation pipeline exists.
Do not attribute these planar discrepancies to annular gap, radial dynamics,
Mundt injector angles, exhausted fuel or collision of counter-rotating waves.

## October 27 continuation: requested 1 ms movies

The user now requests approximately 1 ms of propagation, with Modal authorized.
First compare the pinned solver's existing MOL Lax–Friedrichs flux with the
previous flux at unchanged mechanism, initial state, mesh and time step. Include
a frozen-chemistry moving-frame control to isolate transport. These runs resolve
the current inconsistency before admitting an engine interpretation; no source
patch or thermodynamic extrapolation is introduced. Prepare the native engine
adapter and movie exporter independently while the controls run. A completed
preview must retain its exploratory label and cannot establish experimental
sustainment without numerical and physical validation.

### Measured continuation status and review

[October 27 engine attempt and evidence](../verification/pelec_2d_engine/README.md).
The LF planar repeats pass the saved-state, element and EOS checks in both frames;
P2 wave-speed/structure acceptance remains open. The engine adapter now builds,
and uniform and cold-feed native controls pass independent snapshot checks.
The first reacting engine attempt fails around 0.042 µs. Smaller timesteps do not
remove it; saved negative species and element errors prohibit a sustainment claim.

Review found that upstream release GPU builds suppress device `assert()` even
inside AMReX's always-assert wrapper. Replace problem-level guards with an
unconditional CUDA trap and demonstrate an actual rejection. Do not claim earlier
engine runs had working every-step guards. A compiler-flag-only attempt is not
sufficient while NDEBUG still disables the underlying CUDA assertion.

The next bounded comparison uses the existing MOL correction and Godunov/SDC
options with unchanged physical inputs. Only state-valid output can enter the
requested 1 ms movie campaign. Preview permission is not physical acceptance;
P2 stays open, and no large geometry sweep starts while the reacting launch is
invalid. This sequence supersedes the previous unqualified P3-pending statement:
P3 implementation exists, but reacting-engine execution is not accepted yet.


The final bounded engine diagnostics produced a valid 0.2 µs Godunov launch
and both GIF formats, but not the requested 1 ms histories. The separately
declared trace-budget experiment failed; default strict criteria are unchanged.
See the engine report for exact failure magnitudes and the functioning CUDA
negative-control guard. Resume with a localized transport/reaction coupling
reproducer and a longer strict control before more geometries or long movies.
