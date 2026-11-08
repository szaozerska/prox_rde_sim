# RDE simulation planning review

Planning review of revision 3. No simulation code or configuration was changed and no dependencies were installed during the review. At the owner's subsequent request, this report was moved into the repository as `sim_plan_review.md`; extracted paper text, rendered pages, and scratch calculations remain under `/private/tmp/prox_rde_review_20261021/`. The review has a dedicated `.gitignore` entry to preserve the original request to keep it out of Git. Nothing has been committed or pushed.

**Current implementation plan:** [first_sim_plan.md](first_sim_plan.md), revision 9. The latest [paper/model audit](docs/verification/mundt_model_audit.md) updates the requirements before further studies. It incorporates this review, the short-test overnight scope, separate physics/test/plot files, and the follow-up requirements for replaceable CFD backends, explicit 2D gap limitations, parametric 3D, CAD import after the first working iteration, and graph validation against Chapters 3–4. Findings and original line references below describe [revision 3](docs/plans/first_sim_plan_rev3.md), preserved unchanged. The milestone sequence below is historical; follow the current plan.

This review incorporates the owner's follow-up: automatic replication of the full chemical/wave stability classification is a lower priority. The first version should make sustained propagation, extinction, wave count, and speed easy for a human to inspect. Numerical checks remain necessary so those pictures have meaning.

## 1. Recommendation

**Keep the starter as a small 2D research prototype, revise the plan before implementation, and make the later CAD solver an explicit second development track.**

The plan has a sensible foundation: start with a simpler geometry, separate cases from solver code, verify basic numerics, compare with experiment, and expose intermediate results. However, several statements overestimate what the proposed physics can establish, and two of its immediate stage gates are undermined by its own equations.

The most consequential findings are:

1. **The proposed two-step reaction zone is much longer than claimed.** Its shock-to-90%-reaction distance is about 1.65 mm, not about 0.75 mm; the distance to 95% is about 2.27 mm. These values follow from the plan's own calibrated model.
2. **Changing chemistry lengths when changing the mesh invalidates the proposed grid-convergence comparison.**
3. **A zero-gradient outlet does not impose a sonic exit.** Choking must be supported by the solution and an outlet sensitivity check.
4. **The proposed induction clock does not guarantee that numerical contact burning disappears.** Its example overlooks the remaining induction time of already partially advanced gas.
5. **The first iteration does not accept or simulate CAD geometry.** It accepts four manually supplied parameters and discards several features directly relevant to the requested predictions.
6. **Mundt provides pressure and wave data, but no measured thrust or torque.** A closely related additional experiment supplies a practical thrust benchmark; torque requires either a matched external benchmark or explicit treatment as an unvalidated estimate.

The first deliverable can still be worthwhile: a verified, simplified annular-flow simulation with an honest visual display, pressure comparisons, a thrust estimate, and a friction-model torque estimate. It should not yet be advertised as a predictive arbitrary-CAD engine simulator.

## 2. Sources and scope of inspection

Local source identifiers used below:

- **[P]** [Original plan — revision 3](docs/plans/first_sim_plan_rev3.md). It was named `first_sim_plan.md`, rather than `first_plan_sim.md` in the request.
- **[M]** [Mundt2023.pdf](Mundt2023.pdf), 204 PDF pages. Printed page 1 is PDF page 17; the plan's +16 convention is correct.
- **[S]** [rde_sim_starter](rde_sim_starter): all five Python files, configuration, status, saved calibration and test JSON, and all three saved PNGs.
- At the original review, the root README contained only the project title. The starter is a directory inside the enclosing repository; no independent starter Git repository or dependency manifest was found.

I read the thesis's substantive Chapters 1–5, checked its uncertainty appendix, inspected relevant tables and figures as rendered pages, and sampled the engineering drawings and wave-mode examples in Appendices A and B. This is a physics/planning review, not a tolerance-by-tolerance manufacturing audit of every Appendix A drawing.

I independently evaluated selected equations using scratch calculations, including the two-step ZND distances, induction times, geometry factors, reference pressure, and fill height. **I did not rerun the CFD solver or reproduce the detailed-chemistry calculations.** Numba and Cantera are absent from the Python environment inspected. The starter's reported successful runs are therefore retained as supplied evidence, not newly reproduced test results.

External primary sources consulted:

