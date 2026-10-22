# Figure validation roadmap: Mundt Chapters 3 and 4

**D3 update (October 22, 2026):** the initial Run 937 G0 subset now exists:
five-point CJ/heat-release neighborhood, nominal physical/surrogate ZND comparison
and stricter-tolerance reference checks. See [D3 investigation](../verification/d3_investigation.md).
NASA CEA itself, full Fig. 4.2–4.4 curves and experimental digitization remain
pending. The nominal factor-29 cell-size proxy is not a resolved CFD cell width.
Contact/refinement figures are numerical diagnostics and do not close G2's
sustained-wave criterion.

**Controlled-test update:** [C1–C6 and three plan reviews](controlled_2d_tests.md)
now precede additional engine figures: multirow/direction, verified formed-profile,
layer survival and initiation controls. The previously selected 0.25 mm engine
comparison is superseded. Reuse diagnostic output for plots; full campaigns stay
deferred. This session publishes on main; independent 3D work has its own branch.

**Planning catalogue; part of [the current simulation plan](../../first_sim_plan.md), revision 9.** Apart from the completed D3 subset described above and existing D1/D2 diagnostics, functions and reports below remain proposed work, not implemented capabilities. The review covered the complete relevant pages, captions, surrounding discussion, and rendered figures: Chapter 3, Figs. 3.1–3.35 and Tables 3-2/3-3; Chapter 4, Figs. 4.1–4.31. Printed page numbers are used throughout; add 16 for the PDF page.

**Deadline override:** the current test stage uses **three expected passage intervals by default, up to five total only if needed**. For Run 937 that is approximately **0.19–0.32 ms** of simulated time. This supersedes the earlier long screening-run proposal; use a fixed time cap so an extinguished wave cannot prolong a test indefinitely. The immediate output is a short Run 937 field/front/pressure/budget report, with transient estimates labelled accordingly. G2 spectra and G3–G9 campaigns below are deferred. The 51 mm map and the 3 ms/10 ms campaign budgets in section 8 are later planning context, not overnight work.

**Separate files, simple workflow:** physics/source laws in `physics.py`, numerical integration in `solver.py`, orchestration in `run.py`, reductions in `analyze.py`, rendering in `plot.py`, and assertions in `tests/`. Reuse the existing starter and a single run → saved results → plot workflow. No per-figure/per-engine script trees or workflow framework; see main-plan §4.5.

Primary source: [Mundt2023.pdf](../../Mundt2023.pdf). Additional source used to resolve Fig. 3.35's operating condition: Mundt et al., *Operating Characteristics of a 76-mm Rotating Detonation Rocket Engine*, AIAA 2023-1104, DOI `10.2514/6.2023-1104`, Fig. 17 and pp. 15–16; author-posted full paper inspected.

## 1. What counts as a useful check

Build comparisons in three distinct categories:

- **Measured observable:** simulation pressure, frequency, wave count or speed compared with experimental observations using compatible definitions. These provide evidence about CFD accuracy, subject to numerical and model uncertainty.
- **Reference calculation:** reproduce CJ/ZND/heat-release calculations or a paper formula. This checks thermochemistry or postprocessing; it is not independent validation of the engine simulation.
- **Exploratory correlation:** compare mode maps, geometric ratios and derived quantities across operating conditions. These reveal model limits, but often share inputs or reuse the same observations. Do not count every replotted point as a new validation result.

Imposed plenum pressure or mass flow is an **input/setup check**, not a successful prediction of that quantity. If the injector model predicts mass flow from fixed plenum conditions, comparison of that predicted flow becomes meaningful, provided its discharge coefficient was not fitted to the same target.

Human review remains the primary wave assessment. Store a reviewed mode label, its time window and supporting plots; do not build a comprehensive automatic classifier before pressure/frequency validation. Numerical failure, uncertain mode, unsupported physics, and no sustained detonation must be separate outcomes.

## 2. Shared data and comparison rules — G0

### Reference registry

Create one canonical row per experimental condition or repeat group, with engine, study, run/group ID, actual mass flux, total flow, equivalence ratio, back pressure, temperatures, feed specification, instrument positions, reported mode and observations. Record figure/page/table, units, raw-versus-grouped status, uncertainty, and whether tabulated, digitized or inferred.

Use explicit links from each figure to these rows. Figs. 3.19–3.34 and much of Chapter 4 reuse data; generating another figure does not require another simulation. Never deduplicate two distinct modes at nearly identical conditions into one averaged mode.

Prefer exact tabulated values, then recoverable author data, then checked digitization from the PDF. The workspace does not include the experimental raw time histories or a complete machine-readable run table. For digitized data, save axis calibration, marker/legend identity, possible overlaps, and coordinate uncertainty. Do not invent precision or silently fill missing conditions. Obtain missing per-point plenum conditions if possible; otherwise use a documented, independently fixed feed model and label the case an approximate reconstruction.

Mundt grouped repeat runs only when individual mass flow and equivalence ratio were within 2.5% of the group means **and** the wave number/counter-wave designation agreed (p. 52). Keep repeated simulation initializations separate first. Report mode multiplicity or fraction of time in each mode; do not take an arithmetic mean of categorical labels or claim identical deterministic reruns are independent experimental repeats.

The principal sweeps use nominal `phi = 1.15` or mass flux `243 kg/(s m²)`. Run 937 is a distinct exact point. Table 3-3 uses slightly varying equivalence ratios and is a different campaign. Reserve some off-sweep conditions for G8 before tuning on the broader maps.

### Measurement operators and plots

For each graph, specify:

