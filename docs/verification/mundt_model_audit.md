# Run 937: paper and implementation audit

October 22, 2026. **RDE-001 remains OPEN. No new CFD, contact, or thermochemical
study was run for this audit.** This review supersedes the immediate refinement
recommendation in the D3 report. It checks the original paper, current source,
saved inputs, and previously completed D1–D3 evidence. Production code, case
parameters and calibration remain unchanged.

Primary source: [Mundt2023.pdf](../../Mundt2023.pdf), *Geometric Scaling of
Cylindrical Rotating Detonation Rocket Engine Combustors*. All page numbers below
are **printed** pages; add 16 for the PDF page. Relevant complete pages and the
geometry, injector, ignition and thermochemistry figures were inspected.
[Audit arithmetic and source hashes](mundt_model_audit.json) preserve the exact
files reviewed. Model details refer to [config.yaml](../../rde_sim_starter/config.yaml),
[calibrate.py](../../rde_sim_starter/calibrate.py),
[physics.py](../../rde_sim_starter/physics.py),
[solver.py](../../rde_sim_starter/solver.py) and
[run.py](../../rde_sim_starter/run.py).

## Assessment

The nominal geometry and tabulated operating point were largely transcribed
correctly. The substantial differences are in **model construction**: a thickened
one-step gas model, uniform premixed injection, omitted downstream expansion,
and an artificial initial charge/igniter. The paper does not validate these
choices as a CFD reconstruction of Run 937.

Run 937 experimentally sustained two co-rotating waves. Our two short starts did
not demonstrate sustained shock-coupled burning. That physical milestone remains
unmet, but it was too strong to imply that the current choices should already
reproduce the experiment simply because the reactive solver runs and its software
tests pass. The paper neither guarantees that this surrogate will sustain nor
shows that missing 3D physics is the reason it fails. The cause remains unresolved.

## 1. What matches, and what each number means

| Quantity | Paper | Current implementation and assessment |
|---|---|---|
| Annulus | Table 2-1, p. 28: outer diameter 76.2 mm, gap 5 mm, length 76.2 mm | Outer/inner radii 38.1/33.1 mm and length 76.2 mm match. Unrolled width is 223.6814 mm; width × gap equals the annular area exactly, 1118.407 mm². This preserves area, not radial dynamics. |
| Injector area | Table 2-1 and p. 34: 72 pairs, fuel/oxygen diameters 0.79/1.24 mm, nominal total opening/annulus area 0.110 | Nominal area ratio matches. Individual holes, angles and mixing are absent. Rounded hole diameters need not reconstruct the nominal ratio exactly. |
| Mixture and flow | Table 3-2, p. 52: methane/oxygen, phi 1.176, 268.65 g/s, 240.21 kg/(s m²) | Match as reference inputs. Actual CFD injection is predicted by a plenum law; the target flow is not simultaneously imposed. |
| Separate feeds | Table 3-2: oxygen/methane plenums 1309.5/1399.4 kPa and 303/301 K | Retained as metadata. Active boundary uses one equivalent premixed plenum at 1350 kPa and 300 K. Its effective Cd = 0.76 is inherited, not independently established by this paper. |
| Back pressure | Table 3-2: 100.2 kPa; facility described pp. 23–24 | Number matches, but applying it directly at the annulus end is an additional assumption; see §4. |
| Pre-detonation pressure | Eq. 4.1, pp. 72–74: empirical estimate from mass flux and phi | Correct substitution gives 377.917 kPa. Measured front-end mean is 368.5 kPa. The 2.56% difference is between a fitted estimate and a measurement, not a transcription error. Applying the fit uniformly to startup gas is our choice. |
| Refill height | Eq. 4.5, pp. 77–78: inferred operating height using measured passage frequency | Gives 3.836 mm with our fresh-mixture gas constant and 300 K. It is not a measured startup charge or an independently prescribed steady layer. Setting an initial mask to 3.8 mm is our choice. |
| Wave data | Table 3-2: two waves, 15.84 kHz, 1893 m/s outer-periphery speed, 2471 m/s calculated CJ reference | Frequency only budgets the current run duration. Wave count is reference metadata. Our unrolled coordinate uses mean radius: 1893 m/s at the outer radius corresponds to about 1768.8 m/s at the mean radius for the same angular speed. Do not compare raw linear speeds at different radii. |