- **[E1]** Bennewitz et al., *Experimental validation of rotating detonation for rocket propulsion*, Scientific Reports 13, 14204 (2023), DOI **10.1038/s41598-023-40156-y**. Full article and PDF inspected.
- **[E2]** Sawada et al., *Torque Around Axial Direction on Rotating Detonation Engines*, Journal of Propulsion and Power 38(1), 59–70 (2022), DOI **10.2514/1.B38374**. Author-institution abstract inspected; detailed apparatus and data not independently audited.
- **[E3]** Menikoff, Lackner, and Bukiet, *Modeling flows with curved detonation waves*, Combustion and Flame 104(3), 219–240 (1996), DOI **10.1016/0010-2180(95)00106-9**. Author-institution research record inspected.
- **[E4]** Caltech Explosion Dynamics Laboratory, *Shock and Detonation Toolbox*, official description, capabilities, and release notes.
- **[E5]** PeleC official repository, now under **Pele-Suite/PeleC**, README and `Docs/sphinx/geometry/geometry_init.rst`.
- **[E6]** Harroun, Heister, and Ruf, *Experimental Validation of Nozzle Flow Simulations for Rotating Detonation Rocket Engines*, AIAA SciTech 2020; NASA NTRS document **20230009329**. Official research abstract inspected.

## 3. What the existing plan gets right

**The 76-FI-5 / Run 937 starting case is well chosen.** Its relatively thin annulus is a better candidate for an unrolled approximation than the small, wide-gap engines. Table 3-2 supplies unusually complete inputs and results. The plan correctly transcribes the main geometry, flow, equivalence ratio, plenum conditions, axial pressures, frequency, wave count, and CJ speed. [P D3–D11; M pp. 28, 37, 52, 80]

**The area-preserving annulus construction is correct.** With mean radius \(r_m=(r_o+r_i)/2\) and gap \(g=r_o-r_i\), the cross-sectional area is exactly \(2\pi r_m g=\pi(r_o^2-r_i^2)\). This preserves mass-flow conversion; it does not preserve radial flow physics. [P D7, A.7]

**The conservative chemical-energy formulation is internally sensible.** Storing unspent chemical energy in total energy and increasing reaction progress without an additional energy source is a consistent calorically perfect reactive-Euler formulation. Adding heat again to the energy equation would double-count it. [P D16, A.4; S solver.py]

**The proposed wall-force balance is a reasonable first closure.** For a straight annulus, the inner-plus-outer lateral wall area divided by volume is exactly \(2/g\). With a skin-friction coefficient defined using \(\tfrac12\rho U^2\), the stated force-density factor follows. Retaining total energy under stationary, adiabatic wall friction is also defensible: loss of resolved kinetic energy becomes internal energy. These statements validate the formulation, not the chosen coefficient or the resulting torque. [P D16b, A.4]

**Separate analysis, saved states, and live inspection are good design choices.** Keep these, along with explicitly sourced experimental inputs and a clear separation of numerical verification from experimental comparisons. [P D2, D2b, Part 4]

## 4. Critical changes before coding

### 4.1 The two-step reaction length is miscalculated

**Priority: immediate blocker to the proposed chemistry and Stage 0 gate.**

The plan sets \(\Delta_I=\Delta_R=0.25\) mm and \(k_R=u_{VN}/\Delta_R\), then says the full reaction zone is approximately 0.75 mm and therefore about one-fifth of the fresh-layer height. [P D14, lines 290–306; A.3, lines 679–686]

There are two problems:

- For \(\dot{\xi}=k_R(1-\xi)\), \(\Delta_R\) as defined is not a distance to completion. Exact completion is asymptotic; a completion percentage must be specified.
- The shock-frame gas velocity increases substantially during heat release. It cannot be held at its initial von Neumann value when integrating the physical distance.

Using the saved calibrated values \(u_{VN}=306.03\) m/s, \(k_R=1.2241\times10^6\ {\rm s^{-1}}\), and the plan's own ZND path:

\[
L(\xi_*)=\Delta_I+\int_0^{\xi_*}\frac{u(\xi)}{k_R(1-\xi)}\,d\xi .
\]

The shock-frame velocity reaches about 1388.5 m/s at the CJ state. My resulting distances are:

| Reaction completion | Distance from leading shock |
|---|---:|
| 50% | 0.518 mm |
| 90% | 1.652 mm |
| 95% | 2.275 mm |
| 99% | 3.882 mm |

Even incorrectly holding velocity at \(u_{VN}\) gives 0.826 mm to 90%, not a well-defined 0.75 mm “full” zone. With the varying velocity, 90% completion occupies about 43% of the nominal 3.84 mm layer; 95% occupies about 59%. These are calculations for the proposed ideal planar model, not CFD predictions.

**Change:** define named lengths such as shock-to-90% and induction length; fit rate constants by integrating the actual model; report both physical reference lengths and reduced-model lengths. Reconsider whether the desired length, grid resolution, and laptop cost can be satisfied together. Do not shorten chemistry merely until a rotating wave survives.

The coarse debugging model doubles both lengths and consequently doubles these distances. Requiring that coarse model to sustain the same thin-layer wave before allowing a finer model to run can stop development for the wrong reason.

### 4.2 The grid check changes the governing model