1. Physical measurement location and quantity, including wall versus interior/ring-average pressure.
2. Native field/probe sampling interval, any resampling/filtering, transient exclusion, and averaging duration.
3. Whether the comparison is a scalar mean, trend, spectrum, instantaneous structure, or categorical mode.
4. Experimental uncertainty, digitization uncertainty, numerical sensitivity, and repeat variability separately.
5. Values used as inputs/calibration, which cannot count as independent predictions.

At the “65% length” station use the actual geometry-specific locations: 76-FI-5 at 47.6 mm (62.4% of length), 51-FI-5 at 33.7 mm (66.3%), and 25 mm configurations at 16.5 mm (65.0%). Show exact-station comparisons first; any interpolation to a common `z/L = 0.65` is a separate model comparison.

Keep three pressure definitions distinct: measured/simulated front-endwall mean, paper's empirical pre-detonation-pressure estimate from Eq. 4.1, and a simulation measurement in fresh gas ahead of the front. They are not interchangeable by definition.

For every direct comparison show paired measured/predicted points and residuals, with signed and absolute relative errors where the reference is nonzero. Use pressure-profile shape errors as well as individual station errors. Report a mode mismatch separately from frequency error. Do not install arbitrary universal ±5%/±20% bands as though they were paper uncertainty. Report achieved accuracy, then set justified project tolerances from the intended use and observed numerical uncertainty.

## 3. Function and engine order

These are responsibility names to guide implementation; the file boundaries above are required, while individual API names can be chosen during coding. All plotters consume common result tables or time-series records, rather than loading solver-specific arrays themselves. For the immediate deadline, implement only the Run 937 reference subset and G1 diagnostics; the remaining rows retain the later implementation order.

| Step / main milestone | Proposed reusable calls and outputs | First engine/data; expansion |
|---|---|---|
| **G0 / stages 0–1** | `load_reference`, `build_case`, `compute_thermochemical_reference`, `plot_reference_curves`; cache by mixture/state/mechanism/version. | Run 937 neighborhood; CJ speed → heat release → ZND induction/cell-size proxy. Full mixture range before G3's equivalence-ratio leg. |
| **G1 / stages 3–4** | `sample_probes`, `sample_ring`, `reduce_stationary_window`, `track_fronts`, `plot_pressure_profile`, `plot_spacetime`, `compare_case`. | Run 937. Output pressure/flow history, station residuals, front tracks, `N`, `f`, and both speed conventions. |
| **G2 / stage 4** | `compute_directional_spectrum`, `compute_rolling_frequency`, `compute_probe_spectrum`, `plot_spectrum`, `plot_spectrogram`. | Reuse G1 records. No new CFD run unless sampling/window length is inadequate. |
| **G3 / stage 5C** | `make_sweep`, `run_cases`, `collect_metrics`, `plot_sweep`; store run status/checkpoints and reuse completed cases. | 76-FI-5 mass-flux leg first; add a 51-FI-5 high-flux anchor and its leg; then a qualified 25-FI-5 subset. Repeat this order for equivalence-ratio legs. |
| **G4 / stage 5C, extended in 6–7** | Sweep ambient pressure; reuse `plot_pressure_profile` with dimensional and front-pressure-normalized panels; add categorical table comparison. | Four Fig. 3.35 76 mm conditions; then selected Table 3-3 25-FI-5 rows. |
| **G5 / stage 5C** | `group_repeats`, `attach_reviewed_mode`, `plot_operating_map`, `compare_mode_map`. Use explicit operating-point lists, not only rectangular grids. | Prove raw/grouped map plotting on the small 76 mm dataset; then sparse and broader 51-FI-5 maps. |
| **G6 / stages 5C exploratory, 6–7 predictive** | Same sweep/map calls, with geometry capability checks and the fixed-mean-radius depth-invariance diagnostic. | 25-FI-5 → limited 25-FI-7 → 25-FI-3 including chamfer → coreless 25-FI-12.7. |
| **G7 / alongside G3 onward** | `derive_scaling_metrics`, `plot_relation`, `compare_derived`; declarative x/y/group/axis-scale specifications. | Begin with available 76/51 mm records; extend to all supported engines. No new CFD jobs merely to change plotted axes. |
| **G8 / after parameter freeze; stages 5C/6–7 as supported** | `select_holdouts`, `compare_holdouts`; reuse map and relation plots plus residual summaries. | A small reserved off-sweep set first; expand to the reported data coverage later. |
| **G9 / optional future scope** | Dynamic plenum/feed and sensor/thermal/structural measurement models. | Only needed for full instrument-transient/amplitude or structural-damage replication. |

Engine order reflects evidence and model suitability, not just graph complexity. The 25-FI-7 plot has few points and is cheap to draw, but its wide relative gap makes physical replication less straightforward. The 25-FI-3 chamfer and the coreless case must not be silently reduced to the same rectangular model.

## 4. First additional checks: Run 937 — G1–G2

Implement in this order. For the overnight delivery, items 1–2 are **short-window diagnostics**, not converged mean-pressure or mode-selection validation. Use front tracks/arrival intervals if the short data record supports them; do not force a frequency estimate when too few clean passages remain. Items 3–5 follow later.