The single-plenum ideal choked capacity is 267.756 g/s, 0.33% below the measured
flow. That is an algebraic capacity check using the selected Cd, not independent
validation of transient delivery, separate-species fluxes or mixing. With the
current constant gamma, its sonic-plane temperature and pressure are 268.04 K
and 752.09 kPa; the supplied 300 K is a reservoir temperature.

The 293 K initial engine temperature in Table 3-2 is not a requirement to replace
the paper's 300 K fresh-gas reference. The roughly 5.5–6 MPa orifice pressures in
that table are upstream of separate flow-metering critical nozzles, not the
combustor plenum pressures. No such replacement is justified.

## 2. Chemistry and gas properties are approximations we introduced

Mundt's Eq. 1.11 (p. 9) presents a one-step Arrhenius law in introductory ZND
theory. It does **not** supply or validate our activation energy, pre-exponential
factor, constant gamma, or artificially enlarged reaction length for Run 937.
The paper's later physical calculations use premixed CH4/O2, GRI-Mech 3.0,
Cantera and SDToolbox at 300 K and estimated pre-detonation pressure (pp. 74–75).
NASA CEA supplies CJ-equilibrium product compositions for heat release, combined
with NIST formation enthalpies and molecular weights (Eq. 4.2, pp. 76–77).

Our production model uses constant R = 318.673 J/(kg K), constant gamma =
1.23845, q = 5.5 MJ/kg, Ea/(R T1) = 20 and k = 2.52246e6 /s. Gamma is fitted
to the tabulated 2471 m/s CJ speed; k is selected for a 1 mm half-reaction length.
These fits cannot independently validate wave speed or reaction structure.
The single progress variable cannot represent induction chemistry or changing
species thermodynamics in the same way as the physical mechanism.

The **already completed** [D3 reference](d3_investigation.md) quantifies the
differences; none of the following was recalculated for this audit:

| Quantity | Current surrogate | D3 Cantera/SDToolbox reference |
|---|---:|---:|
| CJ speed | 2471 m/s, fitted | 2531.86 m/s |
| Heat release | 5.500 MJ/kg, inherited estimate | 5.41847 MJ/kg, independent GRI equilibrium cross-check |
| CJ temperature | 4885.15 K | 3994.14 K |
| Shock-to-half-heat distance | 1.000 mm | 0.03952 mm |
| Shock-to-95%-heat distance | 4.177 mm | 0.05108 mm |

The 2.46% difference between our physical CJ calculation and the paper's tabulated
CJ value remains unreconciled. NASA CEA itself has not been run. Similar total
heat release and CJ speed do not establish similar reaction timing or partially
mixed-state behavior. The current 0.5 mm mesh gives only about two cells to the
surrogate half-reaction distance; substituting the physical length on this mesh
would not resolve it. The surrogate's reaction tail is comparable to the inferred
refill height. This is a reason to assess the model, not a proven extinction rule.

The inherited 0.8 mm cell-size and 5.5 MJ/kg heat-release values are approximate
plot estimates, not exact Run 937 table entries. Mundt's cell-size method uses
the time of maximum dT/dt, post-shock velocity and a factor of 29 (pp. 74–75).
It is not the same as half-heat distance or a measured cell width in our CFD.
Mundt also notes that this method can underestimate experimental cell size.
The h/lambda >= 4.5 comparison on p. 90 concerns a literature guideline for
efficient thrust; the paper explicitly treats it as a guideline and lacks its
own thrust measurements. It is not a universal sustained-detonation threshold.

Stored chemical energy and the source term are internally consistent in the
current code: progress converts chemical to thermal energy without adding it
again to total energy. This audit identifies no new double-counting error.
The D3 contact controls already demonstrate mesh-dependent reaction in numerically
mixed fresh/product cells. Mundt's Fig. 1.10 (p. 13) discusses real interface
burning, but our inviscid numerical mixing is not a validated model of that flame.

## 3. Injection differs substantially from the hardware

The paper says fuel and oxygen first meet **inside the combustor** (p. 24).
Its premixed assumption on p. 74 concerns the CJ/ZND reference calculation,
not the experimental injector boundary.

For Run 937, all 72 impinging pairs have holes inclined 30 degrees to the engine
axis, meeting 2.16 mm above the injector face at a 71.2 mm impingement diameter
(Table 2-1 and §2.2.4, p. 34). The impingement height is approximately 57% of our
requested initial layer height. Treating mixing as complete at the face is
therefore a substantial near-injector approximation. The “radial” feed entries
in Table 2-1 describe feed passages, not a contradiction of the 30-degree holes.