**Priority: immediate blocker to claims of numerical convergence.**

At 0.5 mm grid spacing, the plan uses 0.5 mm chemistry lengths; at 0.25 mm, it uses 0.25 mm lengths. It then compares frequency, mode, and contact burning. Those differences combine mesh error with changed reaction kinetics. [P D14, D43; Stages 1 and 5]

The statements that under-resolution changes internal structure “not speed or pressure” are too strong. Ideal planar CJ jump conditions do not guarantee correct propagation in a numerically smeared, laterally expanding, lossy RDE. Published work explicitly identifies artificial reaction-zone thickness as a source of grid-dependent curved-detonation propagation. [E3]

**Change:** freeze thermochemistry, wall model, injection, and outlet treatment during a grid study. Refine spatial resolution and then reduce the time step independently. Explore rate/thickening changes as a separate model-sensitivity study. Check mean thrust and pressure as well as wave speed; torque needs its own convergence assessment if reported.

A 1D speed close to CJ is necessary evidence but does not establish correct 2D survival or wall loads.

### 4.3 The induction-clock fix is plausible, but its claimed guarantee is false

**Priority: high.**

A two-step induction/reaction model is a reasonable candidate. However, its ability to preserve the fresh layer has not been demonstrated. The plan's example considers a 50/50 mixture of fresh and burned gas at about 1400 K and says its induction time is about 100 microseconds, longer than the 63 microseconds between waves. [P D12]

Under the plan's own transported-scalar mixing assumption, that cell also has induction progress about 0.5. Its **remaining** time is therefore approximately 51 microseconds, not 103 microseconds, even before accounting for subsequent heating. The stated safety margin disappears. A mixed cell already contains burned progress as well; its state is not a fresh parcel with a reset induction clock.

The previous 2D failure is consistent with numerical mixing and premature reaction, but the available plot and status file do not establish one uniquely identified cause. Boundary conditions, model reaction length, ignition, and numerical diffusion must also be separated.

**Change:** verify induction completion, mixing of hot products with fresh gas, and reaction timing in controlled small cases. Do not promise that changing the reaction law automatically fixes the 2D run.

There is also a numerical event issue: clipping an induction variable at 1 inside an RK stage and then averaging it with an earlier value below 1 can leave the final variable below the reaction threshold. The proposed strict `lambda >= 1` gate needs an explicit integration design and a timing check, not an unexamined extension of the one-step update.

### 4.4 Detailed-chemistry references and the reduced gas model are mixed together

**Priority: high for quantitative predictions.**

The fitted constant \(\gamma=1.23845\) reproduces the chosen ideal CJ speed and approximate heat release. That makes it a useful surrogate parameter; it does not establish accurate thermodynamics over cold injection, shocked gas, products, and expansion. The claim that pressures, speeds, and Mach numbers are consequently “trustworthy” is unsupported. Sound speed, compressibility, injection response, and thrust depend on the thermodynamics too. [P D8–D10]

Mundt used Cantera/SDToolbox and GRI-Mech for detonation calculations, and CEA for equilibrium product composition/heat release. His induction time is taken from the ZND calculation. A constant-volume ignition calculation at a constant-\(\gamma\) surrogate VN state is not exactly the same reference calculation. Matching the definition “maximum dT/dt” does not make the paths identical. [M pp. 74–77; P D13, A.2; E4]

**Change:** maintain two explicit datasets:

1. Physical reference CJ, frozen post-shock state, ZND induction, and equilibrium thermochemistry.
2. Reduced-model parameters and its own CJ/ZND solution.

Quantify their differences before using the surrogate. Fit ignition behavior over the pressures and temperatures actually encountered, rather than making an \(R^2\ge0.98\) straight-line fit a physical law. The induction source is temperature-sensitive even though \(k_R\) is constant; source integration cannot be justified from \(k_R\) alone.

Using a guessed activation temperature if Cantera is unavailable can support a demonstration, but should not pass a stage described as reproducing the paper's chemistry.

### 4.5 A zero-gradient boundary is not a choked boundary

**Priority: high for thrust and chamber pressure.**

The observed pressure decrease downstream of the core and weak back-pressure influence support a choked-regime approximation for the selected case. They do not make zero-gradient extrapolation an implementation of choking, nor prove every outlet face is supersonic at all times. [P D26; M pp. 45, 69–71]

For locally subsonic outflow an acoustic characteristic can enter the domain. Extending the domain or treating that characteristic is then relevant. The startup specified in the plan initially has zero velocity, so a justification limited to a final supersonic exit does not cover startup.

**Change:** examine the **axial/normal** outlet Mach \(v/a\), the extent of locally subsonic or reversed flow, and sensitivity to outlet location/treatment. The current postprocessor reports total-speed Mach \(\sqrt{u^2+v^2}/a\); this is not the same choking diagnostic.

