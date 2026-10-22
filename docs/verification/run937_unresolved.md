# RDE-001: sustained detonation unresolved for the reduced Run 937 case

**Status: OPEN.** The D1 baseline and D2 startup variant do not demonstrate
sustained rotating detonation over their 189.394 microsecond development window.
This is a known unsuccessful propagation result in the current model. The root
cause has not been isolated. Numerical validity and passing software tests do
not close this issue.

## Was this stage supposed to produce a working RDE?

Sustained detonation is the intended physical target: Mundt Run 937 reports two
co-rotating waves throughout a 0.696 s burn, with 15.84 kHz passage frequency and
1893 m/s outer-periphery speed (printed pp. 47-52, Table 3-2). The present model
has not reproduced that behavior.

The D0-D2 labels refer to short development increments: run infrastructure,
source/boundary checks, a short propagation attempt, and saved-field diagnostics.
They are distinct from the broader numbered stages in the master plan. D2 is
implemented, but broader Stage 1 physical-reference/refinement work is incomplete,
and Stage 3's sustained shock-coupled burning criterion is **not met**. The first
working, physically assessed 2D iteration has not been delivered.

The solver already includes reactive flow, chemical energy, injection and an
outlet, and supports the tested 1D detonation. It has enough machinery to attempt
2D propagation; there is no disabled switch that will simply turn on stable RDE
operation. Missing work includes physical chemistry references, fixed-chemistry
spatial sensitivity and investigation/correction of the failing case. A full
mechanism in every CFD cell is not a prerequisite established by these results.
Nor do the results prove that a one-step model can never sustain rotation.

Accordingly, stable rotation was an objective of the propagation check, not an
outcome justified in advance by the existing model. That check was unsuccessful.
Treat it as an open model/numerical investigation, not as a successful engine
simulation or a harmless startup that can be assumed to recover with more time.

## Exact affected cases and evidence

Both cases use 76-FI-5 geometry: outer/inner radii 38.1/33.1 mm, length 76.2 mm,
nominal injector area ratio 0.110, methane-oxygen equivalence ratio 1.176,
equivalent plenum 1350 kPa / 300 K, back pressure 100.2 kPa, Cd=0.76, constant
annulus, inviscid walls and the inherited one-step chemistry. The grid is
447 x 152 (actual spacing 0.500406 x 0.501316 mm); source CFL is 0.05 and flow
CFL is 0.4. Both runs stop at three reference passage intervals from startup.
The 15.84 kHz reference budgets time; it neither imposes waves nor confirms them.

| Quantity | D1 baseline | D2 startup variant |
|---|---:|---:|
| Case file | `rde_sim_starter/config.yaml` | `rde_sim_starter/cases/run937_fill_7p6mm.yaml` |
| Local run directory | `runs/d1_run937` | `runs/d2_fill_7p6mm` |
| Initial fresh-layer height | 3.8 mm | 7.6 mm |
| Initialization energy change | 5.0265 J | 9.4247 J |
| Simulated duration | 189.393939 microseconds | 189.393939 microseconds |
| Invalid states | 0 | 0 |
| Final maximum pressure | 0.450731 MPa | 0.607945 MPa |
| Sustained rotating detonation demonstrated | No | No |

The baseline remains 3.8 mm. The 7.6 mm case was one bounded startup-sensitivity
experiment, motivated by reaction moving away from the initial fresh layer.
It is not a new physical calibration or a replacement default. Height is used
only at initialization; the solver subsequently transports/reacts the fields.
Increasing it also enlarges the ignition/product masks, so this comparison does
not isolate layer thickness at fixed igniter energy. Chemistry, boundaries, mesh
and numerical implementation are identical between the two runs.

The larger startup strengthens early pressure and conversion, but late reaction
follows an extended fresh/product interface while pressure peaks weaken. Reaction
continues, so this is not total chemical extinction. Pressure-peak tracks and
threshold-based overlap are inspection aids, not proof of a shock or a detonation.

See [D1 evidence](d1_propagation.md), [D2 evidence](d2_coupling.md), and the
[committed comparison metrics](d2_coupling_metrics.json). Each local run also
preserves its configuration, calibration, initialization energy, numerical-source
hashes and software versions in `inputs.json`, plus native history, snapshots and
a checkpoint. Bulk runs are Git-ignored; the reports, selected figures, compact
metrics and reproduction commands accompany this publication.

## Parameters checked against the paper