Our boundary distributes premixed gas uniformly around the annulus, injects
axially, blocks inflow when chamber pressure reaches the fixed plenum pressure,
and suppresses reverse flow. It has no separate-species mixing, resolved jets,
plenum dynamics or independent injector recovery delay. It accounts for open
and closed face pressure and has tested sonic/unchoked limits within this
idealization. Those checks do not validate the effective closure against the
impinging injector. Mundt's literature review highlights mixing, recovery and
plenum coupling even for nominally choked injectors (pp. 15–17).

These omissions can change the amount, location, temperature and composition
of detonable gas. Their net effect on this failed run is not determined by the
paper. Do not assume adding imperfect mixing will necessarily improve propagation,
or apply a standalone cosine correction to axial momentum without a consistent
mass, area, enthalpy and mixing model.

## 4. Downstream hardware and walls are not reproduced

Figure 2.4 and §2.2.1 (pp. 29–30) show a 76.2 mm annulus inside a 152 mm outer
core. The inner core ends, leaving a cylindrical expansion. The 85.7 and 98.4 mm
pressure taps are explicitly in this expanded 76 mm section (pp. 37, 45).
The assembly exhausts into a 0.25 m duct and a 4 m³ dump tank (p. 23).

Our rectangular domain ends at z = 76.2 mm. At that face, subsonic outflow uses
a ghost-cell pressure of 100.2 kPa and supersonic outflow is extrapolated.
There is no downstream expansion, core end or facility response. The paper's
100.2 kPa back-pressure measurement does not demonstrate that this boundary
is equivalent to the omitted hardware. A zero-gradient branch does not impose
sonic flow. Normal Mach and characteristic coupling determine whether omitted
downstream physics can influence the modeled chamber; causal significance is
still unmeasured. A pressure-only ghost prescription also needs assessment if
flow reverses at the outlet.

The downstream tap pressures, 68.4 and 59.5 kPa, are spatial measurements in an
expanding flow. Neither should be substituted as an arbitrary annulus-exit
pressure to make a wave survive. A supported effective boundary or represented
expansion must precede that interpretation. Simply lengthening the same constant
annulus would not reproduce the core termination.

The physical engine uses metal walls (p. 29); the prototype has no radial
boundary layers, wall friction or wall heat transfer. The paper provides no
validated adiabatic-wall conclusion for this CFD reduction. Missing losses
limit pressure, performance and gap-scaling comparisons, but their absence alone
does not establish why this run decays. No wall coefficient should be chosen
solely to force the target wave or pressure.

## 5. Startup and comparison time were model choices

The real engine is ignited through a radial pre-detonator port at z = 73 mm
(Table 2-2, p. 37). The spark-ignited tube has length/diameter 50 and its own
approximately phi = 0.95 charge; the valve-fill and ignition sequence is described
on p. 26. It supplies a transient from outside the annulus.

Our start instead prescribes fresh gas below 3.8 mm, 1500 K products above it,
a 20 mm circumferential product strip, and one 10 mm hot patch within the lower
layer. The patch is at twice the surrogate CJ pressure (21.903 MPa), CJ
temperature (4885 K), and fully reacted progress; all initial velocities are
zero. This is neither the measured pre-detonator forcing nor an initialized
traveling CJ wave. Patch count is one by choice; observed two-wave operation is
an outcome to assess, not a reason to impose two waves and call them predicted.

The D2 7.6 mm variant changed initialization only and also increased the net
initialization energy change from 5.0265 to 9.4247 J. It did not independently
isolate fill height, and it did not establish sustained rotation. Those energies
are changes relative to the code's pre-mask state, not measured igniter energies.

**New static finding:** cell-center masks change the discretized initial charge
when only requested spacing changes. Basic cell counting and energy arithmetic,
without building or advancing a solver, give:

| Startup quantity | Saved 0.5 mm grid | Proposed 0.25 mm grid, not run |
|---|---:|---:|
| Cells, circumferential × axial | 447 × 152 | 895 × 305 |
| Actual axial spacing | 0.501316 mm | 0.249836 mm |
| Lower-layer rows before ignition masks | 8 | 15 |
| Represented layer height | 4.010526 mm | 3.747541 mm |
| Remaining fresh-mixture mass after masks | 15.3509 mg | 14.3283 mg |
| Net initialization energy change | 5.02651 J | 4.58984 J |