Back-pressure independence of a wave label alone is insufficient. Mundt explicitly shows that axial pressures can change even when wave number does not. The 25-FI-5 sweep cannot establish back-pressure independence for all other gap configurations. The plan also admits the 25-FI-7 point may be sensitive, contradicting its blanket claim that every test point is insensitive. [M p. 70; P D26, Part 3]

### 4.6 Injection needs an explicit averaging model

**Priority: high for fill dynamics and thrust.**

One premixed plenum replaces two feeds, different gas properties, inclined discrete holes, jet impingement, and mixing. This can be a deliberately reduced boundary condition, but it cannot be described as matching the physical injector merely because it matches total mass flow. [M pp. 24, 34–35; P D5, D24–D25]

The formula combines choked mass flow at the orifice with a velocity expanded all the way to the chamber pressure. That can be interpreted as an effective expanded-jet model, but then the jet footprint, entrainment, unresolved momentum, and pressure-force convention require explanation. It is not automatically the flux through the physical injector exit plane.

The approximately 235 K temperature follows from full isentropic expansion to the reference chamber pressure. The sonic-throat temperature using this same \(\gamma\) is about 268 K. Neither establishes a fixed bulk fresh-layer temperature after jet mixing.

**Change:** verify the boundary in nonreacting flow across blocked, subcritical, and choked conditions. Choose whether measured mass flow is imposed or plenum pressure and independently calibrated discharge coefficients predict it. If \(C_d\) is fitted to a hot-fire flow rate, mark that flow rate as a calibration target, not validation evidence. Freeze fitted parameters before testing another operating point; explain physically implausible effective coefficients rather than silently retuning them.

### 4.7 CAD scope and important missing geometry

**Priority: high for the overall product objective.**

Four scalars are enough to define this reduced rectangular problem, but do not constitute CAD ingestion. Two CAD engines with the same four scalars but different injector patterns or exit features will produce identical results by construction. [P D3, D7]

A particularly important omission is the **25-FI-3 inner-core chamfer**, which extends to the 2.16 mm impingement height to avoid blocking fuel injectors. That is in the region where the fresh layer forms, not an irrelevant exterior detail. The gap study also changes injector area ratio and jet position relative to the gap. Its behavior cannot be assigned solely to gap width or wall heat loss. [M pp. 33–35, 79–80, Appendix A.4]

For the actual CAD milestone, add: supported geometry class and file types, unit/assembly handling, extraction of connected fluid volumes, geometry repair, inlet/outlet/wall identification, mesh verification, and operating conditions supplied separately from the CAD. Material and thermal boundary data are required when wall temperatures or structural behavior are requested.

The coreless rectangle preserves area but not radial propagation, the central flow region, wall moments, or base pressure. Keep it outside the quantitative validation set. A virtual annulus used to process camera images does not justify a virtual annulus for fluid dynamics. Also, the radial surges cited on p. 70 refer to pulsing in the **cored 25-FI-5**, not an observation of the coreless configuration as stated in the plan. [P Part 3.2; M pp. 42, 69–70]

## 5. Thrust: a practical validation route

### Define exactly which force is reported

For the simplified annular exit, the proposed quantity is

\[
F_e=\int_{A_e}[\rho v^2+(p-p_a)]\,dA.
\]

This is a useful exit-stream momentum/pressure quantity. It becomes a whole-engine thrust statement only with the rest of the control volume and external loads consistently accounted for.

For example, pressure on the downstream face of the inner core can contribute a base force that the annular exit integral does not include. Exhaust expansion and base suction may matter even in a nozzleless configuration. NASA-published experimental/computational work explicitly identifies this effect. [E6]

The injection momentum term is an advective momentum contribution, not simply a pressure force on the injector plate. Plenums, supply-plane forces, and mounting-system conventions matter when comparing with a load cell.

### First verify the computation

For the plan's simplified domain, let \(P_y=\int_V\rho v\,dV\). With its force conventions,

\[
\frac{dP_y}{dt}=F_{\rm inj,check}-F_e,
\]

where \(F_{\rm inj,check}\) includes the bottom momentum flux and the signed axial wall source. Over a finite averaging window, retain the endpoint term
\([P_y(t_2)-P_y(t_1)]/(t_2-t_1)\).

The analogous mass check is \(dM/dt=\dot m_{\rm in}-\dot m_{\rm out}\). Requiring inlet and outlet equality while ignoring stored mass/momentum confuses physical transients with numerical errors.

Use the actual RK-weighted numerical boundary fluxes and source integrals for these checks. The starter instead reconstructs diagnostics from instantaneous cell-center states and duplicated injector formulas; those need not exactly equal the fluxes that updated the solution.

Then check fixed-model mesh/time-step sensitivity, averaging-window sensitivity, and a simple known-flow force case. Conservation agreement establishes correct bookkeeping; it cannot validate an incorrect physical closure.