The main geometry, mixture ratio, reference mass flux/flow and back pressure agree
with Tables 2-1, 3-2 and 4-1. The single premixed plenum is an approximation to
separate measured oxygen/methane feeds (1309.5/1399.4 kPa and 303/301 K). The
current ideal choked capacity is 267.76 g/s versus the measured 268.65 g/s; this
checks nominal capacity only, not actual transient flow or mixing.

The initial 377.9 kPa follows the paper's Eq. 4.1 fit; it is not a prescribed
measured steady chamber pressure. Eq. 4.5 gives about 3.84 mm using Run 937's
measured frequency, supporting the baseline initialization but not independently
validating the resulting wave frequency.

Surrogate inputs remain q=5.5 MJ/kg, gamma=1.23845, R=318.67 J/(kg K),
Ea/(R T1)=20 and k=2.52246e6 /s. Gamma is fitted to the paper's 2471 m/s CJ
reference. The heat release is an inherited plot estimate, not a reproduced CEA
result. No gross experimental-input transcription error has been identified;
this does not establish the suitability of the surrogate or boundary closures.

## Candidate causes and distinguishing checks

These are hypotheses, not established explanations or instructions to tune for
an attractive rotating wave.

| Candidate | Evidence or reason to investigate | Useful distinguishing check |
|---|---|---|
| Numerical mixing and reaction at the fresh/hot-product interface | Late conversion follows that interface; the one-step Arrhenius law can react heated mixed states. The association alone does not establish causality. | Small pressure-balanced contact problem with reactive and nonreactive controls; measure temperature, progress and integrated conversion while refining space with chemistry fixed. |
| Spatial resolution and artificial reaction structure | The 1 mm shock-to-50% length spans only two 2D cells. The surrogate's shock-to-90/95% lengths are 3.140/4.177 mm. No spatial convergence is established. | Fixed-chemistry refinement of the contact and propagating-front problems, then one bounded 2D comparison if justified. Do not alter rate constants with the grid. |
| Thermochemistry/ignition response | Constant gamma and gas constant, fitted CJ speed and selected activation energy do not validate post-shock states or induction. | Reproduce physical CJ/ZND/heat-release references; compare with the surrogate at documented states before changing its kinetics. |
| Injection and outlet reduction | Separate impinging feeds, mixing, backflow and the expanded downstream duct are unresolved. Sonic-plane algebra is checked, but the effective model and outlet response are not physically validated. | Check replenishment and axial characteristics; test a justified downstream extension/outlet alternative while preserving the other physical inputs. |
| Initialization and mode selection | The two starts differ in fuel inventory and ignition energy as well as layer height. Neither sustains the target state. | If revisited, separate igniter geometry/energy from layer height and record both. A larger ignition alone has not fixed the tested case. |

The 1D source-step halving result changes speed by only 0.0222 m/s, and the
closed-reactor tests show second-order temporal convergence for selected states.
This supports those time-integration checks; it does not establish 2D spatial
convergence or eliminate every time-discretization concern.

## Next work and what counts as a fix

1. Establish the controlled contact/refinement evidence above. A numerically
   broadened reactive interface is not a resolved physical flame-speed prediction.
2. Complete the Run 937 physical-reference subset of G0: Cantera with SDToolbox
   for CJ/frozen post-shock/ZND calculations using the paper's GRI-Mech 3.0
   mechanism; reproduce the CEA CJ-equilibrium heat-release calculation, or label
   an alternate equilibrium package/database as an independent cross-check.
   Record versions, mixture/state, induction definition and convergence. A
   constant-volume reactor is an auxiliary check, not a substitute for ZND.
3. Use those results to select a specific correction or bounded 2D resolution/
   boundary experiment. A two-step induction/reaction model remains a candidate,
   requiring source/event-timing and mixed-state tests; it is not a proven cure.
4. Reassess the same documented case with pressure and reaction fields together.
   A fix must demonstrate continuing shock-associated heat release after ignition
   across multiple observed passages, preserve state validity and budgets, and
   include an appropriate sensitivity check. Document any changed physics,
   resolution, boundary or initialization. Exact experimental wave count is a
   subsequent comparison, not something to impose to force success.

Keep the existing bounded-run policy (three reference intervals; a justified
extension of the same saved run to five total). If that window cannot support a
claim, report the claim as unresolved/inconclusive rather than inferring a steady
state. Closing the short-propagation issue would still not establish long-term
stability or agreement with the paper's last-100-ms pressure averages.

Do not shorten reaction lengths until a wave survives, double-count chemical
energy, hide invalid states with clipping, interpret pressure tracks alone as
detonation, or treat matching a fitted CJ target as independent validation.
