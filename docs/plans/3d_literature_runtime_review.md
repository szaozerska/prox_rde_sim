# 3D literature review and two-hour execution plan

2026-10-22. Revision 12 decision record. Planning, not a new simulation result.
This document and the revision 12 override in [the master plan](../../first_sim_plan.md)
control the next implementation. Keep the existing G0-G5 verification dependencies.

## Decision

Use an established compressible, reacting CFD solver. Evaluate **PeleC on GPUs
first**, with its native CPU build for small verification controls. Keep the
installed **OpenFOAM 8/detonationFoam** as a bounded CPU fallback and independent
geometry reference. One branch and one active engine implementation; no custom
3D flux solver, GPU port, machine-learned chemistry, or backend framework.

The reason is the user's new one-to-two-hour limit for the largest routine runs,
not an established PeleC speedup on our case. Neither candidate has yet run a
validated 3D methane/oxygen engine here. detonationFoam has installation and mesh
passes only. Modal CPU execution was verified at eight requested cores; no GPU
allocation, 64-core allocation, solver throughput, or maximum quota is verified.

The first team deliverable is a reproducible **idealized 3D diagnostic case**,
with saved inputs, native fields, pressure/front plots, conservation and numerical
sensitivity results, and a short limitations report. It is useful for inspecting
flow and comparing controlled changes. The eventual design-screening target is
sustained detonation, so a rotating pressure disturbance or imposed rotating
ignition source cannot count as success. It is not yet a validated design predictor,
experimental operating map, thrust certification, or resolved cellular detonation.

The user subsequently authorized **starting before 14:30 PDT, October 22**.
Implementation starts after these plan reviews; the scheduled kickoff is paused
to avoid duplicate work. The earlier spoken request to allocate 64 cores
and start detonationFoam was cancelled. Do not resurrect it as the current choice.

## What Mundt actually computed

Primary source: [Mundt 2023, local thesis](../../Mundt2023.pdf). Printed pages are
used below; PDF page = printed page + 16. Re-read the complete Chapter 3/4 text,
rendered pp. 44-103, and revisited the methods and dimensions in Chapters 1/2.

**Run 937 is a physical experiment, not a 2D or 3D CFD result.** Chapter 3 reports
pressure sensors, temperatures, inferred feed flows and high-speed camera wave
tracking. Its two-dimensional FFT is a transform of angle-time camera data, not
proof that a two-dimensional flow simulation produced the graph. Chapter 1,
p. 21, points to separate CFD publications by Strakey/Ferguson and Pal et al.

Chapter 4 combines these experimental data with inexpensive thermochemical and
empirical calculations:

| Calculation / assumption | Why Mundt uses it | What it does not establish for CFD |
|---|---|---|
| Eq. 4.1 pressure fit from mass flux and equivalence ratio (pp. 72-74) | Estimate pre-detonation pressure where a front-wall measurement is unavailable. | It is an empirical fit, not a conserved boundary law or independently predicted pressure. |
| Premixed CH4/O2, 300 K, GRI-Mech 3.0, Cantera + SDToolbox (pp. 74-76) | Compute ideal CJ/ZND references consistently across operating conditions. | The hardware injects separate gases; premixing in this calculation does not validate a premixed engine inlet. GRI is a comparison reference, not an uncertainty-free truth. |
| Induction at maximum dT/dt, post-shock velocity, factor 29 (pp. 74-75) | Estimate cellular width from a one-dimensional ZND calculation. | This is not a resolved cellular CFD result. The thesis reports nonconverged/shifted points and underprediction of experimental cell size. |
| CEA CJ-equilibrium products + NIST formation enthalpies (pp. 76-77) | Estimate heat release and nominal chemical energy supply. | A Cantera equilibrium calculation is an independent recalculation unless database and state conventions match; it is not an exact CEA reproduction. |
| Eq. 4.5 fill height from mass flux, gas properties, pressure and measured frequency (pp. 77-79) | Infer an effective replenishment height for scaling comparisons. | It is not a measured fresh-layer field or a prescribed startup charge. Using it to predict its input frequency is circular. |
| Approximate mode regions and 3.25 mm mean-height prediction (pp. 80-103) | Obtain inexpensive empirical engineering guides and test them on off-sweep data. | Regions overlap; coreless operation contradicts a universal radius/cell-size extinction rule. Reported mean errors are not universal tolerances. |