### Then compare with an actual force measurement

**A useful additional benchmark exists.** Bennewitz et al. [E1] describe the same nominal 76.2 mm diameter/length, 5 mm gap, 72-pair architecture. Their nominal case (0.272 kg/s, \(\phi=1.1\)) gives **387 ± 2.22 N (AFRL)** and **367 ± 5.10 N (Purdue)**. See Methods/Fig. 7 and supplementary data for case definition. UW has no thrust entry.

Use one facility's documented operating point and force definition, not Run 937's inputs paired with another facility's thrust. Preserve each facility's result separately. Inspect the remaining exit/port geometry and boundary conditions when building the case.

My recommended sequence is:

1. Verify force bookkeeping on simple flows.
2. Demonstrate a sustained 76 mm rotating wave and compare its pressure distribution with Mundt.
3. Run a separately defined thrust benchmark using independently fixed model parameters.
4. Report prediction error and input/numerical/model sensitivities.
5. Test a held-out operating point before claiming predictive accuracy.

Do not tune \(C_d\), chemistry, and friction on a case and then call agreement on that same case independent validation. Until the comparison is completed, label the output **estimated annulus-exit thrust** or **estimated whole-engine thrust**, according to the implemented force model.

## 6. Wave inspection, torque, and the meaning of “stability”

### The owner's revised wave priority

For iteration 1, provide pressure and reaction-progress animations, a space–time plot, tracked wave count/speed, and markers for extinction or major mode changes. State the simulation duration. This should make the qualitative judgment straightforward without building an elaborate classifier.

Retain a minimum physics check that heat release remains associated with a propagating shock after the ignition transient. A moving pressure pulse alone is not enough. Basic numerical convergence also remains necessary.

The full 58% camera-power classification and all six-engine mode requirements can be deferred. A heat-release projection is not a calibrated luminosity model; transferring an empirical camera threshold requires separate validation. The plan's 5% noise threshold, 0.4 CJ-speed cutoff, pressure peak/mean cutoff of 5, and ±5% steadiness rule are project heuristics, not Mundt's exact definitions. [P D32, D34; M pp. 42–43]

The proposed Euler/local-reaction model also has no physical heat or species diffusion for flame propagation. Numerical mixing plus local reaction is not a validated deflagration model. Prefer the label **no sustained detonation detected** to a confident physical deflagration verdict. [P A.4]

The proposed “contact burning” diagnostic is similarly approximate: all heat release more than 2 mm in circumferential distance from a probe-row pressure peak is not necessarily contact burning. Curved/oblique fronts and the reaction tail can enter that region. The newly calculated 95% reaction distance already exceeds 2 mm. Track shock geometry and distinguish reaction tails from mixing layers, or label this simply an off-front heat-release proxy.

### Torque balance and model limitations

For axial angular momentum \(L_z=\int_V\rho r u_\theta\,dV\), neglecting other external torques and with zero inlet angular-momentum flux:

\[
\tau_{\rm engine}+\Phi_{L,\rm out}+\frac{dL_z}{dt}=0.
\]

The plan omits storage from its finite-window cross-check. Include it before deciding a torque residual is an error.

Its ideal smooth, inviscid annulus has no wall shear or azimuthal pressure torque, so a statistically stationary solution with zero injected angular momentum has zero net exported angular momentum. Local gas motion and wave motion can nevertheless be strongly azimuthal. Adding a wall-friction model allows nonzero reaction torque. The sign must emerge from the computed forces; it should not be enforced to agree with wave direction. A mirrored-ignition case is a useful symmetry check. [P D16b, D37; derivation from A.4]

A constant-\(C_f\) model can give a first estimate. It does not establish quantitative uncertainty of only a factor of two, nor guarantee torque scales linearly once the flow responds to friction. Pressure forces on nonaxisymmetric CAD features and actual boundary layers require more geometry and physics.

Mean-radius angular momentum is also a thin-gap approximation. Area preservation alone does not preserve a wall torque moment. For uniform wall shear, the wall-force effective radius is \((r_o^2+r_i^2)/(r_o+r_i)\), not exactly \(r_m\). This difference is small for 76-FI-5 and increasingly relevant for wide gaps.

### How to use the torque experiment

Sawada et al. [E2] report 0.149 ± 0.009 N m torque, 48.1 ± 0.9 N thrust, and azimuthal shear force equal to 8.8 ± 0.6% of thrust under their test conditions. These are useful external observations, **not a universal 8.8% rule**. A dimensionless ratio transfers only when the relevant physical similarity is established.

Use their result as context initially. For validation, obtain the full apparatus/conditions and simulate that case, or obtain torque measurements for the target engine. The abstract alone is insufficient to specify a matched simulation.

