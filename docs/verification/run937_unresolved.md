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

The D0-D3 labels refer to short development increments: run infrastructure,
source/boundary checks, a short propagation attempt, and saved-field diagnostics.
They are distinct from the broader numbered stages in the master plan. D3 is
implemented, but broader Stage 1 physical-reference/refinement work is incomplete,
and Stage 3's sustained shock-coupled burning criterion is **not met**. The first
working, physically assessed 2D iteration has not been delivered.

The solver already includes reactive flow, chemical energy, injection and an
outlet, and supports the tested 1D detonation. It has enough machinery to attempt
2D propagation; there is no disabled switch that will simply turn on stable RDE
operation. D3 now supplies the nominal physical chemistry reference and small fixed-chemistry
spatial tests. Remaining work includes 2D spatial sensitivity, surrogate assessment
and investigation/correction of the failing case. A full
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

The [October 22 paper/model audit](mundt_model_audit.md) is the detailed source
check, with printed-page citations and source hashes. No new studies were run.
It identifies model-construction differences rather than a gross transcription
error: the paper does not validate our one-step kinetics/EOS, uniform premixed
feed, annulus-end boundary, or hot-patch initial state. Its discussion of radial
curvature and mixing does not establish that a 3D solver is the missing cure.

The main geometry, mixture ratio, reference mass flux/flow and back pressure agree
with Tables 2-1, 3-2 and 4-1. The single premixed plenum is an approximation to
separate measured oxygen/methane feeds (1309.5/1399.4 kPa and 303/301 K). The
current ideal choked capacity is 267.76 g/s versus the measured 268.65 g/s; this
checks nominal capacity only, not actual transient flow or mixing.

The initial 377.9 kPa follows the paper's Eq. 4.1 fit; it is not a prescribed
measured steady chamber pressure. Eq. 4.5 gives about 3.84 mm using Run 937's
measured frequency. This estimates an operating refill height, not a measured
startup charge; adopting it as initialization is our assumption and cannot
independently validate the resulting wave frequency.

Surrogate inputs remain q=5.5 MJ/kg, gamma=1.23845, R=318.67 J/(kg K),
Ea/(R T1)=20 and k=2.52246e6 /s. Gamma is fitted to the paper's 2471 m/s CJ
reference. The heat release is an inherited plot estimate, not a reproduced CEA
result. No gross experimental-input transcription error has been identified;
this does not establish the suitability of the surrogate or boundary closures.

## Candidate causes and distinguishing checks

The [layer-diagnostic review](layer_diagnostic_review.md) checks the subsequent
external diagnosis against saved data. Thin-layer survival and ignition adequacy
are the leading controlled-test questions. C1 row/direction equivalence and C2
formed-profile verification now pass. C3 has a coarse thin/thick contrast, with
refinement still in progress; a matched blast/profile control remains pending. Outlet isolation and negligible
engine contact losses have not been established by the arguments in that diagnosis.

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

## D3 evidence and next work

The [D3 investigation](d3_investigation.md) strengthens the numerical-contact and
surrogate-structure hypotheses without isolating the 2D failure's root cause:

- Reactive contact conversion at 20 µs decreases from 726.44 to 457.79 to
  289.78 J/m² as spacing decreases from 0.5 to 0.25 to 0.125 mm. Frozen controls
  release no heat and preserve uniform pressure. Numerical mixing can produce
  reaction in this model; this isolated experiment does not prove it quenches RDE rotation.
- The fixed-model 1D front fits are 2456.05/2490.16/2522.45 m/s over 40–95 µs;
  the later 65–90 µs window gives 2457.33/2477.59/2495.97 m/s. Spatial convergence
  and settled speed have not been established by the former single-grid CJ match.
- Cantera/GRI-Mech with SDToolbox gives 2531.86 m/s, 5.41847 MJ/kg,
  3994.14 K at CJ, and a 0.03952 mm half-heat distance. The thickened surrogate
  has similar nominal heat release but different thermodynamics and structure.
  This is an independent physical reference at the documented state; the
  paper's tabulated CJ difference and exact NASA CEA replication remain open.

## Controlled evidence after D3

[C1–C3 evidence](controlled_2d_progress.md) narrows the investigation:

- C1's 95 µs matched 1D/multirow/rotated runs have identical saved fields and
  fronts. This excludes the specific coordinate/row-path errors tested.
- C2's conservative formed profile propagates through 40 µs on three grids,
  with continued near-front reaction and speeds approaching the surrogate CJ
  value. Jump, inventory, table and source-step checks pass; remote-boundary
  characteristic cones remain clear of the measured reaction region.
- C3 at 0.5 mm: a 3.8 mm formed wave loses leading shock/reaction coupling by
  40 µs, while a 15 mm layer retains strong coupling near its wall/middle.
  Both are valid and conservative with positive remote-boundary margins.
  Interface burning remains visible. The 0.25 mm comparisons are in progress;
  no converged critical-height threshold or unique root cause is established.
- These are isolated unforced propagation controls. They show that the declared
  model can propagate in 2D and can lose coupling in a thin layer even when
  initialized with a formed wave. They do not reproduce the complete engine,
  isolate all numerical mixing effects, or exclude a separate initiation problem.

**Next work:** finish C3 refinement and review the combined fields, reaction,
budgets and causality evidence before conditional C4 initiation comparison.
Keep chemistry frozen across the comparison. Do not launch an engine rerun
merely because the isolated thick layer supports a wave. The [reviewed plan](../plans/controlled_2d_tests.md)
contains the remaining gates. This session commits only to main; independent
3D preparation is not blocked by this investigation.

A fix must demonstrate continuing shock-associated heat release after startup,
with state validity, conservation and sensitivity evidence. Neither numerical
validity nor a visually rotating pressure peak alone closes RDE-001.

Keep the existing bounded-run policy (three reference intervals; a justified
extension of the same saved run to five total). If that window cannot support a
claim, report the claim as unresolved/inconclusive rather than inferring a steady
state. Closing the short-propagation issue would still not establish long-term
stability or agreement with the paper's last-100-ms pressure averages.

Do not tune reaction lengths solely until a wave survives. A predeclared,
physically motivated reaction-length sensitivity study is allowed: verify the
source, resolve its structure, freeze chemistry within each mesh comparison and
retain failure evidence. A model-specific critical layer height does not itself
validate the chosen chemistry. Do not double-count chemical energy, hide invalid
states with clipping, interpret pressure tracks alone as detonation, or treat
matching a fitted CJ target as independent validation.
