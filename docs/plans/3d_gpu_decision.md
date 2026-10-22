# Modal GPU decision for 3D modelling

October 22, 2026. Research and planning only; no GPU benchmark or new solver pass.
This historical record supports revision 11. The [revision 12 literature/runtime
review](3d_literature_runtime_review.md) and [execution plan](../../first_sim_plan.md)
now control implementation, timing and sustained-wave claims. Modal CPU access has
since passed; no GPU result existed at this record's handoff.
User priority: minimize time to a useful result, tolerate reduced initial fidelity,
about eight Modal GPUs initially. Device type, topology and access remain unverified.

## Recommendation and scope

Use one physics project with small CPU controls and GPU production. Retain the
existing isolated `3d-modelling` checkout; do not create separate permanent CPU
and GPU model branches. A hardware flag must not silently change chemistry,
boundary conditions, energy convention or diagnostics. Same-backend CPU/GPU small
checks are more useful than maintaining two complete engine implementations.

PeleC is the first GPU candidate, conditional on a short capability and correctness
trial. Freeze the working detonationFoam installation and native mesh evidence as
fallback/reference, rather than spending additional effort completing both stacks.
If the trial uncovers substantial solver development, benchmark the installed
solver on more CPU cores and continue that path. Existing OpenFOAM meshes remain
useful reference evidence; PeleC needs a newly checked native EB geometry.

The optimization target is time to a checked result, including migration and
failed runs. No available evidence establishes an absolute runtime or GPU speedup
for this engine. Do not promise eightfold speedup from eight GPUs.

## Solver comparison

| Option | Relevant capability/evidence | Cost or risk for this project | Decision |
|---|---|---|---|
| Installed OpenFOAM 8 + detonationFoam | Built, pinned, smoke-tested, body-fitted annulus checked; compressible reactive solver. Current audited build has no demonstrated GPU execution. | Existing progress lowers setup cost. More CPU cores need a decomposition/consistency check. Adding GPUs alone changes no kernels. A GPU linear-system library alone is not an end-to-end port of explicit flux/chemistry work. | Fastest fallback; do not write a GPU port. |
| PeleC + AMReX + PelePhysics + SUNDIALS | Compressible reacting flow; MPI+GPU; block AMR; upstream cold shocks, zero-D chemistry and EB tests. [P1, P2] | Native geometry/case migration; chemistry-generation/build configuration; cut-cell corrections; AMR verification and GPU/MPI integration. Existing OpenFOAM fields/mesh are not native PeleC inputs. | Preferred GPU trial. Most direct documented match to compressible chemistry plus selective refinement. |
| MFC | GPU-capable compressible flow and reacting-flow support, with shock-tube/mixing examples. [M1, M2] | Need to verify the exact methane kinetics, wall treatment and cylindrical/geometry combination at a pinned version. Published large-scale multiphase throughput is not an RDE chemistry benchmark. | Credible reserve candidate, not a simultaneous implementation. Selection could change if an exact supported configuration demonstrably shortens setup. |
| Ansys Fluent native GPU | 2026 R1 documentation includes compressible species transport, finite-rate reactions and stiff chemistry. GPU solver settings are pressure-based; transient coupling options differ from density-based shock solvers. [F1] | License/cloud deployment not established; native GPU model compatibility and detonation propagation must be demonstrated. GUI availability does not remove verification. | No purchase/migration now. Reconsider only with an available license and a proven matching detonation case. |
| Custom CUDA/JAX/PyTorch solver or ML chemistry | Potential acceleration is not implementation evidence. | New fluxes, source integration, boundaries and conservation checks; training/domain coverage for learned chemistry. | Reject for fastest reliable delivery. |

PeleC is a compressible code. The similarly named low-Mach Pele solvers are not
substitutes for this shock-supported detonation problem. We already use CFD
software; GPUs motivate a backend assessment, not abandoning an in-house 3D solver
that was never planned.

PeleC development HEAD observed via read-only `git ls-remote`:
`949e2bb67386bf4b16324b06555e303ff411e179`. This identifies the research snapshot,
not an installed or validated version. G0 must pin the selected commit and all
submodules together, inspect their build/tests, and record the actual binary/image.
Do not combine moving documentation defaults with an older release silently.

## Why a GPU path still needs a geometry test

PeleC cuts the geometry out of a Cartesian mesh. Its documentation describes
small-cell state redistribution, default species repair near embedded walls,
and coarse/fine correction accounting. The default robust reconstruction is not
guaranteed second order at the wall. [P3] These are concrete verification tasks,
not evidence that the solver is unsuitable.