Mundt's Eq. 4.7 is not a measured torque. The plan is right to flag its apparent use of a shock-relative VN velocity as a laboratory-frame velocity; his detailed intermediate calculation is unavailable here, so describe this as a frame-consistency concern. In any case, \(\dot m D u\) is not the actual azimuthal kinetic-energy flux. Compute that from \(\int \tfrac12\rho v u_\theta^2\,dA\), with an explicitly defined denominator. [M pp. 98–100; P D37]

### Do not overstate “roll stability”

Torque gives angular acceleration after an inertia is specified. For constant inertia and torque, \(\dot\omega=\tau/I\). Whether a vehicle stays acceptably oriented also depends on initial rotation, burn duration, damping, controls, and other torques.

Call this output **axial torque and estimated roll response**. It is neither a vehicle stability verdict nor a structural assessment. If structural survival becomes part of the scope, add temperature-dependent material properties, thermal loads, stresses, and constraints; the thesis actually reports core failures from thermal problems. [M pp. 55–56, 105]

## 7. Additional paper/data corrections

| Plan issue | Correction or qualification |
|---|---|
| Fig. 1.1 is treated as an implied replication target | It is an illustrative design/flow image reproduced from another source. A cylinder-wrapped 2D field can emulate its presentation, but is not a 3D validation dataset. [M p. 1] |
| \(h/\lambda\ge4.5\) motivates the survival criterion and rate selection | Mundt discusses this as an external efficient-thrust guideline, explicitly not a rule, and had no thrust data to test it. It is not a universal extinction boundary. [M pp. 88–90] |
| “Effective cell size = 29 × thickened induction length” | The factor is an empirical correlation used with a particular physical ZND calculation. It does not establish the emergent cell width of an arbitrary two-step model. Treat both the physical cell-size estimate and numerical thickness as separate quantities. [M pp. 74–75; P D14] |
| 3.25 mm fill height is used almost as measured truth | It is a model-derived average, and Eq. 4.5 already contains experimental frequency. Initializing with it is allowable, but recovering it is not independent validation. [M pp. 77–79, 103] |
| Frequency prediction “to about 5% on average” | The paper reports an average **overprediction** of 5% on off-sweep data; this is not a maximum error, an absolute-error guarantee, or a confidence interval. [M p. 103] |
| Counter-wave and deflagration map boundaries are nearly deterministic | The thesis explicitly reports exceptions and says these ratios provide guidance, not rules. Coreless operation is a clear counterexample to applying \(r_i/\lambda\) mechanically. [M pp. 85, 101–102] |
| A single 320 kg/s/m² point is treated as exact common data | Figures show nearby measured points, grouped runs, and a nominal ER=1.15 sweep. The plan also uses 1.18 and a separate back-pressure series at 1.19. Record exact tabulated points where available; otherwise label interpolation/approximation. [M pp. 52, 59–61, 69] |
| Claimed 320-point frequencies and 3/2/1 count ladder | Broadly consistent with the plotted radius-study data. Retain as approximate comparisons, not high-precision measurements at an identical operating point. [M Figs. 3.19–3.22] |
| T3 uses Fig. 3.20 for all cored cases | Fig. 3.20 covers the radius study. Use Fig. 3.29 for the gap study. For 25-FI-3 frequency, Fig. 3.30 is on printed p. 66 and plots speed, requiring conversion using outer circumference. |
| T6 promises no counter waves, but passes anything below 58% | That allows weak counter waves and contradicts “no counter wave.” Defer this gate or make its stated target match its implementation. |
| All detonative 25 mm cases are said to have one wave | Accurate for the selected steady sweep subset, not for every instantaneous mode. The 25-FI-3 low-ER cases contain multiple co-/counter-rotating waves. [M p. 57] |
| Roughly the lower 60% of the fill layer is declared not fully mixed | Impingement height divided by a derived mean fill height does not measure the unmixed mass fraction or establish a sharp mixing boundary. [P §1.9; M pp. 34, 103] |
| Gap-width performance trends are assigned to wall heat loss | The cited discussion is partly from other experiments and includes injector coupling. Mundt's own gap study also changes area ratio and jet placement. A Reynolds-analogy sink cannot by itself establish the mechanism. [M pp. 18–19, 79–80] |
| ±10% pressure-tube uncertainty is implicitly paper based | Mundt reports axial pressure uncertainty ±1.6%, frequency ±0.7%, speed ±0.9%; total flow ±2.4%, equivalence ratio ±6.1% in Appendix C, with a separate reduced-noise alternative. Any extra instrument-model allowance must be separately identified and supported. [M p. 188] |
| Pressure ratio at 65% length is a universal value | The approximately 0.73 ratio is an empirical observation for selected back-pressure-insensitive data, not an exact boundary condition. [M p. 103] |
| “Wave-radius ambiguity” is treated as measurement error | The outer-circumference convention is explicit. The mean-radius model gives a different linear speed for the same angular speed; that is modeling discrepancy. Compare \(f\), \(N\), angular speed, and the documented outer-equivalent speed consistently. [M pp. 42, 59; P D35] |
| Startup choices “barely matter” after discarding a transient | Demonstrate this for the selected case; do not assume it. Large ignition patches and removed fresh gas can select a mode, especially in short circumferences. [P D27–D29; M p. 54] |