The thesis describes laboratory resources and reference software, but gives no
full-engine CFD CPU/GPU allocation or runtime to copy. It reports no thrust data
for these engines. Eq. 4.7 and Figs. 4.28-4.29 do not measure torque or shaft power;
keep the wave-frame/laboratory-frame velocity issue and mechanical balance separate.

Run 937 anchors remain Table 3-2: phi 1.176, 0.26865 kg/s, two co-rotating waves,
15.84 kHz passage frequency, 1893 m/s outer-periphery speed, 100.2 kPa back pressure.
Eight axial pressure values include two taps beyond the core termination. The
0.696 s burn and last-100-ms averages cannot be equated to a short CFD startup.
The unresolved 2.46% discrepancy between our GRI CJ calculation and the table's
2471 m/s remains visible; never tune chemistry merely to hide it.

## Closely relevant literature and resource evidence

The following are primary papers, author manuscripts, project reports or official
solver documentation. Abstract-only evidence is identified. They are not a
comprehensive census of CFD use, and different fuels/cases are not runtime proxies.

| Source | Method, assumptions and useful evidence | Resources / limit of inference |
|---|---|---|
| [Strakey & Ferguson, AIAA 2022-1113](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf), full methods/results | Full 3D AFRL CH4/O2, Fluent 20.1, 1D numerical controls, 12-species/38-step chemistry, LES, separate injectors, 300 K walls and downstream plenum. Baseline phi 1.16 and 0.267 kg/s differs from Run 937. Mesh and timestep change speed; 400 um gives one wave, finer meshes two. Closer speed agreement may involve offsetting errors. | 2.1-85.2M cells; 100 um density-based case took about five weeks on 2,000 cores to reach statistical steady operation. This is not a forecast for our reduced preview. |
| [Pal et al., AIAA 2021-3642](https://www.researchgate.net/publication/351246775_Large-Eddy_Simulations_of_Methane-Oxygen_Combustion_in_a_Rotating_Detonation_Rocket_Engine), author-posted methods/results | Full 3D AFRL CH4/O2 with CONVERGE 2.4; Cartesian cut cells/AMR, discrete injectors, predetonator, ideal gas, adiabatic walls, dynamic Smagorinsky LES and finite-rate 12-species/37-reaction chemistry without turbulence-chemistry closure. Peak about 18M cells; 0.1875 mm finest normal AMR. Captures modes, but speeds are 300-400 m/s low. | Argonne Bebop CPU cluster; inspected manuscript does not specify a reproducible core-count/wall-time pair. Cannot infer a two-hour cost. An unwrapped plot is a slice of 3D flow. |
| [Peng & Deiterding, 2025 AMROC study](https://eprints.soton.ac.uk/497299/1/elsarticle-template-num.pdf), methods, mesh and cost tables | 2D unrolled and 3D curvilinear RDEs, detailed chemistry, adaptive meshes. In 3D hydrogen cases, changing resolution affects mixing and structure even when global speed changes little. Local shock, reaction and contact refinement matter. | Table 3 reports 4,260 / 27,648 / 194,246 CPU-hours per 1 ms for 2.9 / 15.1 / 78.6M-cell 3D cases. Core-hours are not wall hours; neither case nor scaling transfers directly to methane/Modal. |
| [Sun et al., detonationFoam, CPC 2023](https://www.sciencedirect.com/science/article/pii/S0010465523002047), abstract/program summary; [official source](https://github.com/JieSun-pku/detonationFoam) | Dedicated reacting shock solver; paper tests include ignition, diffusion, shocks, flames, planar/cellular/oblique detonation. Public application bibliography supports actual research use. | Published AMR/DLB capability does not establish those options in our pinned build. Its optional 2D AMR library is not a verified 3D AMR workflow. No end-to-end GPU execution established. |
| [Henry de Frahan et al., PeleC 2023](https://doi.org/10.1177/10943420221121151), indexed full performance section | Compressible reacting CFD, AMReX AMR/embedded boundaries, GPU chemistry integration. Same-path and best-configuration comparisons give different speedups. | Eagle CPUs versus Summit nodes with six V100s; representative chemistry comparison about 6x, same-path comparison about 14x per node. These are combustion benchmarks, not a two-hour Run 937 result or per-GPU equivalents. |
| [PeleC RDE presentation, 2022](https://research-hub.nlr.gov/en/publications/computational-study-of-variable-fuel-air-ratio-and-hydrogen-dopin/), abstract and indexed slide evidence | Methane-air/hydrogen-doping studies; indexed slides identify 2D RDE results. Supports application relevance. | Does not supply a ready validated 3D CH4/O2 case. Reviewed upstream RegTests has shock, zeroD, reacting and EB controls, but no named RDE template. |
| [JAXA R20ECMP12](https://www.jss.jaxa.jp/en/ar/e2020/14259/), project report | 2D non-premixed CH4/O2 LES of a different 101 mm engine; finer resolution improves speed agreement. Its figure source is conference work, not peer-reviewed validation of our case. | Supercomputer use, more than 20 species. Establishes that 2D propagation is possible, not that our surrogate is adequate or 3D cures extinction. |
| [Lau-Chapdelaine et al., JPP 2024, author version](https://arxiv.org/html/2609.04519v1), model/methods | Quasi-2D unrolled thin annulus, radial averaging, area variation, reactive Euler and one-step hydrogen/oxygen model. Reduces cost and exposes injector shock/pressure-loss mechanisms. | Fuel/model differ. Injector dynamics cannot be inferred from an instantaneous valve closure. Useful assumption control, not a replacement 3D implementation. |
| [Kwak et al., updated preprint 2026](https://arxiv.org/pdf/2508.16105v2), methods and Table 15 | OpenFOAM v12 pressure-based solver, 2D AMR/DLB; global and detailed-wave accuracy need different resolutions. First-order settings introduce diffusion. | 48 Xeon cores; 200-201 us benchmark takes 281 s uniform, 67 s AMR+DLB. This is only a one-microsecond timing sample, not total runtime. Another CPU stack offers no demonstrated shortcut here. |
| [Elasrag et al., ASME GPU RDE submission](https://asme-turboexpo.secure-platform.com/a/solicitations/193/sessiongallery/12509/application/101483), abstract only | GPU charLES plus ZND-trained flamelet rate scaling for non-premixed H2/air. | Reports under one day and near-100x versus conventional CPU solvers. Chemistry reduction and hardware are combined; exact hardware/cost absent here. Does not establish under two hours or CH4/O2 transfer. |

Additional candidates screened: [MFC](https://github.com/MFlowCode/MFC), its
[feature constraints](https://mflowcode.github.io/documentation/case_constraints.html),
and the [AMReX-based high-speed solver study](https://arxiv.org/html/2412.00900v2).
They reinforce GPU/AMR feasibility but do not provide a demonstrated quicker,
ready Run 937 workflow. Do not implement them in parallel. Commercial Fluent,
CONVERGE and charLES add licensing/deployment dependencies; do not buy a license
or migrate absent a demonstrated matching-case advantage.

## Physical decisions for the first deliverable

| Choice | Benefit and alternative considered | Required check / limitation |
|---|---|---|
| Full 360-degree 3D annulus and core-end expansion | Retains curvature, radial structure and possible wave counts. A sector would force permitted periodic modes; an axisymmetric model cannot represent rotating waves. | Recheck analytic volume, wall/face areas, normals, equilibrium, shock direction and outlet influence. No claim that dimension alone fixes extinction. |
| Thermally perfect ideal-gas species, finite-rate methane chemistry, FP64 | Reuse native thermodynamics and chemistry. Avoid inherited fitted constant-gamma/1 mm reaction surrogate and premature mixed-precision work. | Native units, energy convention, 0D reactors and 1D CJ/ZND propagation; compare reference models and preserve discrepancy. |
| Start with a premixed equivalent feed | Avoid resolving 144 holes/plenums before a useful diagnostic exists. | Major model approximation. Preserve mass, composition and enthalpy; compare fixed mass feed with pressure-responsive feed before experimental sustainment claims. Do not impose both pressure and mass flow independently. |
| Smooth inviscid, adiabatic slip walls initially | Removes expensive boundary layers/LES closure and wall thermal setup. | Omits friction, heat loss and turbulent/molecular mixing. Cannot support wall heat flux or injector-mixing claims. Different published wall assumptions are a reason for later sensitivity, not proof losses are negligible. |
| Controlled ignition with fixed integrated inventory | Avoid full predetonator DDT expense and unmeasured hardware history. | Verify the formed wave separately; compare mesh-independent initial mass/energy. Stop forcing before judging propagation. Seeded wave count is not a prediction. |
| Local refinement after fixed-mesh controls | Resolve required shock/reaction/contact regions while coarsening downstream flow. | Verify interface/regrid budgets and tagging buffers. No generic cold-box timing or temperature-only tagging as proof of reacting performance. |

An inviscid premixed calculation cannot decide whether the real separate jets mix
well enough to sustain a wave. Progress to an injector/mixing sensitivity before
using it to classify modified injector designs. A geometry-only change also needs
renewed boundary, mesh and startup sensitivity, rather than a transferred pass.

For chemistry, use built-in GRI-Mech 3.0 as the paper-comparison baseline in small
cases. Screen one existing reduced candidate (DRM19 is available upstream) against
it at the actual fresh, compressed and mixed hot/fresh states. Its availability
is not validation for oxygen-rich high-pressure detonations. A published 12-species
model is acceptable only with its exact file/provenance and matching checks;
"grimech12" is not automatically the same mechanism. Do not invent a mechanism
or rate multiplier. If reduction fails, keep detailed chemistry and reassess cost.

[PeleC EB documentation](https://github.com/Pele-Suite/PeleC/blob/development/Docs/sphinx/geometry/EB.rst)
requires special attention: default state redistribution favors robustness, and
species repairs can change conserved quantities. Measure corrections; a finite,
positive final state is not enough. Use native upstream tests before custom case
setup. Do not transplant OpenFOAM mesh-validation status to Cartesian cut cells.

## Making the one-to-two-hour target operational

Interpret the target as **per complete routine case**, including normal queued
startup, integration, diagnostics and artifact persistence, after the solver image
has been built once. Building and validating the application is separate engineering
work and is not promised within two hours. A three-case refinement comparison may
take longer in aggregate; run independent cases concurrently only with independent
resources and passed prerequisites. Do not split a long case into many two-hour
restarts and call it compliant.

No literature source above establishes that the most detailed full-engine case
fits two hours on eight GPUs. Treat this as a constrained optimization problem:
minimize measured dollars per completed case subject to the numerical/physical
checks, memory fit and a conservative runtime forecast below the limit.

1. Build/cache a pinned native GPU case; confirm actual device execution on one
   H100-class allocation (compatible A100/H200 if more practical). First checkpoint
   after four active engineering hours. If basic chemistry+EB requires major solver
   changes, use the installed CPU fallback instead of an open-ended port.
2. Run small verified representative reacting workloads on 1 then 2 GPUs; use
   4/8 only when justified. Time startup, chemistry, fluxes, communication, output
   and persistence separately. Use the smallest fitting allocation as the baseline
   if one GPU cannot fit. Measure host RAM and VRAM with 20% planning headroom.
3. Benchmark multiple blocks that include hot chemistry, fresh refill and expected
   refined-cell occupancy. Five-to-ten-minute timing windows are a budget, not a
   substitute for advancing enough physical time to exercise these states.
4. Forecast with measured wall-seconds per simulated microsecond, using the slowest
   representative block and a 30% planning margin. Require forecast integration
   <=90 minutes to reserve 30 minutes for scheduling/setup/output. Refresh the
   estimate as refinement occupancy and chemistry stiffness evolve.
5. Use a submission-to-result watchdog and bounded subprocess timeouts. Attempt
   graceful stop/output by 110 minutes and stop at 120; zero automatic retries.
   A timeout is incomplete, not a passed run. Modal's function timeout alone does
   not include queue time, so it cannot enforce this end-to-end contract. The
   watchdog bounds spending/waiting; it cannot guarantee a completed result when
   hardware is unavailable. Cancel stalled allocation instead of silently overrunning.

Illustrative **required throughput**, not predicted performance, for a 90-minute
integration allowance:

| Physical interval | Maximum forecast wall s/us | Maximum measured wall s/us before 30% margin |
|---|---:|---:|
| 189.394 us first preview | 28.512 | 21.932 |
| 315.657 us extended preview | 17.107 | 13.159 |
| 2 ms later screening case | 2.700 | 2.077 |
| 5 ms later statistical candidate | 1.080 | 0.831 |

The initial 63.131 us checkpoint and 189.394-315.657 us preview cap remain. A
successful preview can then qualify for a **separately specified, at-most-2-ms
screening case**, only after its reference checks, runtime gate, restart/storage
checks if needed, and mesh/time sensitivities pass. This revision permits that
bounded extension; it does not automatically launch it or establish stationarity.
Five milliseconds is a feasibility illustration, not an approved next run.
Do not extend a decoupled/extinguished wave merely to fill this time budget.
A 2 ms record is not automatically statistically stationary or long enough.
Pick the post-startup observation window from actual refill/flow-through and wave
periods; report how many of each it contains and compare disjoint window metrics.

For planning only, earlier authenticated Modal rates were $3.95/H100-hour,
$0.04730/physical-CPU-core-hour and $0.008/GiB-hour. Eight H100s for two hours are
$63.20 GPU-only, plus host resources/storage. Sixty-four cores and 128 GiB for two
hours are about $8.10, but cheap hourly cost says nothing about completion time.
Recheck rates and actual allocation before launch; select the least costly tested
allocation that meets the time/accuracy gates. Use Modal Functions as in the access
probe; non-preemptible/Sandbox rates differ. [Pricing](https://modal.com/pricing),
[GPU allocation](https://modal.com/docs/guide/gpu),
[timeouts](https://modal.com/docs/guide/timeouts).

If the forecast fails: reduce output, improve load balance or add useful hardware;
then use verified local refinement/reduced chemistry. If it still fails, deliver
the shorter explicitly limited diagnostic and record the infeasible higher-fidelity
case. Never silently coarsen a failed detonation, shorten its claimed averaging
window, or relax conservation checks to meet the clock.

## Small implementation increments after kickoff

| Increment | Concrete output | Verification before proceeding |
|---|---|---|
| R0 / G0 | Pinned PeleC/submodule/mechanism/build manifest; cached image; one tiny upstream case | Actual GPU execution, final-time/field checks, device/rank mapping. If unusable, record cause and switch to bounded detonationFoam CPU trial. |
| R1 / G1a | Native shock and zeroD controls, CPU/GPU comparison | Analytic shock and Cantera reactor comparisons; finite states, species/element/energy budgets, tolerance tightening. No engine run through failure. |
| R2 / G2a-b | Mechanism reference and formed 1D methane detonation report | Separate mesh refinement and timestep halving; speed AND induction/heat release AND shock/reaction coupling. Add third mesh if order/trend is unclear; do not call two grids formal convergence. |
| R3 / G1b-c | Annulus/expansion cold case, boundary and refinement-interface controls | Geometry areas/volume, equilibrium, inclined shock, hot/fresh contact, quantified EB repairs, composite flux budgets. Reactive AMR crossing only after R2. |
| R4 / G3 | Timed reacting pilot and cheapest feasible resource choice | Same physics, grid, physical interval and output across allocations. Verify MPI/restart consistency over short deterministic controls and longer statistical observables, not pixelwise equality of chaotic runs. |
| R5 / G4 | First short 3D case and team report | Post-ignition coupling, front tracks, all tap histories, input/output/storage budgets, one spatial and one temporal sensitivity. Report experimental discrepancies without retuning to them. |
| R6 | At-most-2-ms screening case if qualified; one highest-value assumption sensitivity | Runtime forecast, window-to-window stability, mode consistency and numerical sensitivity. No full multi-engine sweep before this is useful. |

Keep existing cold tolerances and initial 5% speed/10% mean-pressure/heat-release
triage values explicitly labelled project screening values. They are not experimental
error bars or proof of convergence. Before each numerical test, record the norm,
reference, tolerance and intended claim. A mode change or extinction/survival change
under refinement blocks a physical mode conclusion even if scalar errors are small.

PeleC does not support a true 1D build. Implement physical 1D controls as
transversely uniform thin native 2D/3D domains and check transverse invariance.
Resolve the physical 1D reference sufficiently to measure its reaction structure.
For the first 3D diagnostic, quantify the effect of under-resolution on the stated
observables; global speed agreement alone does not demonstrate resolved chemistry
or cellular structure. No claim of DNS resolution everywhere is required for an
explicitly idealized diagnostic, but no widened reaction surrogate is implicit.

Use a small hierarchy for eventual design screening: 0D/1D chemistry/propagation
controls; cheap 2D geometry/feeding investigations where assumptions apply; short
3D propagation and replenishment checks; then qualified longer 3D stability and
model-sensitivity cases. Two-dimensional failure is evidence to investigate, not
a universal veto or predictor for 3D. Before calling the classifier useful, include
a nearby documented non-detonative condition as a negative control, not only Run
937. Select its exact inputs and experimental label from the thesis, without
inferring a failed condition from an approximate plotted mode boundary.

Classify outputs as `invalid numerics`, `insufficient observation`, `wave decouples`,
or `coupled propagation over the measured window`. Reserve `sustained within the
validated model` for tests that also pass replenishment, startup/window, grid/time,
and relevant feed/outlet sensitivities. This remains conditional on the model;
credible modified-design prediction requires relevant experimental validation.

For every failure preserve the run and classify: setup/code/units; spatial or
numerical mixing error; temporal/source integration error; physical assumption;
or unresolved. Test the discriminating small control before the next dependent
step. A proposed future physics feature does not excuse a present conservation or
propagation failure. Diagnostics may still be delivered as failed/inconclusive.

## Figure comparisons and minimal useful output

Reuse the detailed [figure roadmap](figure_validation_roadmap.md); it already
catalogues all 35 Chapter 3 and 31 Chapter 4 figures. No new CFD campaign is needed
merely to change axes. The priority for this branch is:

1. **Table 3-2 / Fig. 3.2:** exact wall-pressure stations, front wall, downstream
   taps; dimensional and normalized profiles with residuals. Keep ring averages
   separate from clocked probes, and short-window means separate from 100-ms data.
2. **Figs. 3.4-3.7:** pressure and heat-release angle-time plots, front trajectories,
   direction, wave count, passage frequency and outer-equivalent speed. Heat release
   is not camera luminosity. Use arrival tracking first; 0.19 ms is too short for
   fine FFT frequency claims. Two-dimensional FFT analysis is a later output tool.
3. **Figs. 4.2-4.4:** CJ, ZND-derived cell proxy and heat-release references, starting
   with the existing Run 937 neighborhood. Preserve gaps/nonconvergence and the
   CEA-versus-Cantera distinction; no full sweep required before the native case.
4. **Fig. 4.5:** paper-formula fill height beside a separately defined field-derived
   fresh-layer diagnostic. Never initialize from the inferred value and claim it
   as an independent result. **Figs. 4.19/4.21:** chemical supply versus actual
   conversion/pressure after useful neighboring cases exist.
5. Later: 76 mm pressure/speed trends (3.20-3.27), back-pressure sensitivity (3.35),
   then other geometries and mode maps. Remaining Chapter 4 ratios reuse those
   records. Off-sweep Figs. 4.30-4.31 remain holdouts. Plenum spectra (3.8-3.10),
   material damage (3.15), and full feed/thermal histories require missing models.

Minimum package: one run command, one plot/report command, immutable case manifest,
compact CSV/JSON metrics, saved native fields readable by standard viewers, six
useful panels (fields; angle-time; probes; pressure residuals; conservation;
mesh/time sensitivity), and a README stating supported uses and open issues.
Reuse published 2D plotting changes only by inspecting a specific pushed commit;
no shared mutable imports, merge during a run, or dependency on that chat finishing.