1. **Axial mean pressures and their time histories:** Fig. 3.2 right and Table 3-2. Plot the six in-combustor stations and a measured-versus-predicted axial profile with residuals. Add flow histories and conservation checks as context. These directly test the pressure field relevant to thrust.
2. **Space–time structure and measured wave frequency:** Fig. 3.5 and Table 3-2. Show a circumferential pressure ring and synthetic reaction/heat-release ring, front tracks, and the distinction between passage frequency and revolutions per wave. Compare with two co-rotating waves and 15.84 kHz without imposing that answer in initialization or analysis.
3. **Directional spectrum:** Fig. 3.6. Distinguish the fundamental `(N = 2, f = 15.84 kHz)` from its harmonics. Verify direction/sign conventions with a known traveling signal; confirm peaks using front tracks. Add normalized spectra only with the normalization stated.
4. **Frequency over time:** Fig. 3.7. Report an arrival-time/phase-based history and variation over simulation subwindows. A short computation can establish persistence on that simulated interval; it cannot reproduce or demonstrate stability over the experimental 0.696 s burn.
5. **Probe spectra/spectrograms:** use generic G2 functions on chamber signals first. The paper's Figs. 3.8–3.10 use plenum sensors; compare dominant frequency only until a matched feed/plenum/sensor model exists.

Important acquisition differences:

- Run 937 statistics use the last 100 ms of the burn, between experimental timestamps 2.8 and 2.9 s. Fig. 3.5 shows the final 2 ms. The current three-to-five-interval test lasts only about 0.19–0.32 ms, so its space–time plot covers a shorter interval and cannot reproduce those averaging statistics. The time cap includes startup; record how many clean passages actually remain.
- The displayed slow histories were filtered at 100 Hz for pressure, 50 Hz for temperature and 20 Hz for flow (p. 45); reported means were not taken from those filtered display traces. Do not apply those cutoffs to the short CFD record and treat the result as comparable instrumentation.
- A 0.19–0.32 ms FFT has only about 5.3–3.2 kHz bin spacing, versus 500 Hz for 2 ms or 10 Hz for 100 ms. Prefer front tracking/arrival intervals for the current test; defer fine spectral comparisons. Zero-padding does not recover missing duration. If ignition/settling leaves too little usable data, mark the diagnostic inconclusive rather than extending the run beyond the test budget.
- Save probes/rings at declared physical times even if CFD time steps vary. Resample consistently for FFTs, avoid aliasing, and retain anti-aliasing/window/normalization metadata. Choose sample rate for the highest harmonic actually compared, not merely the fundamental; inexpensive probe histories can be denser than full-field snapshots.
- The 85.7 and 98.4 mm pressure stations lie beyond the annulus in an expanded duct. They are excluded from the first rectangular-domain validation and added only when that downstream geometry is represented.
- Camera brightness includes viewing/chemiluminescence effects and stationary bright spark-port features. A synthetic heat-release ring can compare front count, direction and slope, not absolute luminosity. An arbitrary phase shift between simulation and experiment is not a failure.

### Chapter 3: complete figure disposition