## 8. What to reuse from the starter

| Component | Assessment |
|---|---|
| `solver.py` conservative variables, HLL fluxes, MUSCL reconstruction, RK structure | Useful for a controlled 2D prototype. Keep after meaningful verification; extend only with the revised model. |
| `calibrate.py` ideal-gas CJ/ZND algebra | Useful as a reduced-model reference calculation. Separate it from physical thermochemical reference data. |
| `test_1d.py`, saved JSON and PNG | Useful baseline evidence. The script prints results but has no pass/fail assertions; the current “test passed” status is a human interpretation of saved values. |
| `run.py` geometry mapping and initialization | Useful starting structure, but output handling, case loading, boundary diagnostics, and startup assumptions need changes. |
| `analyze.py` plotting and FFT scaffolding | Reuse selectively. Do not reuse its current torque/stability conclusions without correction. |
| `STATUS.md` | Helpful and candid about failure of the 2D case. It is not independent verification. |

Specific code findings:

1. **No reactive source time-step control.** `solver.py:236` derives time step from fluid wave speeds alone. The new thresholded induction model needs reaction-event accuracy and source robustness checks.
2. **Floors are not full validity checks.** `solver.py:185` clips progress without counting it, modifies state through density/pressure floors, and lacks an explicit nonfinite-state check. Zero/negative density handling itself can divide by the old density. “Zero floor hits” is not sufficient evidence of a valid run.
3. **Primitive conversion touches initially zero-density ghost storage.** `cons_to_prim` covers the full array before ghost values are replaced. Restrict conversion to valid cells or initialize storage consistently.
4. **Boundary modes are not independently honored in every branch.** `fill_ghosts` treats both x sides as periodic whenever the left side is periodic; left transmissive copying also differs from a constant zero-gradient extension. The presently used symmetric-periodic case avoids the first problem, but the interface is misleading.
5. **Diagnostics do not use stored stage-integrated face fluxes.** `run.py:55` duplicates injection formulas and uses last-row cell values for outlet integrals. Retain the actual numerical fluxes for conservation accounting.
6. **Reported exit Mach includes swirl.** `run.py:96` uses total speed. Add axial Mach for outlet-characteristic/choking checks.
7. **Torque is inferred solely from exhaust with no storage term.** `analyze.py:119` takes the negative exit flux as engine torque despite the starter having no wall-friction source. A transient residual can become a false torque estimate.
8. **The swirl-power expression is not kinetic-energy flux.** `analyze.py:124` uses \(\dot m D u\). Replace the diagnostic as described above.
9. **Speed conventions are mixed in the comparison.** The current results table compares a mean-radius \(D/D_{CJ}\) with the paper's outer-radius ratio. `analyze.py:67–70, 168`.
10. **The strongest FFT peak can be a harmonic.** `analyze.py:44` treats it directly as wave count. Prefer tracking fronts and verifying the fundamental when ambiguity exists.
11. **The “camera” array is average temperature.** `run.py:104` is not a luminosity or heat-release projection. The revision already proposes changing this; continue labeling any replacement as synthetic.
12. **Provenance and output isolation are weak.** Scripts read a shared configuration and calibration by path; the analysis can read a config changed after the run. Capture immutable inputs with each run. Current scripts also execute at import time.
13. **Ignition patches are not wrapped periodically.** The “products behind” mask truncates at the left boundary when \(x_0<20\) mm, relevant to the smaller cases. A periodic domain needs periodic patch construction.
14. **Memory/output cost is understated.** At about 273k cells, 150 snapshots of eight float32 fields are about 1.3 GB before compression, apart from logs and checkpoints. Stream output rather than accumulate all full fields in memory.

I would not discard this work just to rewrite the same 2D equations. Equally, preserving a few hundred lines is not a reason to build a general CAD mesher, stiff chemistry system, and 3D wall-resolved solver from scratch.

For the CAD phase, evaluate an established compressible reacting-flow framework first. PeleC is a credible candidate: its official repository documents AMR and CPU/GPU parallel options, while its geometry documentation describes embedded boundaries. However, that documentation labels generic STL geometry support as beta/potentially unstable. It is a candidate for a representative-case evaluation, not a verified turnkey CAD solution. [E5]

## 9. Revised milestone order