For this annulus, construct the two cylinders and finite core analytically. Keep
the full circumference and downstream expansion. Recheck integrated volume,
inlet/outlet/core-end/wall areas, normals and a closed uniform state. Use fluid
volume fractions in integrals, omit covered cells and masked coarse cells, and
include coarse/fine flux corrections. Check a rotated shock and a hot/fresh contact
near a wall before inferring a physical failure. Measure species/energy repairs
rather than merely testing that final values were clipped into a legal range.

First use static geometry and a fixed level layout. Then check a single refinement
interface/regrid before using moving AMR bands. Tag shock gradients AND reaction/
induction regions with a buffer; temperature-only tags can miss cold induction gas.
Measure refinement occupancy and block overhead. Adaptive meshes are an option for
saving work, not a guaranteed speedup; a broadly reacting/refined domain can erase
the benefit. Keep finest spacing sufficient for the 1D-verified chemistry model.

## Cost arithmetic: why model and mesh choices dominate

For ro=38.1 mm, ri=33.1 mm, L=76.2 mm, Lout=152 mm:

`V = pi*(ro^2-ri^2)*L + pi*ro^2*(Lout-L) = 4.3089845447e-4 m^3`.

The following are volume-equivalent cell counts, not generated meshes or memory
forecasts. The box column uses 76.2 x 76.2 x 152 mm and illustrates covered-space
cost for a Cartesian layout; actual AMR boxes, ghosts and alignment change it.

| Uniform spacing | Fluid-volume equivalents | Bounding-box cells | Illustrative dt | Steps for 189.394 us |
|---|---:|---:|---:|---:|
| 0.5 mm | 3.45 million | 7.06 million | 37.5 ns | 5,051 |
| 0.25 mm | 27.58 million | 56.49 million | 18.75 ns | 10,102 |
| 0.125 mm | 220.62 million | 451.88 million | 9.375 ns | 20,203 |

The dt column assumes only `dt = 0.3*dx/(4000 m/s)`. It is illustrative, not a
certified timestep: the solver's multidimensional characteristic sum, diffusion,
source accuracy, cut-cell treatment and AMR subcycling determine the usable dt.
Real speeds evolve. Halving uniform spacing in 3D costs roughly 8x cells and 2x
steps, about 16x explicit fluid work; chemistry iteration costs can change further.

The inherited physical half-heat-release distance is about 0.03952 mm for its
reference state/model. Even 0.125 mm exceeds that distance. The coarse grids above
are cold/performance/diagnostic examples, NOT pre-approved detonation grids. An
engine result that dies or survives there does not settle physical sustainment.
Use native 1D convergence at the actual mechanism/states to choose local spacing.

A state array lower bound with Ns species is roughly `8*Ncells*(Ns+5)` bytes in
FP64. At 27.58 million fluid cells and an illustrative Ns=12, one state is about
3.75 GB decimal. The actual solver also holds stage states, thermodynamics,
chemistry/Jacobian work, AMR ghosts and geometry; this is not a VRAM request.
Twelve species is an arithmetic example, not a selected or validated mechanism.
Measure peak GPU AND host memory; use a conservative 20% device-memory headroom
planning target and account for per-rank replicated storage.

## Accuracy-speed contract

First question: can a checked idealized premixed 3D model maintain a coupled front
after the controlled ignition ends? This is narrower than reproducing Run 937.
Retain full annulus, core expansion, compressible conservation and finite-rate
chemistry. Use thermally perfect ideal-gas species rather than the old fitted
constant-gamma surrogate. Start with slip/adiabatic inviscid walls, uniform premixed
feed, no turbulence model or radiation, and no resolved injector passages. These
choices remove wall-loss/mixing physics; they are exploratory assumptions, not
claims that the corresponding experimental effects are negligible.

Choose either mass-driven feed or plenum-driven feed, never independently impose
both. A simple prescribed mass feed can test propagation first but cannot validate
injector feedback or plenum pressure. Record this explicitly; pressure-responsive
feed sensitivity precedes an experimental sustainment claim. Preserve injected
composition, total mass/enthalpy and ignition energy/inventory across mesh changes.

