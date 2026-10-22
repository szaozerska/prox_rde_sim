# C5b–e quarter-length reaction experiment

October 22, 2026. Predeclared protocol: [controlled plan](../plans/controlled_2d_tests.md).
Status: C5b–d reactor/planar/contact verification passed; C5e two-mesh layer runs in progress. C6 not launched.

The independent investigation correctly motivates testing a shorter surrogate.
Its confirmed-root-cause, universal h/L50 threshold, outlet timing and 12x source
step slack claims are not adopted. The original plan permitted this sensitivity;
this increment makes that option concrete. C6 remains gated.

Selected L50=0.25 mm, k=4 times baseline, unchanged activation energy and EOS.
Production defaults and previous runs remain unchanged. Initial reactor/planar/
contact gates precede the 10 us, two-grid, 3.8 mm formed-layer experiment.
The current SSP-RK2/source-slope cap is retained. Full-scale physical chemistry,
GPU work and an engine run are outside this experiment.


## Implementation and verified prerequisite results

`short_reaction.py` creates a copied calibration with k=10,089,856.546/s,
L50=0.25 mm, L90=0.784987 mm and L95=1.044317 mm. Other constants are unchanged.
It gates the layer pair on saved verification status, calibration and source
fingerprints. `controlled.py` accepts an explicit remote-domain scale and records
it; default C1–C4 behavior is retained, and continuation must preserve the scale.
No production solver, source integrator, default configuration or calibration changed.

- Profile jump residuals: maximum 7.46e-13; independent quadrature confirms
  L50, L90 and L95. Conservative profile states are unchanged by the rate rescale.
- Cold/warm/shock-heated homogeneous reactors: maximum progress error 7.62e-6
  at source fraction .05, decreasing approximately fourfold at .025. Total
  energy is unchanged; zero invalid states. Tightening DOP853 tolerances changes
  the reference by at most 2.29e-10.
- Filled strips through 10 us: late (5–10 us) speeds 2478.153/2472.973 m/s
  at 0.125/0.0625 mm versus model CJ=2471 m/s. Coarse half-source-step speed
  is also 2478.153 m/s. Shock/reaction separation at the endpoint is
  0.375/0.1875 mm; all source/grid cases retain near-front reaction. Maximum
  budget residual <2e-14, zero invalid states, positive causal margins.
  These are surrogate numerical checks, not independent validation of fitted CJ.
- Moving contact through 5 us: reactive conversion 181.745/114.582 J/m2 at
  the two meshes; frozen conversion is zero. Contact burning is still numerical
  and mesh dependent. This decrease is not an engine-loss bound or convergence.

Metrics and full histories: [verification](c5_short_verification.json).
Original stopped gate: [preserved record](c5_short_initial_gate.json).
Raw fields stay under ignored `runs/c5_short_verify*` directories.

## Issue encountered and corrected

The initial reactive-contact gate required the far-field pressure to remain at
its initial value. It stopped at a relative change of 1.426476e-6. Independent
homogeneous integration predicts 1.426476e-6 from the model's nonzero 300 K
Arrhenius reaction. This was an incorrect diagnostic assumption, not evidence
of a reflected disturbance or unstable solver. Comparing pressure, density,
velocities and progress against that evolving reference gives <2.2e-15 scaled
error. A deliberately perturbed saved boundary fails the new check.

The initial failure remains recorded. The corrected verification reused the three
completed planar and two completed contact runs after matching inputs and all
simulation-source hashes; only the missing fine contact pair advanced CFD.
No timestep, chemistry, flux or numerical tolerance was relaxed. Two test-command
invocations initially used the repository root instead of the documented starter
working directory; rerunning from the starter fixed those invocation errors.

## Tests and running layer protocol

- Focused harness/import checks: 17 passed, 23.6 s (`c5_short_tests.log`).
- Regression suite before the contact-gate correction: 77 tests, 76 passed and
  one opt-in reactive baseline skipped, 75.4 s (`c5_short_full_tests.log`).
- After the diagnostic correction: five focused tests passed, including the
  independent reactor and injected boundary-error check (`c5_short_gate_tests.log`).
- Actual corrected reactor/planar/contact diagnostic gates all passed.

The layer pair uses four Numba threads on the eight-logical-CPU, 16 GB host;
verification used two. This only changes execution parallelism. The fixed local
model, 3.8 mm layer, 0.125/0.0625 mm meshes, 10 us cap, causal bounds and conserved
initialization are predeclared in the plan. No automatic engine run follows.
The coarse/fine domains have about 261,000/1,045,800 cells. The source cap is
about 3.61 ns, so each takes about 2,770 steps. Results remain pending here.