| Figure / printed page | What it actually contributes | Implementation timing and comparison limit |
|---|---|---|
| **3.1 / 46** | Feed-system pressure and individual propellant/purge flow histories | G1: input/flow-budget context and stationary predicted flow if applicable. G9: full valves, orifices, purge and feed transients; not a first chamber-CFD accuracy target. |
| **3.2 / 46** | Plenum pressures and axial combustor pressures | **G1 first.** Quantitative combustor station means from Table 3-2; imposed plenum values are setup checks. Full startup/shutdown history and downstream stations later. |
| **3.3 / 47** | Feed/plenum/facility thermocouples and combustor exterior temperature | G1: check feed-temperature inputs. G9: sensor/solid thermal response; not a direct plot of simulated reacting-gas temperature. |
| **3.4 / 48** | End-view camera image with two waves | G1 qualitative synthetic head-end view; count/spacing/direction only. Do not reproduce camera brightness or spark-port spots as a CFD requirement. |
| **3.5 / 48** | Raw/background-subtracted camera angle–time map | **G1 first.** Ring space–time plot, front trajectories and frequency; preserve raw synthetic signal alongside any processed version. |
| **3.6 / 49** | Two-dimensional video FFT | G2: signed azimuthal mode/frequency peaks and harmonics; normalized synthetic intensity is not measured spectral power. |
| **3.7 / 49** | Dominant frequency history over the burn | G2: frequency persistence and drift over the actual simulated window; longer experimental-duration comparison later. |
| **3.8 / 50** | Raw dynamic pressures in fuel/oxidizer plenums | G2 chamber-probe diagnostic is analogous only. G9 required for matched plenum transient/amplitude comparison. |
| **3.9 / 51** | Plenum PCB spectrograms | G2 reusable spectrogram and dominant-frequency cross-check; G9 for comparable amplitudes, bandwidth and structural response. |
| **3.10 / 51** | Plenum PCB power spectra with detected peaks | G2 fundamental/harmonic consistency; do not try to reproduce structural resonance peaks with a fluid-only fixed-plenum boundary. |
| **3.11 / 53** | All 63 76-FI-5 runs in mass-flux/equivalence-ratio space | G3/G5: first raw operating-map plot from per-run records. Exact raw experimental repeat reproduction needs raw/group membership data. |
| **3.12 / 53** | Those runs reduced to 21 repeat-group points | G3/G5: first grouped map; test grouping and preserve distinct modes near transitions. Useful simpler precursor to 51 mm. |
| **3.13 / 55** | Broad 51-FI-5 averaged operating-mode map | **G5 dedicated target.** Sparse cross-leg/selected off-cross points first, then denser transitions/broader coverage; effort in section 8. |
| **3.14 / 56** | Limited 25-FI-7 equivalence-ratio dataset | G6: reuse map/sweep plotter; reproduce only actual measured coverage. Missing points reflect core failures, not an operating boundary. |
| **3.15 / 56** | Photograph of damaged inner cores | Exclude from CFD graph validation. G9 thermal/structural work would be a distinct project; no quantitative failure-time target is provided here. |
| **3.16 / 57** | 25-FI-5 averaged operating map | G6: start with detonative cross-leg cases; low-flow pulsing/extinction boundaries later and with adequate geometry/model support. |
| **3.17 / 58** | 25-FI-3 averaged operating map | G6 after a supported chamfer/injector representation. Lean unsteady and counter-wave region is a later demanding comparison. |
| **3.18 / 58** | Coreless 25-FI-12.7 averaged operating map | G6 with a supported 3D coreless domain. First 2D annulus backend must not claim its replication. |
| **3.19 / 60** | Total flow versus annular mass flux, radius study, nominal fixed phi | G3 first sweep bookkeeping plot. Mostly `mdot = mass_flux × area` if flow is prescribed; mode symbols add observational content. |
| **3.20 / 60** | Near-65%-length pressure versus mass flux, radius study | **G3 first multi-run accuracy target.** 76 → 51 → qualified 25-FI-5; sample actual axial stations. |
| **3.21 / 61** | Passage frequency versus mass flux, radius study | G3, reuse G1–G2 metrics. Preserve mode-transition discontinuities; do not smooth them into one continuous fit. |
| **3.22 / 61** | Outer-equivalent wave speed versus mass flux | G3 with simulated `N` and `f`; a speed jump caused by wave-count change must be visible. |
| **3.23 / 62** | Total flow versus phi at nominal fixed mass flux, radius study | G3 equivalence-ratio leg; primarily feed/area bookkeeping if imposed. Preserve actual small flow variations. |
| **3.24 / 63** | Near-65% pressure versus phi, radius study | **G3 second sweep target**, after mixture-dependent thermochemistry/feed definitions work. |
| **3.25 / 63** | Passage frequency versus phi, radius study | G3, same plotter with another metric. Do not reuse Run 937 chemistry indiscriminately across phi. |
| **3.26 / 64** | Outer-equivalent speed versus phi, radius study | G3 from the same cases/metrics; keep modes and geometry identity. |
| **3.27 / 64** | Speed/CJ-speed versus phi, radius study | G3 after G0's mixture/state reference. Report the paper-compatible and simulation-local CJ normalization separately if different. |
| **3.28 / 65** | Total flow versus mass flux, gap study | G6 bookkeeping plus mode symbols; account for actual annulus/injector area changes. |
| **3.29 / 65** | Pressure versus mass flux, gap study | **G6 first gap-study accuracy target.** Supported 25-FI-5 baseline, then additional gaps; common 16.5 mm pressure station. |
| **3.30 / 66** | Outer-equivalent speed versus mass flux, gap study | G6 from the same runs. The selected single-wave data need no separate frequency plot to duplicate the same information. |
| **3.31 / 67** | Total flow versus phi, gap study | G6 after its mass-flux leg; geometry/feed bookkeeping and mode overlay. |
| **3.32 / 68** | Pressure versus phi, gap study | G6 before finer mode-boundary work; explicit coreless/lean anomaly comparison only with supported physics. |
| **3.33 / 68** | Speed versus phi, gap study | G6, reuse existing metrics; retain non-detonative/uncertain cases as missing speed with an explicit reason. |
| **3.34 / 68** | Speed/CJ-speed versus phi, gap study | G6 after thermochemistry support. An outer-periphery apparent speed above CJ is not automatically a solver failure; inspect radius/state/mode conventions. |
| **3.35 / 71** | Dimensional and normalized low-flow 76 mm axial profiles | **G4 high-priority later check.** Exercises exit/back-pressure physics without needing a full mode classifier; conditions/source correction below. |
| **Table 3-3 / 69** | 25-FI-5 modes across 13 mass-flux rows and three back pressures | G4 sparse subset, G6 broader coverage. This is a table, not another existing graph; add a three-column categorical comparison/heatmap without interpolated boundaries. |

## 5. Sweep and map construction — G3–G6

**Deferred beyond the overnight deadline.** Reuse the completed single-case code when this work begins; none of these case counts is a requirement for the current test stage.

### G3: simpler one-dimensional sweeps first

After Run 937 checks, run a small set of actual 76-FI-5 points on the nominal `phi = 1.15` leg, spanning steady regions and bracketing the two-/three-wave change. Start with about 5–7 points, then refine only where a transition or numerical sensitivity warrants it. Reuse the resulting records for flow, pressure, frequency, speed and mode plots. Run 937 may be shown as a nearby separately identified point; it is not exactly the sweep intersection.

Add a high-flux 51-FI-5 anchor before its lower-flow/transition points, then a restricted 25-FI-5 detonative subset. Compare errors engine by engine. Do not delay useful pressure comparisons until every engine reproduces the exact observed mode.

Then implement the nominal `243 kg/(s m²)` equivalence-ratio leg, again 76 → 51 → supported 25-FI-5. Start with a modest central-phi subset, then extend lean/rich. The physical reference/surrogate parameter law must be defined across mixtures first. Do not keep a Run 937 constant-gamma/heat-release fit as an unexplained universal methane/oxygen model, or fit every point's CJ speed to its target and call that prediction.

### G4: back-pressure checks before extensive maps

Reuse the G1 pressure-profile code for Fig. 3.35. Digitize and preserve these separate legend conditions:

| Mass flux, kg/(s m²) | Phi | Back pressure, kPa | Plot role |
|---|---|---|---|
| 160 | 1.19 | 98.1 | Higher-flow blue profile |
| 81 | 1.18 | 105 | Low-flow red profile |
| 81 | 1.15 | 86.6 | Low-flow green profile |
| 80 | 1.16 | 42.6 | Low-flow purple profile |

The dissertation's p. 70 prose says 180 for the blue case, but its figure says 160. The original AIAA paper, Fig. 17 and accompanying text, also says 160; use that value and retain the discrepancy. Do not silently make all four phi values identical. Match physical downstream pressure coupling; an outlet that always extrapolates cannot substantiate back-pressure independence.

Plot both `mean(p(z))` and `mean(p(z))/mean(p_front)`; do not normalize by the mean of instantaneous ratios without identifying the changed statistic. Compare profile shape, front pressure and the degree of sensitivity separately. A reduced model may expose its limitations here before a large sweep is worth running.

For Table 3-3, start with three tabulated rows: 319.20, 239.00 and 160.30 kg/(s m²), each at the three reported back pressures 3.5, 52 and 97 kPa. This gives **nine planned cases**, using each row's actual phi. The table's conditions are three-run averages; do not pretend each pressure-specific run had independently reported exact identical inputs. Check the high-flow result first, then onset of sensitivity. Extend toward the 13 × 3 = 39 combinations later. The low-flow radial/pulsing behavior described on p. 70 may require 3D and richer mixing/transport; numerical death is not evidence of physical deflagration.

### G5: 51-FI-5 map and repeated conditions

Prove the map format on Figs. 3.11–3.12 using the completed 76 mm runs. Then target Fig. 3.13 with 12–20 selected 51 mm conditions: cross-leg steady points, a few transition brackets, and reserved off-cross checks. Expand the two-dimensional distribution from the actual plotted coordinates, not a large uniform grid unrelated to the experiment.

For each point show experimental and simulated labels side by side, plus a discrepancy marker or comparison table. Keep primary count, counter-wave presence, and confidence separate. Strong/weak camera classifications remain experimental labels unless the simulation measurement model is justified; a human can record approximate correspondence without asserting identical luminosity thresholds.

Repeat different controlled starts near ambiguous points to detect persistent competing modes. Keep model/mesh/feed definitions fixed across repeats. Do not initialize every case with the paper's desired wave count and count its persistence as an independent mode-selection prediction.

Do not draw precise continuous phase boundaries between sparsely sampled points. Store failed/unfinished points visibly. Reserve off-cross points for G8 or evaluate them once with already-frozen parameters; broadening the map must not silently turn the intended holdout set into tuning data.

### G6: reuse for gap studies and remaining operating maps

The application can already render all experimental panels from the reference registry. Simulation overlays are added only where the backend supports the geometry. Build in this order:

1. Reuse 25-FI-5 cases shared with the radius study.
2. Add the limited measured 25-FI-7 equivalence-ratio points, keeping gaps in experimental coverage visible. Do not invent a full mass-flux sweep for this engine.
3. Add 25-FI-3 with the near-injector chamfer and its impact on the fluid domain/injection.
4. Add the coreless domain and its measurement convention. The paper bins a virtual outer annulus with 3 mm depth for coreless camera analysis (p. 42); preserve this when defining a synthetic ring, rather than inventing an inner wall.

Before attributing a trend to gap physics, distinguish geometry scaling, injector area ratio, feed conditions, modeled loss terms and newly resolved radial effects. A fixed-mean-radius, wall-loss-free depth change should exhibit the reduced-model invariance described in the main plan. Successful integrated-force scaling in that check is not validation of cross-gap dynamics.

Use the same plots before/after backend migration, with backend/model/resolution identified, to show which discrepancies improve with 3D or transport/injector modeling.

## 6. Chapter 4: complete figure disposition

The cheapest figures to produce are not always the most independent checks. Many Chapter 4 quantities are computed from the same feed conditions and fitted pressure relation. Build their calculations once, preserve provenance, and reuse the resulting columns. “Early” below can mean a reference-only plot before CFD; it does not imply a completed six-engine comparison.