Use an existing reduced methane mechanism only after comparing it against the
reference over the intended pressure/temperature/composition range. Check ignition
delay and heat-release structure as well as CJ speed; a speed match alone does not
validate kinetics. For early screening an imperfect mechanism can be retained with
its measured limitations, but grossly wrong induction or nonconservation blocks
reactive interpretation. Do not start by writing a reduction or applying arbitrary
reaction thickening. Keep detailed chemistry in cheap reference controls.

Cheap mandatory checks: thermodynamic/units consistency, shock propagation,
closed reactor, native storage/boundary budgets, finite states, actual completion,
quantified corrections, spatial and time sensitivity. Save time by deferring jets,
wall heat transfer, full turbulence studies, long averages and broad parameter
sweeps. Sparse full fields plus frequent small diagnostics reduce output cost.

For a first plausible result, report front speed, mode/count history, pressure
tracks and the relation of heat release to the shock. Require continued coupling
after ignition ends. Numerical sensitivity limits in revision 11 are project
triage rules, not measured error bars. Short observation never proves statistical
steady operation; the paper's 100 ms average is about 528 times the 189.394 us
three-passage development window before considering startup/transient removal.

## How to use eight GPUs

Start with one GPU. Test two on the same problem to validate communication and
rank/device mapping, then four/eight only when the workload warrants it. Modal
supports colocated multi-GPU containers for specified device types and notes
longer scheduling waits above two GPUs. [D1] Do not treat eight independent
containers as a tightly coupled solver by default. Multi-node clusters introduce
additional networking requirements and are unnecessary for this initial budget.

For one run, measure strong scaling: `S(n)=T(1)/T(n)`, `E(n)=S(n)/n`, with identical
problem and output. Measure total turnaround separately from integration time.
If the case fits and scaling is poor, two four-GPU runs or four two-GPU checks may
answer the next numerical question sooner. Only run independent comparisons:
mesh refinement, dt/CFL reduction, or a single boundary/ignition sensitivity. Do
not launch a dependent engine simulation while its prerequisite test is failing.

If one GPU cannot fit the representative problem, report that explicitly and
use the smallest fitting allocation as the scaling baseline; do not fabricate
T(1). Include chemistry-heavy and geometry-heavy work in the benchmark, since
an empty cold box can misrepresent the actual bottleneck. Log actual hardware;
Modal may substitute some compatible devices. Explicitly request host CPU/RAM. [D2]

Initial choice is H100-class if available promptly, with compatible A100/H200 as
options. This is a software-compatibility starting point, not a measured fastest
GPU ranking. Preserve FP64; neural-network tensor/FP8 headline throughput is not
our solver's throughput. Benchmark the assigned hardware before an eight-GPU run.

Use finite pilot timeouts, disjoint run paths and immutable manifests. Modal
execution timeouts exclude scheduling and apply per attempt. [D3] Save active
solver data to local scratch; persist completed evidence/checkpoints to a dedicated
3D storage prefix, then verify durability. Treat retries/preemption as explicit
incomplete runs until a tested checkpoint restart finishes. [D4] The CPU fallback
can also use an explicitly sized single Modal CPU container, with MPI checks,
without allocating GPUs that the executable cannot use.

## Sources checked for this revision

- P1: [PeleC repository and build/parallelism documentation](https://github.com/Pele-Suite/PeleC).
- P2: [PeleC EB verification cases](https://pele-suite.github.io/PeleC/ebverification/ebverification.html).
- P3: [PeleC embedded-boundary methods and corrections](https://pele-suite.github.io/PeleC/geometry/EB.html).
- P4: [PeleC numerical algorithms](https://pele-suite.github.io/PeleC/Algorithms.html).
- M1: [MFC source/features](https://github.com/MFlowCode/MFC).
- M2: [MFC reacting examples](https://mflowcode.github.io/documentation/examples.html) and [feature constraints](https://mflowcode.github.io/documentation/case_constraints.html).
- F1: [Fluent 2026 R1 native GPU supported features](https://ansyshelp.ansys.com/public/Views/Secured/corp/v261/en/flu_ug/flu_ug_sec_gpu_solver_supported_features.html).
- D1: [Modal GPU allocation](https://modal.com/docs/guide/gpu).
- D2: [Modal CPU/memory resources](https://modal.com/docs/guide/resources).
- D3: [Modal timeouts](https://modal.com/docs/guide/timeouts).
- D4: [Modal persistent volumes](https://modal.com/docs/guide/volumes).

Recommendations and effort checkpoints are engineering judgments from these
capabilities and our existing progress. They are not vendor benchmarks or a
claim that any candidate already reproduces Run 937.