The plan's minute-level implementation estimates are not supported by this inspection. Numerical research should advance by evidence and bounded experiments, not a compulsory minimum 2× speedup or an “all figures look like the paper” gate.

| Milestone | Work and visible output | Exit condition |
|---|---|---|
| **0. Scope and benchmark definition** | Define the first model as a straight, thin annulus; freeze Run 937 inputs; separate measured, derived, and fitted quantities. Add the external thrust case specification. Produce an input/reference table. | No ambiguity about what is predicted, fitted, or omitted. CAD phase is explicitly on the roadmap. |
| **1. Reference chemistry and numerical baseline** | Reproduce supplied basic results; compute physical and surrogate CJ/ZND references separately; correct reaction-length definitions. Plot shock/reaction structure and fit residuals. | Basic hydrodynamics, reactive timing, conservation, and fixed-model 1D refinement are credible. No target reached solely by arbitrary rate adjustment. |
| **2. Injection/outlet and force accounting** | Nonreacting feed/outlet cases; actual boundary-flux logging; mass, energy, axial/angular momentum storage; simple force check. Plot filling and pressure histories. | Balances close with storage retained; flow/source changes have understood effects. Outlet assumptions have a defined check. |
| **3. First sustained 2D wave and animation** | Use 76-FI-5; add live fields, checkpoints, and a simple unrolled animation immediately. Display reaction progress with pressure and a space–time plot. | Human-visible shock-coupled burning persists beyond ignition with no hidden state repair. Do not require a particular wave count merely to continue investigating. |
| **4. Fixed-model numerical sensitivity** | Refine mesh and time step; check outlet treatment/location and sufficient run duration. Compare fields, speed, pressure, mean force, and source budgets. | Remaining numerical sensitivity is quantified and small enough for the intended first-version claims. An under-resolved coarse run need not gate a finer run. |
| **5. Mundt pressure/wave comparison** | Compare Run 937 pressures and wave histories; show both speed conventions. Check a second initialization if the result suggests mode selection. | Report discrepancy openly. Keep exact mode classification a secondary comparison under the revised user scope. |
| **6. Measured-thrust comparison** | Run the independently specified external benchmark and a held-out condition with fixed model parameters. Produce measured/predicted force and uncertainty tables. | Establish the accuracy actually achieved; retain “estimate” labeling where agreement is inadequate. |
| **7. Torque estimate and roll response** | Add/test friction separately, then quantify its effect on both axial force and torque. Check angular balance, reversed direction, coefficient sensitivity, and inertia-dependent response. | A supported estimate with stated missing physics; quantitative validation only after a matched torque case. |
| **8. Additional geometries and CAD evaluation** | Add 51 mm and then selected 25 mm cases as exploratory comparisons; evaluate one representative 3D geometry in a candidate framework. | Demonstrated ability to represent relevant geometry and boundary conditions before expanding the supported CAD class. |

The cylinder-wrapped animation can follow as soon as milestone 3 produces data; it need not wait until six configurations and all mode gates pass. Use explicit labels so users see that it is a visualization of a 2D solution.

Milestones need not be a rigid chain for unrelated work. Analysis and visualization can advance while a physics issue is investigated; quantitative claims that depend on that issue remain withheld.

## 10. Concrete edits recommended for the next plan revision

- Rename the first deliverable to a **reduced 2D annular RDE prototype** and describe its later connection to the CAD workflow.
- Correct D14/A.3 with integrated reaction-length definitions and viable resolution requirements.
- Replace the D12 “stops contact burning” guarantee with a hypothesis and targeted checks.
- Separate physical thermochemistry from calibrated surrogate properties.
- Freeze chemistry in grid studies; add independent time-step and outlet sensitivity.
- Add mass, energy, axial momentum, and angular momentum storage to verification.
- Keep measured flow, fitted injector coefficients, and predicted outputs explicitly distinct.
- Replace “roll stability” with **torque and estimated roll response**.
- Use human inspection plus basic wave diagnostics first; defer exact counter-wave taxonomy.
- Define annulus-exit versus whole-engine thrust, including base/external forces when needed.
- Add [E1] as a separate measured-thrust benchmark; keep [E2] as context until its full case is specified.
- Move animations/live views earlier; stream run output and save immutable inputs.
- Keep 25-FI-3 chamfer, wide-gap curvature, and coreless dynamics visible in the model limitations.
- Remove unjustified universal success thresholds, the no-numeric-literals rule, and a mandatory 2× performance gate. Physical constants and tunable parameters need provenance; numerical indices and fixed algorithmic coefficients do not all belong in YAML.
- Evaluate a representative 3D/CAD case before committing the long-term solver architecture.

No future implementation has been performed as part of this review. The uncertainties left open are empirical/model questions to resolve through the revised milestones, rather than reasons to tune the current plan until a desired picture appears.