| Figure / printed page | Quantity or relation | Decision, timing, and what agreement establishes |
|---|---|---|
| **4.1 / 73** | Near-65%-length pressure versus phi, all configurations, detonative subset | **First CFD-derived Chapter 4 comparison**, G7 as soon as G3 phi sweeps exist. Reuse Figs. 3.24/3.32 data; begin 76/51 mm, complete after G6. Test pressure trends at actual sensor locations, not universal pressure independence. |
| **4.2 / 75** | Calculated cell size versus phi at initial pressures 100, 225, 350 and 500 kPa | **G0 reference work, after CJ/heat-release basics.** Detailed ZND induction plus the paper's factor 29; retain nonconverged/shifted points. This checks the physical-reference calculation, not cellular structure resolved by the thickened CFD surrogate. |
| **4.3 / 76** | Calculated CJ speed versus phi/initial pressure, including a 100 kPa CEA curve | **First G0 Chapter 4 graph.** Small neighborhood first, full domain before normalized-speed sweeps. Keep thermodynamic model/CEA comparison separate from a fitted surrogate; matching a calibration target is not validation. |
| **4.4 / 77** | CEA-derived heat release versus phi/initial pressure | **Second G0 graph**, needed before broad phi and energy-flux comparisons. Reproduce the stated product-state and formation-enthalpy convention; if using a different equilibrium package/database, label it an independent recalculation rather than exact CEA replication. |
| **4.5 / 79** | Formula-derived fill height versus phi | **Early G7**, beginning with Run 937 and then G3. Plot paper-formula reconstruction and independently extracted simulated fill height separately; the paper values already contain measured frequency. |
| **4.6 / 81** | Inner-radius/gap ratio versus mass flux, with approximate mode regions | G7 after multi-engine G5/G6 data. Reuse operating-map labels; allow partial-engine panels earlier. Boundaries are empirical guides, not classifier rules or universal pass criteria. |
| **4.7 / 82** | Outer-radius/gap ratio versus outer-equivalent speed | G7 after G3 subset, complete G6. Cheap geometry/speed scatter; compare like operating conditions before attributing the full range to geometry. |
| **4.8 / 82** | Outer-radius/gap ratio versus speed/CJ speed | G7 with G0 CJ references. Reuse 4.7 data; distinguish physical reference from simulation-local normalization. |
| **4.9 / 83** | Inner-radius/gap ratio versus near-65% pressure | G7, lower priority than matched-condition pressure sweeps. Replot existing data; the paper itself notes little new information in the range comparison. |
| **4.10 / 84** | Inner-radius/gap ratio versus calculated cell size | G7 after G0 reference curves and multi-engine cases. An input-derived geometry/reference scatter; do not label cell size an observed CFD result. |
| **4.11 / 85** | Inner-radius/gap ratio versus calculated energy flux | G7 after heat-release lookup and case collection. Low incremental cost; input-derived unless using separately identified actual CFD heat release. |
| **4.12 / 86** | Inner radius versus calculated cell size; lines at `r_i/lambda_cell = 6, 26` | G7 after mode-labelled multi-engine data; G8 for independent checks. Do not enforce these regions as extinction/counter-wave rules; stable points and coreless operation violate such an interpretation. |
| **4.13 / 86** | Inner-radius/cell-size ratio versus phi | G7 after 4.12; reuse its derived columns and labels. Does not supply an independent prediction of mode. |
| **4.14 / 87** | Inner-radius/cell-size ratio versus speed/CJ speed | G7 after G3 speed and G0 references, complete after G6. Low additional plotting cost; record shared inputs and mixture/state assumptions. |
| **4.15 / 88** | Gap/cell-size ratio versus phi, radius study only | **Early reference/scaling check**, G0 once the selected case inputs exist; overlay CFD-informed references in G7 if desired. Tests the intended common gap/cell-size scaling, not resolved radial sensitivity. |
| **4.16 / 89** | Calculated fill height versus calculated cell size | G7 after G0 and 4.5. Compare formula-derived and field-derived fill quantities explicitly; defer full map until sufficient cases exist. |
| **4.17 / 90** | Fill height × frequency (effective fill velocity) versus cell size | G7, lower priority. With Eq. 4.5 this is algebraically `mass_flux R T0 / p0`; reconstructible without CFD frequency. Useful as a postprocessing consistency check, not independent dynamics validation. |
| **4.18 / 91** | Inner-radius/gap ratio versus fill-height/cell-size ratio | G7 after fill/cell references. The discussed `h/lambda_cell >= 4.5` guideline is not a thrust measurement or mandatory detonation boundary; do not use it to validate thrust. |
| **4.19 / 92** | Calculated energy flux versus phi | **Early G0/G7** after heat-release references and case inputs. Establish units, mass-flux dependence and reference consistency; overlay actual simulated conversion separately when available. |
| **4.20 / 92** | Calculated energy flux divided by primary wave count versus phi | G7 after trustworthy mode counts. No division for no-detonation/undefined `N`; not a measurement of energy consumed by an individual wave. |
| **4.21 / 93** | Calculated energy flux versus near-65% pressure | **Early G7 priority** once G3 pressure sweeps exist. It relates predicted pressure to independently specified energy supply; do not generate the pressure axis from the same paper fit and call that CFD agreement. |
| **4.22 / 94** | Per-wave energy flux versus near-65% pressure | G7 after 4.21 and wave-count review. Shared plotting routine; assess pressure and mode errors separately. |
| **4.23 / 95** | Calculated energy flux versus wave speed | G7 after G3/G6, below direct speed sweeps in priority. Reuse recorded speed and input-derived energy; account for unequal operating coverage across engines. |
| **4.24 / 95** | Calculated energy flux versus speed/CJ speed | G7 after 4.23 and G0. Same data and derived columns; not a separate CFD campaign. |
| **4.25 / 96** | Per-wave energy flux versus calculated fill height | G7 after 4.5/4.20. Several axes share frequency/mode/feed inputs; add a separately labelled field-derived-height view if it helps expose model discrepancy. |
| **4.26 / 97** | Calculated energy flux versus calculated cell size, logarithmic cell-size axis | Early reference-only version possible after G0; full mode-coloured G7 version later. Predominantly a correlation between two functions of the same input state. Preserve log-axis and missing-reference behavior. |
| **4.27 / 97** | Per-wave energy flux versus calculated cell size | G7 after 4.26 and reviewed wave count. No additional solver capability beyond its prerequisites; exclude undefined per-wave values transparently. |
| **4.28 / 99** | Eq. 4.7 heat-release power versus `mdot D_spin u_VN`, radius study | **Optional later G7 historical-formula comparison; not torque validation.** Resolve/reference the velocity frame. Prefer the actual angular-momentum/traction and swirl-energy diagnostics described below for mechanical conclusions. |
| **4.29 / 100** | Same Eq. 4.7 comparison including all gap-study configurations | Optional G7 after 4.28/G6. Reuse the same function and change the dataset selection; do not infer a universal 9% mechanical-power or torque rule. |
| **4.30 / 101** | Off-sweep mode distribution versus inner-radius/gap ratio and mass flux | **G8 held-out evaluation.** Reuse 4.6 plotter with frozen parameters and new case IDs; show false inclusions/exclusions and unsupported conditions, not just fitted region lines. |
| **4.31 / 102** | Off-sweep inner-radius versus calculated cell size | **G8**, reuse 4.12. Test the limits of the empirical regions; coreless `r_i = 0` must not automatically imply extinction. |