Thus the previously proposed refinement would start with about 6.7% less fresh
mixture and 8.7% less added net energy. It remains a possible sensitivity test,
but not an isolation of resolution at identical initial inventories. The next
case specification must control or explicitly quantify this difference. A
conservative cell-average initialization is a candidate implementation change;
it would need its own checks and a new comparable coarse baseline. Do not silently
rewrite saved inputs or compare a changed initializer as if only mesh changed.

Run 937 burned for 0.696 s; reported values average the last 100 ms (p. 52).
Our entire record is 189.394 microseconds from an artificial startup, 528 times
shorter than that averaging window. Figure 2.3 shows early ignition images on a
microsecond scale as well as a much later image; the separate 10–20 ms delay
from command to visible ignition is not an internal CFD settling requirement.
Neither observation guarantees our case should settle by 189 microseconds, nor
justifies assuming more time will rescue a decaying wave. Keep the existing
bounded-run policy and label unsupported steady-state claims inconclusive.

Pressure taps have specified axial locations and clocking (p. 37), while the
current diagnostic takes circumferential cell-center means and axial interpolation.
For startup or unsteady modes these are different measurement operators. A
short initial ring mean cannot be claimed to reproduce the paper's last-100-ms
wall-pressure mean.

## 6. Does this require 3D?

Mundt explicitly discusses cellular fronts, curved-channel compression at the
outer wall and expansion at the inner wall (pp. 10–12). Our circumferential–axial
unrolling drops radial dynamics, radial wave structure and jet impingement.
The ratio gap/mean radius is 0.1404: choosing this engine as the most favorable
thin-annulus starting point among the studied configurations is a project
approximation, not an asymptotic accuracy guarantee supplied by the paper.

Two distinctions matter. First, the curved-channel “2D” studies cited on p. 12
retain the curved gap in their plane; they are not our axial–circumferential
reduction. Second, the unrolled drawing on p. 13 is a conceptual illustration,
not validation of our equations, chemistry or boundaries. The paper does not
establish that Run 937 requires a 3D computation before any sustained rotating
detonation can be modeled.

As separate context, [JAXA's 2020–2021 project report](https://www.jss.jaxa.jp/en/ar/e2020/14259/)
reports propagating CH4/O2 rotating detonations in 2D nonpremixed simulations of
a different 101 mm combustor, with resolution-dependent agreement with measured
speeds. Its figures cite non-peer-reviewed conference work. It demonstrates
that 2D is not intrinsically incapable of this behavior; it does not validate our
constant-gamma one-step model or predict Run 937.

**Decision:** retain 2D as an explicitly limited diagnostic model while assessing
its chemistry, injection, outlet and startup assumptions. Do not identify 3D as
the established cure. A 3D backend can represent omitted radial geometry, but
adding that dimension does not repair unsuitable kinetics or boundary conditions.
Matched geometry and dimensional sensitivity remain necessary before quantitative
claims about gap effects or experiment fidelity.

## 7. Consequences for the next implementation increment

This is a completed source audit, not a completed causal investigation. The
[master plan](../../first_sim_plan.md) now requires a **case-definition step
before new studies**, replacing the automatic launch of a finer 2D grid:

1. Specify the next case as a controlled test of the present surrogate or a
   physical-model revision. Record reported inputs, fitted values, and modeling
   choices separately. Preserve the existing failing baseline as evidence.
2. Define and check the initial inventory/energy comparison on both meshes.
   If initialization changes, provide a comparable coarse case. Do not interpret
   a coupled mesh/startup change as a pure resolution effect.
3. Assess the surrogate's reaction structure and mixed-state response against
   existing D3 evidence; document acceptance limits or the need for replacement.
   Reconcile the physical CJ reference and CEA convention separately from tuning.
4. Specify what the equivalent inlet and truncated outlet are intended to
   approximate, including recovery/mixing assumptions and the omitted expansion.
   Choose one discriminating change from this assessment and existing fields;
   do not change chemistry, boundaries and startup together to obtain a wave.
5. Only after that specification, execute the bounded comparison justified by
   it, retaining state validity, native budgets, fresh-gas delivery, normal exit
   Mach and pressure/reaction coupling. Any new chemistry first requires its
   reactor, timing, mixed-state and 1D checks. Broad figure campaigns remain deferred.

The requested 0.25 mm YAML was prepared only in temporary staging before the
user's pause; it was not run or installed into the repository. No new studies
are launched as part of closing this audit. The existing 59-test D3 result is
prior software verification, not a new test result or validation of the physical
assumptions above. Closure of [RDE-001](run937_unresolved.md) still requires
continuing shock-associated heat release with appropriate sensitivity evidence.