Although no further figures are numbered on p. 103, add two useful **new** held-out comparison plots in G8: predicted-versus-measured pressure and passage frequency, with residuals. Compare both CFD and the paper's empirical baseline (`p_65 ≈ 0.73 p0_fit`; constant mean fill height 3.25 mm). The paper's average 8% pressure underprediction and 5% frequency overprediction describe its sample; they are not universal error bounds or requirements to force into our model.

### Priority within Chapter 4

1. **Reference readiness:** 4.3 → 4.4 → 4.2; then 4.15, 4.19 and a reference-only 4.26 when inputs are available. These can progress alongside early CFD.
2. **First useful comparisons with CFD:** 4.5 for Run 937, then 4.1 and 4.21 after modest pressure/phi sweeps. Begin partial datasets and label coverage.
3. **Reuse the collected sweep data:** 4.7–4.11, 4.13–4.14, 4.16–4.17, 4.20, 4.22–4.27. Most are new plot specifications or derived columns, not new runs.
4. **More demanding mode/geometry interpretation:** full 4.6 and 4.12; 4.18 as a qualified derived diagnostic. Depend on sufficient multi-engine coverage and appropriate geometry/chemistry.
5. **Independent applicability tests:** 4.30–4.31 and p. 103 pressure/frequency baselines, on reserved conditions.
6. **Optional reproduction only:** 4.28–4.29; keep actual mechanical validation separate.

## 7. Derived quantities without circular validation — G7

### Physical references and actual simulation observables

Use names that keep physical cell size `lambda_cell` distinct from an induction-progress variable. Store the source/method of every derived column.

| Quantity | Paper-compatible reconstruction | Additional simulation quantity to keep separate |
|---|---|---|
| Pre-detonation pressure | Eq. 4.1 fitted from experimental fill conditions | Fresh-region pressure ahead of the front; front-wall mean is another observable |
| CJ speed | Physical thermochemistry at documented initial mixture, pressure, 300 K | Surrogate CJ speed and, optionally, CJ speed at sampled simulated fresh conditions |
| Cell size | ZND induction definition and empirical factor 29 | Resolved transverse/cellular spacing only if the model/domain/resolution genuinely support measuring it |
| Heat release `q_ref` | Eq. 4.2 from documented CJ equilibrium products and formation enthalpies | Actual chemical energy converted in the simulated control volume, including incomplete reaction |
| Fill height | Eq. 4.5 using the paper's input convention and measured frequency | A field-derived fresh-layer extent, phase-conditioned before wave arrival, with threshold/temperature/mixing sensitivity |
| Energy flux | `q_ref × mass_flux`, in W/m² | Actual chemical conversion rate integrated over volume and divided by declared area; track stored/exported chemical energy consistently |
| Per-wave energy flux | Above reference supply divided by primary wave count `N` | Optional wave-conditioned conversion if later defined; the ratio alone does not establish it |

At 300 K, reproduce the paper's reference calculation as stated before substituting simulated fill temperatures. If comparing physical layer heights, a formula evaluated with simulated inlet/fresh-state conditions is an additional diagnostic. An Eq. 4.5 height computed using measured frequency cannot independently validate that same frequency.

Heat-release reconstruction must use species mass fractions consistently with formation enthalpy per species mass (or the equivalent molar formulation). Record the equilibrium state and thermodynamic database. The CEA-derived pressure-dependent `q_ref` curve is not automatically identical to a fixed lower heating value or the prototype's one-value `q`. A modern/reference implementation with different data may legitimately differ; quantify the difference.

Label `q_ref × mass_flux` as **nominal chemical energy supply**, rather than measured actual released heat. As the paper notes, it evaluates the same detonative reference even for experimentally deflagrative points. Use the same convention when recreating its plots, while keeping actual CFD conversion distinct.

For a transient/competing mode, do not divide by an average noninteger wave count and imply a steady per-wave result. Use stable mode-conditioned intervals or leave the per-wave quantity undefined. Preserve missing values and their reasons in the result table.

A global constant rate fit, an empirical pressure relation, or a fixed 3.25 mm fill height may be useful baselines. They must not generate both the simulated “prediction” and the reference for an apparent validation plot. Freezing a physically defined parameter law across a sweep also differs from recalibrating every case to the paper.

### Mechanical comparison accompanying Figs. 4.28–4.29

The paper evaluates a scaling expression `mdot D_spin u_VN`; it is not an integrated measurement of torque or azimuthal kinetic-energy flux. Its identification of the approximately 270 m/s VN velocity with a laboratory-frame tangential velocity warrants a frame-consistency check. Preserve that concern if recreating its formula, rather than silently replacing its variable and calling the new result a replication.

The simulation's mechanical report should instead retain:

- Wall/feature traction torque and the inlet/outlet angular-momentum balance including storage.
- Azimuthal kinetic-energy flux, with the appropriate signed normal mass flux, such as `integral 0.5 rho u_z u_theta² dA` at a planar axial exit.
- A declared chemical-supply/conversion reference for any energy ratio.
- Engine mechanical power `tau × omega_engine` only when an actual engine rotation rate is specified. A stationary engine's torque does not establish power transferred to a rotating body, and wave angular speed is not engine rotation rate.

These diagnostics can begin with the first torque estimate; the optional paper-formula scatter plot need not delay them.

## 8. Deferred effort for Fig. 3.13, the 51-FI-5 averaged dataset

**This campaign is not part of tonight's work.** These estimates begin after the first working iteration and the generic G3 sweep/plotting infrastructure. They exclude repairing the current failing 2D case, building a new CFD backend, implementing 3D, or developing accurate mixing/transport. They assume one developer comfortable with the code and intermittent scientific review. “Person-days” below are hands-on effort; CFD elapsed time is separate and may overlap. Short three-to-five-passage tests help development but do not establish an averaged operating-mode map.

| Deliverable | Provisional effort | What that does and does not deliver |
|---|---|---|
| Recreate the experimental figure and its legend from the PDF | Roughly 0.5–1.5 person-days | Checked digitization/reference data and plot format; no simulation prediction. Missing author raw data may limit precision/repeat reconstruction. |
| First sparse simulation comparison, 12–20 selected conditions | Roughly **2–4 person-days total**, including the reference preparation above | Case selection, reuse of batch tools, review of outputs, comparison panels; simulated modes may disagree with experiment. |
| Broader coverage of the displayed map, with selected repeats and transition checks | **Another 1–2 person-weeks** | Larger case manifest, record review, repeat/transition handling and an honest discrepancy map; excludes unbounded model-development work if missing physics dominates. |
| Quantitatively reliable reproduction of the full counter-wave/extinction map | No credible fixed estimate yet | Depends on how the reduced model performs; may require later chemistry, injector/plenum, 3D and transport work. Do not promise this as the plotting milestone's deliverable. |

For budgeting use **80 distinct conditions** as a provisional map allowance, not an audited count of experimental groups. The figure contains overlapping/nearby markers; G0 digitization must establish the actual count and repeat membership if available. Start with 12–20, then revise the budget from measured cost and observed sensitivity.

### Historical longer-run compute budget — not current test defaults

For 51-FI-5, `r_m = 22.9 mm` and `L = 50.8 mm`. At approximately 0.25 mm spacing the unrolled mesh is about `576 × 203 = 116,928` cells. Assume, solely for estimating:

- Average CFD time step 20–40 ns.
- 3 ms simulated duration in the earlier campaign proposal, now deferred.
- Throughput `3 × 10^6` full cell-steps/s, as reported in archived revision 3 for its two-core setup. **This has not been remeasured here** and may change with corrected chemistry, source integration, logging and backend choice.

Then

`wall time ≈ cell_count × (simulated_duration / average_time_step) / cell_steps_per_second`.

This gives **0.81–1.62 hours per 3 ms run**. A run slot here means resources sustaining that assumed throughput; it is not one CPU core.

| Campaign at these assumptions | Aggregate run-slot time |
|---|---|
| 12–20 screening conditions, one initialization each | About 10–32 hours |
| 80 conditions, one initialization each | About 65–130 hours |
| 80 conditions, two to three initializations each | About **130–390 hours** |
| Same repeat campaign, 10 ms instead of 3 ms | About **430–1,300 hours** |

The 130–390 hour campaign is approximately 5–16 days on one continuously available equivalent run slot, or ideally 1.5–4 days with four **independently provisioned** equivalent slots. Running four jobs on the same saturated two-core machine does not provide that speedup. These totals exclude queueing, initial compilation, failed attempts, and review.

The earlier 3 ms assumption was not established convergence for mode selection or extinction. A later validation campaign may need longer windows (the 10 ms row illustrates cost), multiple initializations and finer grids for transition cases. **Do not launch or automatically extend to these durations in the current test stage.** Halving both 2D cell spacings increases explicit fixed-duration work by roughly eightfold at unchanged per-cell throughput and CFL-limited stepping. Detailed chemistry can increase cost further.

When the deferred campaign is scheduled, first benchmark representative 51 mm cases after the baseline solver corrections. Measure time step, throughput, output volume, physical settling time and restart behavior. Then replace this provisional budget with actual timings. The present deadline does not require starting that campaign.

## 9. Completion criteria for each graph step

Each scheduled step delivers reference records, reusable analysis/plotting functionality, an actual figure, and a short comparison report once coding begins. For the current deadline this applies only to the limited Run 937 diagnostics, not the whole figure list. The report must identify supported physics, operating conditions, averaging/window choices, numerical sensitivity, data uncertainty, and discrepancies. Passing a short test means only that the exercised checks passed; it does not establish long-time mean thrust/torque, stable operating mode, or completed experimental validation.

For early G1–G2, use stored records or simple known traveling signals to verify sampling, wave-count/speed conversion, FFT sign/harmonics, window handling and pressure reductions. For G3 onward, check one known completed case flows through batch collection without changing its metrics and that experiment/simulation joins use the correct condition IDs. Do not add tests that merely assert chart styling.

No automatic exclusion of disagreeing, non-detonative, ambiguous or failed cases from a map. Use distinct symbols/statuses and list exclusions explicitly. Show only supported comparison subsets until later backends make the remaining points meaningful. Preserve independent holdouts and the earlier thrust/torque validation work; reproducing more paper figures does not replace force validation.

**Planning output only:** no CFD jobs, digitization dataset, new analysis functions, or plotting implementation were produced during this review. Temporary rendered pages remain outside the repository; this roadmap and the revised master plan are the implementation instructions.
