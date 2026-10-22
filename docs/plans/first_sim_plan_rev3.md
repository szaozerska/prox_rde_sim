# First RDE simulation: plan (revision 3)

**Goal of iteration 1.** Simulate the engines in Mundt 2023 (*Geometric Scaling of Cylindrical Rotating Detonation Rocket Engine Combustors*, PhD dissertation, University of Washington) in 2D, and produce for each:

- an animation of the wave propagation (unrolled view, a cylinder view like Fig. 1.1 right, and a head-end "camera" view);
- **two stability verdicts:** wave stability (Mundt's definition) and roll stability (torque on the rocket from exhaust swirl);
- thrust, I_sp, Mach numbers, pressures and fill height;
- comparison tables against the paper.

**Rules:**
1. When there's a choice between a harder and a simpler option, take the simpler one unless it makes the answer meaningless.
2. Keep the test cases separate from the main code. The test cases come directly from the paper: Mundt's six engine configurations across his two scaling studies.
3. Build stage by stage. Each stage has a pass condition, and nothing moves on until the current stage passes.

Page numbers are the thesis's *printed* page numbers. **PDF page = printed page + 16** (e.g. printed p. 28 = PDF p. 44).

### What changed from revision 1, and why

| # | Change | Evidence |
|---|---|---|
| R1 | **Two-step induction–reaction chemistry** replaces the one-step model (D12–D14) | In 2D the one-step model (E_a/RT₁ = 20) burned fresh gas at the injector face, so no fresh layer formed and the wave died. Halving the reaction length didn't help. One-step with E_a/RT₁ = 50–70 failed to initiate in 1D at 0.25 mm (about 1,400–1,500 m/s instead of 2,471). |
| R2 | **Ignition:** 10 mm patch at 2× CJ pressure (D28) | A 5 mm patch at the CJ state decayed to 870 m/s in 1D; 10 mm at 2× p_CJ gave 2,490 m/s (+0.8%). |
| R3 | **Wall friction added** (new D16b) so torque can exist (D37) | Without friction, the circumferential momentum in the unrolled domain is conserved and zero, so the predicted mean torque would be exactly zero. |
| R4 | **Exit boundary: extrapolate, i.e. treat the exit as choked** (D26) | Mundt measured 238 kPa at 73 mm and 68 kPa in the duct beyond: the exit chokes. Forcing 100 kPa at the annulus exit would distort the near-exit pressures. |
| R5 | **Frequency from wave arrival times; runs of 3 ms** (D30, D32) | A 0.6 ms FFT window resolves only about 11% in frequency, so the ±5% steadiness test was unmeasurable. |
| R6 | **Measured cost; efficiency fixes** (§1.7) | Measured about 3×10⁶ cell-steps/s on the 2-core build machine, about 10× slower than the revision 1 estimate. |
| R7 | **Sharp, paper-based success criteria** (§1.9) | The old band (1–3 waves, 8–24 kHz) accepted almost anything. |
| R8 | **Six-configuration test suite and cross-study trend tests** (Part 3) | New requirement. |
| R9 | **Stage-gated timeline** (Part 2) | New requirement; the 2-hour estimate didn't hold. |
| R10 | Limitations added: wave-radius ambiguity, nozzle-less thrust, HLL smearing, single gas constant | Review findings. |

### What changed in revision 3 (checked against Sections 1, 2 and 4 of the thesis)

| # | Change | Paper basis |
|---|---|---|
| R11 | **Thinnest reaction zone the grid allows:** Δ_I = Δ_R = 0.25 mm on the 0.25 mm production grid (D14) | Fill height/cell size governs survival (§1.3 pp. 11–12; h/λ ≥ 4.5, p. 90). With revision 2's 0.5 mm induction length, the effective λ ≈ 29 × 0.5 = 14.5 mm, 4× the fill layer |
| R12 | **Paper test points moved to 320 kg/s/m²,** where the results are back-pressure insensitive and definite (Part 3) | 25-FI-5 is back-pressure sensitive at 243 kg/s/m² but not at 319 (Table 3-3, p. 69; §1.5.3 pp. 19–20). At 320 every case has one definite mode (Figs. 3.13–3.22) |
| R13 | **The 58% counter-wave threshold is applied to a camera-like heat-release signal,** not pressure (D32) | The threshold was set on video luminosity (pp. 42–43) |
| R14 | **Eq. 4.7 is a scaling argument only; Sawada's wall-shear-to-thrust ratio of 8.8% is the roll check** (D37) | Eq. 4.7 uses the shock-frame u_VN ≈ 270 m/s as a lab-frame swirl velocity (p. 98) |
| R15 | **Contact burning measured and grid-checked** (D43) | Fig. 1.10 region E is real burning and a real loss (p. 13) |
| R16 | **Premixed-speed bias labelled as an assumption** (§1.9) | Reactants first meet in the combustor (p. 24), with impingement 2.16 mm above the face (p. 34) and fill height ≈ 3.25 mm (p. 103) |
| R17 | **Optional wall heat loss** by Reynolds analogy (D16c) | Gap-width performance trends attributed to wall heat loss (§1.5.2 pp. 18–19; V/(SA·L) in Table 4-1) |
| R18 | **Induction time defined as Mundt does:** the time of maximum dT/dt (D13) | p. 74 |
| R19 | **Fill-height comparison uses the simulation's actual fill temperature** (D40) | Eq. 4.5 assumes T₀ = 300 K (p. 78); the injected gas is about 235 K |
| R20 | **Frequency cross-check from Mundt's constant-fill-height method** (D44) | §4.3 p. 103: h ≈ 3.25 mm predicts f to about 5% on average |
| R21 | **Ignition location difference noted** (D28) | Pre-detonator enters through a radial port at z = 73 mm (Table 2-2; p. 25) |
| R22 | **Non-discriminating tests removed:** 51-FI-5 moved from its 1↔2 transition point to 320 kg/s/m² (2 waves) | Fig. 3.13 p. 55 |
| R23 | **Caveats on Mundt's λ and on pressure taps** (D4, D39) | Computed λ runs low (p. 75); standoff tubes are 145 diameters long (p. 35) |
| R24 | **Fill-pressure comparison made like-for-like** (D11) | Eq. 4.1 fits the *time-averaged front-wall* pressure, which Mundt uses as the pre-detonation pressure (§4.1.1) |
| R25 | Internal consistency fixes from the final verification pass: induction contrast (125×, not 200×), thickening factor (9×), k_R and time step (D20), heat-release Cantera note (D9), fill-height offset (25–30%), unit-test status (D1) | Recomputed |


---

## Part 0: Read this first (for an implementing agent with no prior context)

### 0.1 What this project is

A team wants a quick, honest first simulation of a **rotating detonation rocket engine (RDRE)**: an engine in which one or more detonation waves run continuously around a ring-shaped (annular) channel. Propellant is injected through the closed end of the ring (the "injector face") and burned gas leaves axially through the open end.

The engines simulated are those of **Mundt (2023)**, a PhD dissertation: T. Mundt, *Geometric Scaling of Cylindrical Rotating Detonation Rocket Engine Combustors*, University of Washington (204 pages). It reports 400+ gaseous methane–oxygen hot fires on six engines across two geometric scaling studies. **Ask the project owner for the PDF.** Every number in this plan cites its page.

**Deliverables:**
- a 2D simulation program for any annular engine described by four geometric numbers and an operating point;
- a test suite that runs Mundt's six engines and compares them with his data;
- for each run: animations, wave stability, roll stability (torque), thrust, I_sp, Mach numbers, pressures and fill height.

**Owner's working rules:**
1. Simplest option that still gives a meaningful answer.
2. Tests separate from the main code, taken from the paper.
3. Build stage by stage; don't start a stage until the previous one passes. **If a stage fails, stop and report to the owner** with the evidence (plots, numbers) rather than pushing on.
4. Every constant in a data file (D2b), never in code.
5. Results must be viewable at every stage (Part 4).

### 0.2 How this document is organised

- **Part 0:** context, glossary, conventions, environment.
- **Part 1:** design decisions D1–D44 (what to build and why).
- **Part 2:** stage gates.
- **Part 3:** the paper test suite.
- **Part 4:** viewing results during development.
- **Appendices:** A, exact equations and algorithms; B, contents of the three data files; C, diagnostics definitions; D, lessons from the partial build.

Revision history (R1–R25) is in the tables just above Part 0. An implementer can skip it.

### 0.3 Glossary

| Term | Meaning |
|---|---|
| Annulus, gap | The ring-shaped channel between the outer wall (radius r_o) and the inner core (radius r_i); gap = r_o − r_i |
| Unrolled domain | The annulus cut open along the axis and flattened: x around the circumference (periodic), y along the axis |
| Injector face / head end | The closed end at y = 0, where propellant enters |
| Detonation | A shock wave sustained by the combustion it triggers; it travels at roughly the CJ speed |
| CJ (Chapman–Jouguet) | The ideal self-sustaining detonation state; D_CJ is its speed, M_CJ = D_CJ / (fresh-gas sound speed) |
| VN (von Neumann) state | The gas state just behind the leading shock, before any reaction: the pressure peak |
| ZND model | 1D detonation structure: shock → induction zone → heat release → CJ plane (Mundt §1.2.2) |
| ξ (xi) | Heat-release progress, 0 = fresh, 1 = fully burned |
| λ (lambda), in the chemistry | Induction progress, 0 = just shocked/fresh, 1 = ignited. **Not** the same as λ meaning cell size |
| λ, cell size | Detonation cell width (a length scale of the real cellular front), from Mundt's Fig. 4.2 |
| N, wave count | Number of co-rotating detonation waves around the ring |
| f, passing frequency | Rate at which waves pass a fixed point: f = N·D/circumference |
| Counter wave | A wave travelling in the opposite direction to the main waves; "weak" or "strong" per Mundt's 58% power threshold |
| Fill height h | Height of the fresh-propellant layer just ahead of a wave |
| Mass flux | Mass flow ÷ annulus area, in kg/s/m² |
| φ (phi) | Equivalence ratio; 1 = stoichiometric CH₄ + 2 O₂ |
| XX-FI-Y | Mundt's engine names: XX = outer diameter in mm, FI = flat-faced impinging injector, Y = gap in mm |
| Run 937 | Mundt's fully documented example run on the 76-FI-5 engine (Table 3-2, p. 52) |
| Roll stability | Here: the torque about the engine axis caused by exhaust swirl |

### 0.4 Conventions

- **Units:** SI throughout the code (m, s, kg, Pa, K). Data files may use mm, kPa or kHz *only if the key name says so* (e.g. `r_outer_mm`); convert at load time.
- **Axes:** x = circumferential distance along the **mean** circumference (outer circumference for the coreless case); y = axial distance from the injector face. Grid index i along x, j along y.
- **Wave direction:** ignition is set up so the main wave travels in **+x**.
- **Torque sign:** τ_engine is positive when it would spin the engine in **+x**. Behind each wave the gas moves in +x and drags the walls with it, so the engine torque follows the wave direction (as Sawada et al. measured). Fresh gas enters with no swirl, so in a steady average the exhaust leaves carrying the equal and opposite angular momentum (net swirl in −x). Check: τ_engine + (exhaust angular-momentum flux) ≈ 0 (D37).
- **FFT sign convention (numpy):** in `np.fft.fft2` over arrays shaped (time, x), a wave e^{i(kx − ωt)} moving in +x appears at **(f > 0, k < 0)**. Don't rely on this from memory: Stage 1 includes a synthetic unit test that confirms it (`tests/unit/test_fft_direction.py`).
- **Thesis pages:** printed numbers; PDF page = printed + 16.

### 0.5 Environment

- Python ≥ 3.10.
- `pip install numpy numba scipy matplotlib pyyaml cantera` (Cantera is only needed for the D13 fit; if it fails to install, use the fallback T_a and say so in the Stage 0 report).
- `ffmpeg` for MP4 animations; otherwise write GIFs with Pillow.
- Runs on a laptop. A recent Apple-silicon machine is assumed for the time estimates; Numba uses all cores with `parallel=True`.
- Each run writes into `runs/<run_name>/` (Part 4.2).

### 0.6 Starting point

A partial prototype exists (Python + Numba): calibration, a solver with one-step chemistry, a run script and an analysis script. It passed the Sod and 1D detonation tests, and failed in 2D for the reasons in Appendix D. If the owner provides it (`rde_sim_starter.zip`), reuse the solver structure. Otherwise everything needed is specified in Appendix A.

---

## Part 1: What the final program looks like

### 1.1 One-paragraph summary

A 2D "unrolled annulus" simulation: the ring is cut open and flattened into a rectangle, as in Fig. 1.10 (p. 13).

- The x-direction runs around the circumference and is periodic.
- The y-direction runs along the axis, from the injector face (y = 0) to the annulus exit (y = L).
- The gas is a premixed methane–oxygen mixture, treated as one ideal gas with a single γ.
- Chemistry is a two-step model: a temperature-sensitive induction step, then heat release following the form of Mundt's Eq. 1.11 (p. 9).
- The equations are the compressible Euler equations, plus two reaction variables and a simple friction term for the inner and outer annulus walls (so swirl, and therefore torque, can develop).
- Propellant enters through a micro-nozzle injector condition along the bottom edge and leaves through a choked exit at the top. An ignition patch starts the wave.

Wave count, speed, direction, counter waves and torque all come out of the solution. Outputs are processed the way Mundt processed his camera and pressure data (§2.4, pp. 41–43).

### 1.2 Program structure: main code separate from tests

```
rde_sim/                      MAIN CODE (runs any engine from a config file)
  config.yaml                 your engine: 4 geometry numbers from the CAD + operating point
  model.yaml                  modelling choices: chemistry lengths, C_f, grid, CFL, thresholds (D2b)
  paper_data.yaml             every number taken from the papers, with source and page (D2b)
  calibrate.py                gas properties, CJ/VN states, two-step rate constants, ZND profile
  solver.py                   Numba kernels: reconstruction, HLL, chemistry, friction, boundaries, RK2
  run.py                      initial state, ignition, time loop, logging, snapshots
  analyze.py                  waves, wave stability, roll stability, thrust, Mach, pressures, fill height
  animate.py                  unrolled / cylinder / head-end animations
  view.py                     interactive scrubber over snapshots/checkpoints, works mid-run (Part 4)
  quicklook.py                one-snapshot PNG of all fields (Part 4)

runs/<run_name>/              one folder per run: live.png, progress.json, log.npz, state_*.npz,
                              snapshots.npz, results.json, summary.md, *.png, *.mp4

tests/                        TESTS (never imported by the main code)
  unit/test_sod.py            shock tube against the exact solution
  unit/test_detonation_1d.py  1D detonation speed and von Neumann spike against calibration
  unit/test_fft_direction.py  synthetic +x wave → confirms the FFT sign convention (§0.4)
  paper/cases.yaml            Mundt's six configurations + expected results with page references
  paper/run_cases.py          runs the main code once per case, checks expectations, writes a report
  paper/trends.py             cross-configuration trend checks (Part 3.3)
```

**D1. Python + Numba,** not an existing CFD package. Four reasons:
- **Setup time:** detonation-capable packages (OpenFOAM-based detonationFoam, LBNL's PeleC) need compiling against specific framework versions.
- **Custom parts are needed anyway:** this setup needs a periodic unrolled domain and a blocking/refilling injector boundary, which would mean writing boundary code inside a package's framework.
- **Transparency:** about 300 readable lines.
- **Laptop performance:** Numba runs natively on Apple silicon and scales across cores.

*Cost:* a home-made solver is less proven. That's why the unit tests (Stage 1) are mandatory gates. They passed with the one-step chemistry (§1.10) and must be re-passed with the two-step model. An established package remains an option for later iterations, for credibility.

**D2. Separate scripts that pass files** (.npz snapshots, logs, results.json). A crash in the animation step then doesn't cost the run, and analysis can be re-run without re-simulating.

**D2b (new). All key numbers live in data files, never in the code.** Three files, each with a different owner:

| File | What it holds | Who changes it |
|---|---|---|
| `rde_sim/paper_data.yaml` | **Every number taken from Mundt and the other cited papers**, each with its source and page. For example: Table 2-1/4-1 geometry; Table 3-2 (Run 937) results and axial pressures; Table 3-3; Eq. 4.1 coefficients; the Westbrook factor 29; the 58% counter-wave threshold; 3.25 mm average fill height; values read off Figs. 3.19–3.22 and 4.2–4.4 (marked "read off plot, ±5%"); Sawada's 8.8% and 0.149 N·m / 48.1 N | Nobody, except to fix a transcription error. Read-only reference |
| `rde_sim/model.yaml` | **Modelling choices:** T_a (or "fit from GRI-Mech"), Δ_I, Δ_R, C_f, heat loss on/off, CFL, grid size, run length, averaging window, ignition patch size and pressure factor, logging interval, classification thresholds (5% counter-wave noise floor, peak/mean ratio of 5, ±5% steadiness) | The simulation team, when tuning |
| `rde_sim/config.yaml` | **Your engine:** the four CAD numbers, propellant, φ, mass flux, plenum pressure and temperature, back pressure | Whoever runs a case |

The test cases (`tests/paper/cases.yaml`) refer to entries in `paper_data.yaml` by name rather than copying them, so every expected value traces back to a single page reference.

**Rule:** no numeric literal in the Python code except pure mathematics and unit conversions. A review check (`grep` for number literals in `rde_sim/*.py`) is part of Stage 2.

### 1.3 Inputs (your engine; the six paper cases are in Part 3)

#### From the CAD team: four numbers only

| Input | Run 937 value (76-FI-5) | Source (all checked against the original pages) |
|---|---|---|
| Outer radius r_o | 38.1 mm | Table 2-1, p. 28: annulus outer *diameter* 76.2 mm (Fig. 2.4, p. 29, shows it's the full diameter). Also consistent with Table 4-1: r_o/gap = 7.62 × 5.0 mm |
| Inner radius r_i | 33.1 mm | Table 4-1, p. 80 (r_i/r_o = 0.87) |
| Annulus length L | 76.2 mm | Table 2-1 |
| Injector-to-annulus area ratio σ | 0.110 | Tables 2-1 and 4-1. Recomputed from 72 pairs of 0.79/1.24 mm holes: 0.109 |

**D3. The CAD is reduced to four numbers,** because a 2D unrolled model has no room for more:
- the individual injectors (30° inclination, impingement height 2.16 mm, §2.2.4 pp. 34–35);
- the expanded duct after the core ends (stations at 85.7/98.4 mm, p. 45);
- the instrument and pre-detonator ports (Table 2-2, p. 37).

The CAD team should still supply these for a later 3D iteration. Losing them removes mixing effects (see §1.9).

#### Operating point: Run 937 (Table 3-2, p. 52), checked

| Quantity | Value | Use |
|---|---|---|
| Mass flux / mass flow | 240.21 kg/s/m² / 268.65 g/s | Target for tuning the injector coefficient C_d |
| Equivalence ratio φ | 1.176 | Mixture gas constant R |
| Plenum pressure | 1309.5 kPa (O₂) / 1399.4 kPa (CH₄) → 1.35 MPa | Single premixed plenum |
| Plenum temperature | 303 / 301 K → 300 K | T₀ |
| Back pressure | 100.2 kPa | Pressure thrust reference |
| CJ speed | 2471 m/s | Calibration target |

**D4. First validation case: Run 937 on the 76-FI-5 engine.**
1. It's the only run with a full results table.
2. It's a clean mode: 2 co-rotating waves, no counter wave.
3. It has the thinnest annulus (gap/r_o = 0.13, Table 4-1), where unrolled 2D is best justified.
4. Mundt's maps predict no counter wave there:
   - r_i/gap = 6.62 at 240 kg/s/m² is outside the counter-wave region of Fig. 4.6 (p. 81), which is r_i/gap < 4.8 and mass flux < 280;
   - r_i/λ ≈ 33.1/0.8 ≈ 41 > 26 (Fig. 4.12, p. 86), with λ ≈ 0.8 mm read off Fig. 4.2 (p. 75). *Caveat (R23):* Mundt notes his computed cell sizes run small (p. 75). His 6/26 boundaries use the same computed λ, so the comparison is internally consistent, but the real margin above 26 may be smaller.

**D5. Premixed, single plenum.** This matches Mundt's own premixed assumption for his Cantera calculations (§4.1.2, p. 74).

**D6. Mixture gas constant:** at φ = 1.176, x_CH4 = 0.370, molar mass 26.09 g/mol, **R = 318.7 J/(kg·K)**.

**D7. Exact-area domain.** Width = mean circumference π(r_o + r_i) = 223.68 mm, and depth = gap = 5 mm. Width × depth = π(r_o² − r_i²) exactly, so 240.21 kg/s/m² × 1118.4 mm² = 268.65 g/s with no correction factor. The coreless case is handled differently (Part 3.2).

### 1.4 Thermochemistry and calibration (`calibrate.py`)

**D8. One ideal gas with a single γ and a single R** for reactants and products. This keeps the Riemann solver standard. Costs:
- temperatures come out too high (D10);
- real products are lighter (about 20–22 g/mol vs 26), so product density and sound speed are somewhat off.

Pressures, speeds and Mach numbers are the trustworthy outputs.

**D9. γ and Q are calibrated to two numbers from the paper** (no Cantera needed for these two; the induction step in D13 does use Cantera):
- D_CJ = 2471 m/s (Table 3-2);
- heat release q ≈ 5.5 MJ/kg (Fig. 4.4, p. 77, read off the plot at φ ≈ 1.18 and about 400 kPa).

Solving Eq. 1.7 (p. 5) for γ gives **γ = 1.238, Q = q/(c_pT₁) = 11.08, M_CJ = 7.18, a₁ = 344 m/s**. Cantera with SDToolbox (Mundt §4.1.2) is only needed later, for other propellants or φ.

*Why not Mundt's γ = 1.4?* The only γ the thesis states is 1.4, and it's used for the illustrative theory plots (Figs. 1.3–1.5, pp. 4–7). It isn't a property of his methane–oxygen gas. With Mundt's own q = 5.5 MJ/kg, γ = 1.4 gives D_CJ = 3,290 m/s, 33% above his own 2,471 m/s, and a CJ temperature of about 8,400 K. γ = 1.238 is the value that makes *both* of Mundt's numbers (q from Fig. 4.4, D_CJ from Table 3-2) consistent, so it's the paper-consistent choice.

**D10. Reference states** (verified by `calibrate.py`):

| State | p | T | M (shock frame) | Paper check |
|---|---|---|---|---|
| Fill | 378 kPa (Eq. 4.1; a time-averaged front-wall value, see D11) | 300 K | 7.18 | Measured front-wall pressure 368.5 kPa ✓ |
| von Neumann | 21.5 MPa | 2116 K | 0.335 | Post-shock speed 306 m/s vs Mundt's u_VN ≈ 270 m/s (p. 98) ✓ |
| CJ | 11.0 MPa | 4885 K | 1.0 | Temperature too high (real is about 3,700–3,900 K): don't report it |

**D11. Fill pressure from Eq. 4.1** (pp. 73–74): p₀ = 377.9 kPa. It's used for the initial state and the reference states.
- *What p₀ actually is:* Eq. 4.1 is a fit to the **time-averaged front-endwall pressure**, which Mundt then *uses as* the pre-detonation pressure (§4.1.1). The real fill gas just ahead of a wave is at a lower pressure than that average, since the average includes the wave spikes.
- So the like-for-like check is the simulation's **time-averaged injector-face pressure** against the measured 368.5 kPa (and Eq. 4.1's 378 kPa), not the instantaneous fill pressure.
- Both D_CJ (Mundt's and ours) are evaluated at this same averaged pressure, so the calibration stays consistent with the paper.

**D12 (revised, R1). Two-step induction–reaction chemistry.** Two transported progress variables, both 0 → 1:

$$\frac{D\lambda}{Dt} = k_I\,e^{-T_a/T}\quad(\lambda<1), \qquad \frac{D\xi}{Dt} = \begin{cases}0 & \lambda<1\\ k_R(1-\xi) & \lambda\ge 1\end{cases}$$

- **λ (induction):** a "clock" that has to fill up before any heat is released. Its rate depends steeply on temperature.
- **ξ (heat release):** Mundt's Eq. 1.11 with the temperature dependence moved into the induction step.

Why this is the smallest fix that works, compared with the one-step model:
- **It stops burning at the injector face.** Freshly injected gas that mixes numerically with hot products ends up at a mixed temperature (about 1,400 K for a 50/50 mix by mass) and a mixed λ. With T_a = 20,000 K, its induction time at 1,400 K is about 125× longer than at the von Neumann state (2,116 K). That's about 100 µs at production settings, longer than the ~63 µs between waves, so the fill layer stays fresh. *The margin is thin* (less than 2×), which is why the fitted T_a (D13) matters and why raising it is fallback F1(b).
- **It keeps 1D initiation robust.** Heat release itself doesn't depend on temperature, so the detonation doesn't develop the pulsing that broke the high-E_a one-step runs.

Costs: one more transported variable, and three constants instead of two.

**D13 (revised again: from Mundt's own mechanism). Induction activation temperature T_a fitted to GRI-Mech 3.0,** the detailed methane–oxygen mechanism Mundt used for all his ZND and cell-size calculations (§4.1.2, p. 74). Mundt's Eq. 1.11 (p. 9) names k and E_a only as symbols ("constants") and never gives numbers, so they can't be copied from the paper. The closest thing to "Mundt's value" is to derive them from his mechanism:
- In Cantera with GRI-Mech 3.0, compute the ignition delay of the φ = 1.176 mixture at the von Neumann pressure, for post-shock temperatures of about 1,600–2,400 K.
- **Define induction time exactly as Mundt does (R18):** the time of the maximum temperature-rise rate (p. 74). Use a constant-volume reactor started at each post-shock state. Temperature barely changes before ignition, so this closely matches the ZND path Mundt used. Use SDToolbox's ZND routine instead if it installs cleanly.
- Fit ln(τ_ind) against 1/T. The slope is T_a.
- As a cross-check, the fitted induction length at the von Neumann state should be close to Mundt's λ/29 ≈ 28 µm (Fig. 4.2, p. 75; factor 29 from p. 74). Mundt notes his computed cell sizes run somewhat small (p. 75).

This replaces the guessed value of 20,000 K, which is kept only as a fallback if Cantera can't be installed. Done in Stage 0.

**D14 (revised). Rate constants from target lengths:**

$$k_I = \frac{u_{VN}}{\Delta_I}\,e^{T_a/T_{VN}}, \qquad k_R = \frac{u_{VN}}{\Delta_R}$$

with **Δ_I = Δ_R = 0.25 mm on the 0.25 mm production grid** (about one cell each; R11). That gives k_R ≈ 1.2×10⁶ s⁻¹. The 0.5 mm debugging grid uses 0.5 mm lengths, and its results are for debugging only.

*Why so thin, even though under-resolved (R11):* Mundt ties wave survival to fill height divided by cell size (§1.3, pp. 11–12; h/λ ≥ 4.5 checked on p. 90), with λ ≈ 29 × the induction length (p. 74).
- Revision 2's 0.5 mm induction length implied an effective λ ≈ 14.5 mm, about 4× the 3.8 mm fill layer. Its full reaction zone (~1.5 mm) was also ~40% of the layer height, so the wave loses too much to sideways expansion into the products above. That probably contributed to the failed 2D run.
- At 0.25 mm the full reaction zone is ≈ 0.75 mm ≈ h/5.
- The wave speed is fixed by the conservation laws (§1.2), so under-resolving the reaction zone costs internal structure, not speed. Shock-capturing RDE simulations commonly run with induction zones only a few cells thick.
- **Constraint:** full reaction length ≤ h/5.
- **Verify** with one 0.125 mm run of a 25 mm case (Stage 5).

- The real induction length is λ/29 ≈ 28 µm (Mundt's Westbrook factor, §4.1.2), so the 0.25 mm used here is deliberately **thickened about 9×** to fit the grid. **This is the one chemistry parameter that can't follow the paper.** Using Mundt's 28 µm directly would need cells of about 3 µm, roughly 10⁸–10⁹ cells in 2D, which is weeks of computing even on fast laptops. The thickening changes the wave's internal structure but not its speed or pressure (theory §1.2.1).
- CJ speed and pressure depend only on Q and γ, not on the rates (theory §1.2.1), so wave speed and pressure stay meaningful.
- Cellular structure and detonability limits aren't captured: Fig. 4.12's r_i/λ boundaries can't be reproduced by this model.
- Even so, the effective h/λ (with λ_eff = 29 × 0.25 mm ≈ 7 mm) is about 0.5, far below the real ≈ 4.8. **The model represents a quasi-ZND wave without cellular structure.** It can't reproduce any limit or mode change that depends on cell size. Revision 1 had also checked only the 50% reaction point, missing that its 90% point (~3.5 mm) filled the whole layer.

**D15. Byproduct: a Fig. 1.7-style ZND plot** of the calibrated model (M, p, T against progress), checked visually against p. 9.

### 1.5 Governing equations and numerics (`solver.py`)

**D16. 2D Euler equations, two progress variables, chemical energy stored in E.** U = (ρ, ρu, ρv, E, ρξ, ρλ):

$$\partial_t U + \partial_x F + \partial_y G = S_{chem} + S_{fric}, \qquad E = \frac{p}{\gamma-1}+\tfrac12\rho(u^2+v^2)+\rho q(1-\xi)$$

- Inviscid in the flow itself, which is standard for RDE wave dynamics.
- Storing the chemical energy in E means burning needs no energy source term, so total energy is conserved exactly and the thrust balance stays clean.

**D16b (new, R3). Wall friction from the inner and outer annulus walls** as a source term on the gap-averaged flow:

$$S_{fric} = -\frac{2}{\text{gap}}\cdot\tfrac12 C_f\,\rho\,|\mathbf u|\,(0, u, v, 0, 0, 0)$$

with **C_f = 0.003**, a typical turbulent skin-friction value.

- **Why it's needed:** without it, nothing can apply a circumferential force to the gas, so circumferential momentum is conserved and zero and the mean torque is exactly zero (the revision 1 error). With it, the walls drag on the swirling gas, the gas leaves with net swirl, and the same wall force is the torque on the engine.
- **No energy term:** the walls don't move, so they do no work. The kinetic energy lost to friction stays in the gas as heat.
- **Cost:** the predicted torque scales directly with C_f, which is uncertain by about 2×. Torque from pressure on injector-hole features is missing (3D only). Roll results are therefore order-of-magnitude.

**D16c (new, R17; optional, off by default). Wall heat loss by Reynolds analogy,** using the same C_f: Stanton number St = C_f/2, heat flux q_w = St·ρ|u|c_p(T − T_w) with T_w = 300 K, applied over both annulus walls as an energy sink of −2q_w/gap.
- Turn it on for gap-study performance trends: Mundt attributes the narrowest gap's poorer performance to heat loss through the walls (§1.5.2, pp. 18–19, Bilger; Brophy), with V/(SA·L) the key parameter (Table 4-1).
- With it off, those trends are reported but excluded from the hard checks.
- It doesn't replace the wall-temperature/heat-sink question; that remains iteration 2+.

**D17. Uniform Cartesian finite-volume grid,** no adaptive mesh refinement.

**D18. HLL flux,** the most robust simple option. *Known risk (R10):* HLL smears the fresh/burned interface, which feeds burning at the injector face. Stage 3 includes a fill-layer check; if it fails, switch to HLLC.

**D19. MUSCL reconstruction with the minmod limiter** on primitive variables.

**D20. SSP-RK2 time stepping, CFL = 0.4,** with the explicit sources evaluated in each stage. The fastest rate, k_R ≈ 1.2×10⁶ s⁻¹ (time scale about 0.8 µs), is about 20 steps long at Δt ≈ 4×10⁻⁸ s, so it isn't stiff.

**D21. Floors:** ρ ≥ 10⁻⁶ kg/m³ and p ≥ 1 Pa (SI units), with a counter. A run with any floor hits in the averaging window is suspect. (The unit tests in nondimensional units set their own floor.)

**D22. Grid:** 0.5 mm for development, 0.25 mm for reported results. The cell size is forced by the physics: the 3.8 mm fill layer needs at least 10–15 cells.

### 1.6 Boundaries, initial state, ignition (`run.py`)

**D23. Periodic left and right edges** close the ring (Fig. 1.10).

**D24. Bottom edge: micro-nozzle injector without backflow,** following Schwer & Kailasanath [31], cited on p. 16. Open-area fraction σ, plenum at p₀,pl and T₀. In each bottom face, compare the wall pressure p_w with the plenum:

| Condition | Face flux (mass / axial momentum / energy) |
|---|---|
| p_w ≥ p₀,pl: **blocked** (region F, Fig. 1.10) | 0 / p_w / 0 |
| p_cr ≤ p_w < p₀,pl: subsonic | σG(p_w) / σG·u_j + p_w / σG(c_pT₀ + q) |
| p_w < p_cr: **choked** | σG* / σG*·u_j + p_w / σG*(c_pT₀ + q) |

- p_cr = p₀,pl (2/(γ+1))^{γ/(γ−1)}, about 0.75 MPa.
- G* has the same form as Mundt's Eq. 2.1 (p. 41).
- u_j is the jet velocity after isentropic expansion to p_w; the jet reaches the cell at about 235 K.
- Injected gas is fresh (ξ = λ = 0).
- Backflow (Paxson & Miki [29], p. 16) is left out; that's a later iteration.

**D25. C_d tuned to the measured mass flow.** Start at 0.76 (what 268.65 g/s needs if the injectors were always choked), then update once: C_d ← C_d × (ṁ_target / ṁ_sim). Mundt calibrated discharge coefficients from cold flows (p. 39). Keeping the *measured* plenum pressure keeps the blocking behaviour realistic.

**D26 (revised, R4). Top edge: zero-gradient extrapolation** (a choked exit). Mundt's data show the annulus exit chokes: 238 kPa at 73 mm, 68 kPa in the duct, against 100.2 kPa back pressure, and 76-FI-5 is back-pressure insensitive at this mass flux (§3.4, pp. 69–71; insensitive even at 180 kg/s/m², Fig. 3.35). Back pressure enters only through the pressure-thrust term (D36).
- *This boundary only represents back-pressure-insensitive operation* (Koch et al.'s choked regime, §1.5.3 pp. 19–20). For 25-FI-5 sensitivity starts between 260 and 280 kg/s/m² (Table 3-3), so **every paper test point is chosen where operation is insensitive** (R12, Part 3).
- Back-pressure-sensitive cases need a downstream buffer region with p_back imposed far downstream. That's out of scope for iteration 1.

**D27. Initial state:**
- the whole domain at 378 kPa;
- a fresh layer 0 ≤ y ≤ 3.8 mm (Eq. 4.5, p. 78) at 300 K, with ξ = λ = 0;
- burned products above it at 1500 K, with ξ = λ = 1;
- velocity zero everywhere.

The start-up transient is discarded, so these exact values barely matter.

**D28 (revised, R2). Ignition: a patch 10 mm wide × fill height at 2× p_CJ and T_CJ,** with ξ = λ = 1. The 20 mm of fill layer behind it is set to products, so only a +x wave forms. A known direction fixes the torque sign.
- *Difference from the experiment (R21):* Mundt's pre-detonator fired through a radial port at z = 73 mm, near the exit (Table 2-2; p. 25), not at the injector face. Shepard et al. found that ignition transients don't change steady operation (p. 19). But Mundt saw different wave counts at identical conditions near mode transitions (p. 54), which is why the test points in Part 3 avoid transitions.

**D29. Start with one wave.** Variant B starts with two patches 180° apart. Mundt saw different wave counts at repeated identical conditions near transitions (§3.2.1, p. 54), so the final mode can depend on the start, and both variants are reported.

**D30 (revised, R5). Run 3 ms; average over the last 1.5 ms** (about 24 wave passes at 15.84 kHz; FFT resolution 0.67 kHz, about 4%). Mundt averaged the last 100 ms of a burn of at least 700 ms (pp. 40, 42). 3 ms also gives the wave count time to settle, since RDE simulations often take several milliseconds.

**D31. Logged every 5th step** (about 0.4 µs, still about 150 samples per wave period):
- (a) a ring of pressure probes at y = 1 mm;
- (b) the camera signal: heat-release rate integrated along the axis at each x (D32 step 4), plus axially averaged temperature for display only;
- (c) exit-plane integrals;
- (d) the injector-face pressure integral;
- (e) ṁ in and out;
- (f) wall-friction torque.

Snapshots every 2 µs over the last 0.3 ms, for the animation.

### 1.7 Cost (revised, R6)

Measured on the 2-core build machine: about 3×10⁶ cell-steps/s with logging. Two fixes are planned: each face flux is currently computed twice, and logging every step costs extra. Expect about 2–3× from both.

| Run, 3 ms of engine time | 2-core cloud machine (measured / scaled) | Recent Apple M-series Pro/Max laptop (estimate) |
|---|---|---|
| 2D 76-FI-5, 0.5 mm (68k cells) | about 20 min | about 2–4 min |
| 2D 76-FI-5, 0.25 mm (273k cells) | about 2.5–3 h | about 15–30 min |
| 2D 25 mm cases, 0.25 mm (about 26–33k cells) | about 15–20 min | about 2–4 min |

The six paper cases are independent, so they can run in parallel on teammates' laptops. 3D is out of scope (about 16× per halving of the grid, plus new code).

### 1.8 Outputs (`analyze.py`, `animate.py`)

#### Wave stability (Mundt's definition)

**D32 (revised, R5). Wave detection follows Mundt's §2.4:**
1. **x–t diagram** of probe pressure (cf. Fig. 3.5, p. 48).
2. **2D FFT with a Hanning window** (Fig. 3.6, p. 49; p. 43). It gives the wave count N and direction from the peak's wavenumber and sign.
3. **Frequency f from wave arrival times** at the probes: the average time between successive peaks passing a probe, averaged over all probes. This is much more precise than an FFT bin.
4. **Counter-wave power ratio, on the camera-like signal (R13):** power at −N divided by power at +N, computed on the heat-release rate integrated along the axis at each angle. That's the closest analogue to the flame light Mundt's camera recorded through the annulus exit (pp. 23–24). The 58% weak/strong threshold was set on that luminosity signal (pp. 42–43), so it's only applied to this signal. Below 5% counts as none. The same ratio from the pressure probes is reported alongside, for information only. Mundt found the counter-wave count always matches the primary count (p. 42).
5. **Steadiness:** the arrival-time frequency in three sub-windows of 0.5 ms each must vary less than ±5%, with the same N in each (cf. Figs. 3.7/3.9).

**D34. Mode classification** using Mundt's labels:

| Mode | Rule |
|---|---|
| Deflagration | No coherent k ≠ 0 peak, *or* D/D_CJ < 0.4, *or* peak/mean probe pressure < 5 |
| Longitudinal pulsing | Dominant k = 0 peak (cf. 25-FI-5 pulsing at about 16.6 kHz, pp. 56–57) |
| N-wave | Steady, counter-wave ratio < 5% |
| N-wave + weak / strong counter wave | Counter-wave ratio below / at or above 58% |
| Unsteady / chaotic | N or f changes between sub-windows (cf. 25-FI-3 at low φ, p. 57) |

**D35. Wave speed,** reported in both conventions. The simulation's value is D_sim = f·πd_mean/N. Mundt's convention uses the outer circumference, D_Mundt = f·πd_o/N (pp. 42, 59). Also report D/D_CJ and the wave-frame M₁.
- *Limitation (R10):* it's unknown at which radius the real wave runs. Comparing frequencies carries a systematic uncertainty of about 7% for 76-FI-5 (r_m/r_o = 0.93), and up to about 20–28% for the 25 mm cores (0.80, 0.72).

**D40 (revised, R19). Fill height** from the ξ field ahead of each wave. Compare with:
- **Eq. 4.5 in two forms:** Mundt's (T₀ = 300 K), and one with the simulation's actual mean fill-gas temperature (about 235 K after expansion from the injector). The second is the like-for-like comparison; the first will read about 25–30% higher (h ∝ T₀, and 300/235 ≈ 1.28).
- Mundt's 3.25 mm average (§4.3, p. 103).
- The h/λ ≥ 4.5 guideline (p. 90), using the real λ ≈ 0.8 mm (not the simulation's thickened λ_eff).

**D43 (new, R15). Contact burning.** Mundt notes that burning "where products and fresh reactants meet (E)" is real and costs performance (Fig. 1.10, p. 13), so it isn't simply suppressed.
- Report the fraction of heat released *outside* the detonation front: cells with ξ increasing more than 2 mm from the shock.
- In the simulation, part of this fraction is numerical (it grows with cell size). So it must be **compared between 0.5 and 0.25 mm** (Stage 5). If it drops sharply with refinement, it's mostly numerical, and wave speeds at coarse grids are suspect.

**D44 (new, R20). Mundt's frequency predictor.** In §4.3 (p. 103), holding fill height at 3.25 mm and solving Eq. 4.5 for f predicted measured frequencies to 5% on average. Compute f_pred = mflux·R·T₀/(p₀·3.25 mm) and compare with the simulated f. For Run 937 this gives 18.7 kHz against the measured 15.84 kHz (+18%), so treat it as ±20%.
- **Why it matters:** if fill time sets the frequency but the premixed simulation's waves run faster than the real ones, the model may settle on *fewer* waves than the experiment at the same frequency. That's the most likely way the wave-count tests fail, and D44 is the diagnostic for it.

#### Roll stability (new)

**D37 (revised, R3). Torque about the engine axis:**
- **Torque on the engine:** τ_engine = −r_m·∫S_fric,u dV, the reaction to the friction force on the gas, times the radius. It follows the wave direction (sign convention §0.4).
- **Cross-check:** the angular momentum leaving through the exit, r_m·depth·∫ρuv dx, must satisfy τ_engine + flux ≈ 0 in the time average (within 5%). Exact formulas: Appendix C.
- **Report:**
  - mean torque and sign (relative to the wave direction);
  - **primary check (R14): circumferential wall-shear force divided by thrust,** against Sawada et al. 2022 (J. Propulsion & Power), who measured an azimuthal shear force of 8.8 ± 0.6% of thrust. It's dimensionless, so it transfers between engines better than torque does;
  - torque/thrust ratio, against Sawada's 0.149 N·m / 48.1 N ≈ 3.1 mm. That's a different, smaller engine, so it's an order-of-magnitude check only;
  - fluctuation (standard deviation divided by mean);
  - swirl power fraction, for information only. Mundt's ~9% (Eq. 4.7 / Fig. 4.28, pp. 98–99) is a scaling argument, not a quantity to reproduce: it uses u_VN ≈ 270 m/s, the post-shock speed *relative to the shock*, as the lab-frame swirl velocity. In the lab frame, gas just behind the shock moves at about D − u_VN ≈ 2,200 m/s;
  - roll acceleration as τ/I per unit roll inertia, plus the undamped spin rate after 1 s for example inertias of 0.005, 0.01 and 0.05 kg·m².
- **Uncertainty:** the result scales with C_f (D16b). Report results at C_f = 0.0015, 0.003 and 0.006.

#### Performance and flow

**D36. Thrust:** F = depth·∫(ρv² + p − p_a)dx at the exit, averaged over time. Cross-check against the injector-face momentum balance, depth·∫(σGu_j + p_w − p_a)dx, minus the axial wall friction; it must agree within 5%. I_sp = F/(ṁg₀).
- **There's no paper value:** Mundt's stand had no load cell (p. 22).
- *Limitation (R10):* this is the thrust of a straight annulus with **no nozzle**. The exit is underexpanded (about 240 kPa against 100 kPa), so the number isn't comparable to a nozzled engine.

**D38. Mach numbers:**
- the field, for the animation;
- the mass-averaged exit Mach number, which should be close to 1 at a choked exit;
- the wave-frame M₁ against M_CJ = 7.18;
- the wave-frame Mach number behind the reaction zone, which should be close to 1 for a CJ-like wave.

**D39. Axial pressures,** averaged over time and circumference, at z = 0, 22.2, 34.9, 47.6, 60.3 and 73.0 mm. Compare with Table 3-2 (368.5 / 323.3 / 292.3 / 281.1 / 255.4 / 238.4 kPa), and check p(65% L)/p(0) ≈ 0.73 (§4.3, p. 103). These pressures are set by fill conditions and don't depend on wave mode (p. 59, p. 72), so they're the best quantitative test. *Caveat (R23):* the measured values come through standoff tubes 145 diameters long (p. 35), which average a strongly oscillating signal non-linearly. Allow about ±10% for that inside the ±20% band.

**D41. Animations:**
- an unrolled view, showing the Fig. 1.10 features A–G;
- a cylinder view (Fig. 1.1 right): the 2D result painted onto a cylinder, which is plotting only;
- a head-end camera view next to the x–t diagram and 2D FFT (Figs. 3.4–3.6).

**D42. Summary:** `results.json` plus `summary.md`, with sections for wave stability, roll stability, performance and pressures, each compared with the paper where a paper value exists.

### 1.9 Expected biases and the success criterion (revised, R7)

| Simplification | Expected effect |
|---|---|
| Premixed, no injector mixing | D/D_CJ higher than Mundt's 0.50–0.80; fewer counter waves (mixing lowers speed and wave count, Bigler et al. [25], p. 15). **The 0.85–0.95 figure is an assumption from typical 2D premixed simulations in the literature, not a derived prediction (R16).** The real loss is large: reactants first meet in the combustor (p. 24), the jets meet 2.16 mm above the face (p. 34), and the average fill height is 3.25 mm (p. 103), so roughly the lower 60% of the real fill layer isn't fully mixed |
| Faster-than-real waves at a fill-limited frequency | The model may settle on fewer waves than the experiment (D44) |
| Contact burning partly numerical | Grid-dependent losses (D43) |
| Adiabatic walls (D16c off) | Gap-width performance trends from heat loss not captured |
| Thickened reaction zone | No cellular structure; detonability limits wrong |
| Single γ and R | Temperatures about 25% too high; product sound speed off |
| No backflow | Plenum coupling missing |
| 2D, no curvature | Good for 76-FI-5; poor for 25 mm cores (Table 4-1) |
| Friction model only | Torque ∝ C_f; pressure torque from injector features missing |
| Straight annulus, choked exit | Thrust not comparable to a nozzled engine; no back-pressure effects |
| Wave-radius ambiguity | f comparison uncertain by 7% (76 mm) to 20–28% (25 mm) |

**Run 937 success criterion.** If waves run at D/D_CJ = 0.85–0.95 and N = 2, then f = N·D/(πd_mean) ≈ 18.8–21.0 kHz. A fill-limited frequency (D44) is 15.8–18.7 kHz. The paper measured 15.84 kHz.

**Pass if all of these hold:**
- N = 2 (if N = 1, apply the D44 diagnostic and variant B before calling it a model failure);
- f between 15 and 22 kHz;
- axial pressures within 20% of Table 3-2;
- mass balance within 2%;
- thrust cross-check within 5%;
- torque cross-check within 5%;
- no floor hits in the averaging window.

### 1.10 Status from the partial build (2026-10-21)

| Item | Result |
|---|---|
| Calibration | ✅ γ = 1.238, Q = 11.08, M_CJ = 7.18; VN state 21.5 MPa, 2116 K; ZND profile matches the shape of Fig. 1.7 (including the temperature dip at the end) |
| Sod shock tube | ✅ p* = 0.3031, u* = 0.9275, shock at 0.851 (exact: 0.3031 / 0.9274 / 0.850) |
| 1D detonation (one-step, E_a/RT₁ = 20, L½ = 1 mm, 0.25 mm grid) | ✅ D = 2490 m/s (+0.8%), peak 20.4 MPa vs 21.5 MPa von Neumann |
| 2D 76-FI-5 with one-step chemistry | ❌ Fresh layer burned at the injector face; wave died by about 90 µs. This motivates R1. |
| Two-step chemistry, friction, revised boundary/ignition, test suite | Not yet implemented |

---

## Part 2: Stage-gated implementation

Each stage ends with a pass condition. **Don't start the next stage until the current one passes.** Times assume a recent Apple-silicon laptop.

| Stage | Work | Pass condition | Est. time |
|---|---|---|---|
| **0. Calibration** | `calibrate.py` per operating point: γ and Q from Mundt's D_CJ and q (D9); fit T_a to GRI-Mech 3.0 ignition delays (time of max dT/dt) in Cantera (D13); two-step constants (D14) | γ, Q, M_CJ as in D10; Arrhenius fit R² ≥ 0.98; fitted VN induction length within 2× of λ/29 ≈ 28 µm; two-step ZND gives D_CJ; full reaction length ≤ h/5 at production settings | 30 min |
| **1. Unit tests** (`tests/unit/`) | Sod; 1D detonation with two-step chemistry at 0.5 mm (Δ = 0.5 mm) and 0.25 mm (Δ = 0.25 mm); FFT direction test | Sod within 1% of exact; D within ±3% of D_CJ at **both**; peak pressure ≥ 80% of von Neumann; a synthetic +x wave classified as +x with the correct N and f | 30 min |
| **2. Solver hygiene** | Compute each face once; log every 5th step; friction source (D16b); optional heat loss (D16c); exit extrapolation (D26); move every constant into `paper_data.yaml` / `model.yaml` / `config.yaml` (D2b) | Stage 1 results unchanged (±0.5%); speed-up ≥ 2×; no stray number literals in `rde_sim/*.py` | 40 min |
| **3. 2D 76-FI-5, sustained detonation** (0.5 mm) | Run 1 ms at Run 937 conditions | A detonation goes around more than 5 times; fill layer ahead of the wave ≥ 60% of the Eq. 4.5 height (else F1); no floor hits | 20 min + runs |
| **4. 76-FI-5 vs Run 937** (0.5 mm, 3 ms) | Full analysis (D32–D44); update C_d once | Mass balance within 2%; thrust and torque cross-checks within 5%; mode classified on the camera signal | 45 min |
| **5. Grid check** | Rerun Stage 4 at 0.25 mm (production). One 25-FI-5 run at 0.125 mm vs 0.25 mm | N unchanged; f within 5%; contact-burning fraction (D43) reported for both grids. Then apply the §1.9 Run 937 criterion | about 30 min + 30 min |
| **6. Six paper cases** (`tests/paper/`) | Part 3, run in parallel on several laptops | Each case reported against its expectation; trend checks evaluated (Part 3.3) | 1–2 h |
| **7. Animation** | `animate.py` on the Stage 5 snapshots | Video plays; Fig. 1.10 features A–G visible | 30 min |

### Fallbacks (decide quickly)

- **F1. Fill layer burns, or the wave dies, in Stage 3:** (a) switch HLL → HLLC; (b) raise T_a by 25%; (c) shorten Δ_I. One at a time, rerunning Stage 1 after each.
- **F2. Fewer waves than the paper:** check D44 (a fill-limited frequency with fast waves leads to fewer waves). Run variant B (D29). Report it; don't tune it away.
- **F3. Blow-ups at the injector edge:** CFL 0.3, then blend the blocked/choked switch over p_w between 0.95 and 1.0 of p₀,pl.
- **F4. Out of time:** cut in this order: cylinder view → C_f sweep → variant B → 0.125 mm check → 0.25 mm (flag the result as unconverged). **Never cut** Stages 1–2 or the balance checks.

---

## Part 3: Test suite from the paper (`tests/paper/`)

### 3.1 Choosing the test points (R12, R22)

Revision 2 put every case at the shared condition of 243 kg/s/m², φ = 1.15. Checking against the paper, that point is a poor test for two reasons:
1. **Back pressure.** At 243 kg/s/m², 25-FI-5 is back-pressure sensitive: 1 wave at 3.5 kPa, 1 wave with a weak counter wave at 52 and 97 kPa (Table 3-3, p. 69). The choked-exit boundary (D26) can only represent insensitive operation.
2. **Mode transitions.** 51-FI-5 at 243 sits on its 1↔2 wave transition (p. 54; Fig. 3.13), so any result "passes". A test that can't fail isn't evidence.

**Primary test points: 320 kg/s/m², φ ≈ 1.18,** on the φ = 1.15 sweep (Figs. 3.19–3.22, p. 60–61). There:
- 25-FI-5 is back-pressure insensitive (Table 3-3: 1 wave at 3.5, 52 and 97 kPa, at 319 kg/s/m², φ 1.19);
- every case except 25-FI-7 has a definite, steady mode with no counter wave;
- the radius study gives a clean wave-count ladder of **3 / 2 / 1** (76 / 51 / 25 mm).

25-FI-7 was only tested near 240 kg/s/m² (Fig. 3.14), so it uses that point, flagged as possibly back-pressure-influenced. **Run 937** (76-FI-5, 240 kg/s/m²) stays as the detailed validation case (Part 1).

**Operating-point calibration at 320 kg/s/m², φ 1.18:**
- fill pressure from Eq. 4.1: p₀ = 523 kPa;
- D_CJ ≈ 2,530 m/s (Fig. 4.3, φ ≈ 1.18 at about 500 kPa) and q ≈ 5.6 MJ/kg (Fig. 4.4), read off the plots, so recalibrate γ and Q per D9 (Stage 0);
- plenum pressure scaled with mass flux and area ratio (choked injectors, as Mundt scaled the gap study, p. 44): p₀,pl = 1.35 MPa × (0.110/σ) × (mflux/240.21);
- C_d tuned per case to hit ṁ.

*Caveat:* Eq. 4.1 was fitted to 76-FI-5 data only (§4.1.1). Mundt found 6–16% spread across geometries (p. 72).

### 3.2 The six configurations (Mundt's two scaling studies, §2.2, pp. 26–28)

| Case | Study | r_o / r_i / L [mm] | σ | Test point [kg/s/m²] | Target ṁ [g/s] | p₀,pl [MPa] | Domain width × depth [mm] | 2D validity |
|---|---|---|---|---|---|---|---|---|
| 76-FI-5 | radius | 38.1 / 33.1 / 76.2 | 0.110 | 320 (+ Run 937 at 240) | 357.9 | 1.80 | 223.7 × 5.0 | good (gap/r_o 0.13) |
| 51-FI-5 | radius | 25.4 / 20.4 / 50.8 | 0.110 | 320 | 230.2 | 1.80 | 143.9 × 5.0 | good (0.20) |
| 25-FI-5 | radius + gap | 12.7 / 7.7 / 25.4 | 0.110 | 320 | 102.5 | 1.80 | 64.1 × 5.0 | fair (0.39) |
| 25-FI-3 | gap | 12.7 / 9.7 / 25.4 | 0.164 | 320 | 67.6 | 1.21 | 70.4 × 3.0 | fair (0.24) |
| 25-FI-7 | gap | 12.7 / 5.7 / 25.4 | 0.0856 | **240** (only data) | 97.1 | 1.73 | 57.8 × 7.0 | poor (0.55) |
| 25-FI-12.7 | gap (coreless) | 12.7 / 0 / 25.4 | 0.0684 | 320 | 162.1 | 2.89 | **79.8 × 6.35** | **approximate** |

Sources: Tables 2-1 (p. 28) and 4-1 (p. 80). Target ṁ = mass flux × annulus area.

**The coreless case.** A flattened annulus can't represent an engine with no inner wall. The **simplest approximation:** the wave runs along the outer wall, so the domain width is the outer circumference (2πr_o = 79.8 mm), and the depth is chosen so width × depth = πr_o², preserving the total flow area and mass flow (6.35 mm). Missing: the gas in the centre, radial expansion, and the radial surges Mundt saw (p. 70). The result is labelled **approximate** and excluded from the hard checks. Mundt himself imposed a virtual 3 mm annulus for this case's video processing (p. 42).

### 3.3 Expected results and checks

**Per-case expectations** (paper values read off the figures; ±5% reading accuracy):

| Case | Paper result at the test point | Source | Discriminating? |
|---|---|---|---|
| 76-FI-5 @ 240 (Run 937) | 2 waves, no counter wave, 15.84 kHz, 1893 m/s, D/D_CJ 0.766 | Table 3-2 p. 52 | yes |
| 76-FI-5 @ 320 | 3 waves, no counter wave, ≈ 21.5 kHz, D_spin ≈ 1,715 m/s | Figs. 3.19, 3.21, 3.22 pp. 60–61 | yes |
| 51-FI-5 @ 320 | 2 waves, no counter wave, ≈ 20.6 kHz, D_spin ≈ 1,640 m/s | Fig. 3.13 p. 55; Figs. 3.21–3.22 | yes |
| 25-FI-5 @ 320 | 1 wave, no counter wave, ≈ 21 kHz, D_spin ≈ 1,670 m/s; same result at 3.5–97 kPa back pressure | Table 3-3 p. 69; Fig. 3.16 p. 57; Figs. 3.21–3.22 | yes |
| 25-FI-3 @ 320 | 1 wave, no counter wave (frequency from Fig. 3.30 when building `cases.yaml`) | Fig. 3.17 p. 58 | yes |
| 25-FI-7 @ 240 | 1 wave | Fig. 3.14 p. 56 | weakly (back-pressure sensitivity unknown) |
| 25-FI-12.7 @ 320 | 1 wave, no counter wave | Fig. 3.18 p. 58 | approximate model |

**Cross-study trend checks** (`trends.py`):

| # | Trend in the paper | Check | Type |
|---|---|---|---|
| T1 | Wave count increases with radius at fixed mass flux (Fig. 3.19, p. 59) | At 320: N(76) > N(51) > N(25-FI-5) (paper: 3 > 2 > 1) | hard |
| T2 | All detonative 25 mm cases ran 1 wave (§3.3.3, p. 64; Figs. 3.14–3.17) | N = 1 for 25-FI-3/5/7 | hard |
| T3 | Pressure at 65% length nearly independent of geometry at equal mass flux (Fig. 3.20: about 390–420 kPa at 320; 6–16% spread, p. 72) | Spread of p(65%) across the cored 320 cases ≤ 20%, and each within 20% of Fig. 3.20 | hard |
| T4 | Mundt's fill-height frequency predictor (§4.3, D44) | f_sim vs f_pred = mflux·R·T₀/(p₀·3.25 mm) (≈ 18 kHz at 320) | comparison (±20%) |
| T5 | D/D_CJ between 0.50 and 0.80 (pp. 60, 64) | Report; the simulation is expected higher (§1.9) | comparison |
| T6 | No counter waves at the 320 points (Figs. 3.13–3.22) | No strong counter wave (camera-signal ratio < 58%) in any case at 320 | hard |
| T7 | Gap-width performance trend (§1.5.2) | Only with D16c on: report chamber pressure vs gap at constant mass flux | comparison |
| T8 | Thrust, torque, wall-shear/thrust per case | Report; wall shear/thrust against Sawada's 8.8% | report only (no paper thrust data) |

"Hard" checks gate Stage 6. "Comparison" checks are reported with the bias explanation, not tuned away.

### 3.4 After iteration 1

1. The 243 kg/s/m² shared point and the 25-FI-5 back-pressure sweep (Table 3-3), using a downstream buffer region (D26 limitation). These test exactly the regime the first version can't represent.
2. Higher-fidelity physics, one at a time: HLLC → injector backflow with a simple plenum → two-γ thermodynamics → Cantera/SDToolbox calibration for other propellants or φ (Mundt §4.1.2) → wall heat transfer as a default → 3D with real injectors (needs a GPU, a cluster or an established package).
3. Torque-reduction studies: counter-rotating starts; nozzle or aerospike exits (needs an area change, so 2D axisymmetric or 3D).

---

## Part 4: Viewing results at every stage

Results must be visible **during** development, not just at the end. Every stage writes pictures, and every long run can be watched and inspected while it's still running.

### 4.1 What each stage shows

| Stage | Visual output (in `runs/<name>/` or `tests/out/`) | What to look for |
|---|---|---|
| 0. Calibration | `znd_profile.png`: M, p, T, ξ, λ against distance behind the shock; `induction_fit.png`: ln τ_ind vs 1/T with the fitted line | Shape like Fig. 1.7 (VN spike, M → 1, slight temperature dip at the end); straight-line fit |
| 1. Unit tests | `sod.png` (numerical vs exact); `det1d_profile.png` (pressure profile with the VN and CJ levels marked); `det1d_xt.png` (shock position vs time with the fitted speed); `fft_direction.png` | Exact Sod curves overlaid; plateau at the CJ level; straight shock path |
| 2. Hygiene | `speedup.txt`, and the Stage 1 plots regenerated | Identical to Stage 1 |
| 3. First 2D run | **Live** `live.png` (see 4.2), and `quicklook_*.png` every 20 µs of engine time | A fresh layer at the bottom; a detonation running in +x; Fig. 1.10 features |
| 4–5. Analysis | `waves.png` (x–t, 2D FFT, arrival-time f over time, torque and thrust history); `pressures.png` (axial profile vs Table 3-2); `summary.md` | N, f, mode; pressures against the paper markers |
| 6. Paper cases | One `summary.md` + `waves.png` per case; `tests/out/report.md` with every check and a ✅/❌ | All hard checks green |
| 7. Animation | `unrolled.mp4`, `cylinder.mp4`, `headend.mp4` | The Fig. 1.1-like view |

### 4.2 Watching a run while it runs

- **`live.png`, refreshed every N steps** (setting `live_every_us` in `model.yaml`, default 5 µs of engine time). Four panels: pressure (log scale), temperature, ξ, λ, all on the unrolled domain with axes in mm. Plus a strip with the current time, max pressure, ṁ in/out, floor-hit count and wall-clock time. Open it in any image viewer that auto-refreshes, or in VS Code.
- **`progress.json`** next to it, rewritten each time: simulated time, steps, current wave-count estimate (FFT of the last 100 µs of probe data), current f, ṁ in/out. Something can watch it, or you can print it with `cat`.
- **`--live` flag (optional):** opens a matplotlib window that redraws the same panels. Off by default, since it slows the run.

### 4.3 Inspecting a running or finished run

- **Checkpoints:** every 0.25 ms of engine time, `run.py` saves `state_<t_us>.npz` (full conserved fields + time) and flushes the logs (`log.npz`, written atomically: write to a temporary file, then rename).
  - **Restart:** `run.py --resume runs/<name>` continues from the latest checkpoint, so a long run can be stopped and continued.
- **`view.py runs/<name>`:** an interactive matplotlib scrubber with a slider over all snapshots and checkpoints, a choice of field (p, T, ξ, λ, Mach, u, v), and a click-to-plot vertical/horizontal cut. It works on a run that's still going.
- **`analyze.py runs/<name> --partial`:** runs the full analysis on whatever has been logged so far (using the latest time window that's available), so wave count, f, thrust and torque can be checked mid-run.
- **`quicklook.py runs/<name> [time]`:** writes a single-snapshot PNG (all fields) for quick sharing.

### 4.4 Rule

Every stage report to the owner includes its Part 4.1 images. A stage isn't "passed" until its pass condition holds **and** the pictures look physically sensible (spot-checked by eye: no checkerboarding, no waves going the wrong way, no fields stuck at floors).

---

## Appendix A: Equations and algorithms (exact specification)

### A.1 Gas and calibration

- Mixture at φ: x_CH4 = φ/(φ + 2), MW = x_CH4·16.043 + (1 − x_CH4)·31.999 g/mol, R = 8314.46/MW.
- c_p = γR/(γ − 1); a₁ = √(γRT₁); Q = q/(c_pT₁).
- **CJ Mach (Eq. 1.7, upper root):** M_CJ² = 1 + (γ+1)Q + √[(1 + (γ+1)Q)² − 1].
- **γ calibration (D9):** solve D_CJ(γ) = M_CJ(γ)·a₁(γ) = D_CJ,paper for γ by bisection on [1.05, 1.6], with q held at the paper value.
- **VN state (normal shock at M₁ = M_CJ):**
  - p_VN/p₁ = (2γM₁² − (γ−1))/(γ+1);
  - T_VN/T₁ = p_VN/p₁ · ((γ−1)M₁² + 2)/((γ+1)M₁²);
  - M_VN² = ((γ−1)M₁² + 2)/(2γM₁² − (γ−1));
  - u_VN (shock frame) = M_VN·√(γRT_VN).
- **CJ state:** p_CJ/p₁ = (1 + γM₁²)/(1 + γ); T_CJ/T₁ = [(1 + γM₁²)/((1+γ)M₁)]².
- **ZND path for plots (Eqs. 1.6, 1.9, 1.10):**
  - at heat released Q_x = ξQ, solve Eq. 1.6 for the **subsonic** root M₂ ∈ (0, 1]. The function is monotonic in M₂ on (0, 1], so brentq on [1e−6, 1] works, returning 1 if f(1) ≤ 0;
  - T/T₁ = (M₂/M₁)²·[(1+γM₁²)/(1+γM₂²)]²; p/p₁ = (1+γM₁²)/(1+γM₂²).
  - Distance: dx = u·dt, with dt from the two-step rates (A.3).
- **Fill pressure (Eq. 4.1, kPa, mass flux in kg/s/m²):** p₀ = −531.2 + 2.965·m + 526.6·φ + 0.0009336·m² − 1.418·m·φ − 54.73·φ².

### A.2 Induction fit to GRI-Mech 3.0 (D13)

1. `gas = ct.Solution('gri30.yaml')`, composition `CH4:φ, O2:2`.
2. For T in nine values from 1600 to 2400 K: set `gas.TP = T, p_VN`, run `ct.IdealGasReactor` (constant volume) in a `ReactorNet` to 10 ms or until T has risen 1500 K, record T(t), and take **τ_ind = time of max dT/dt** (Mundt p. 74).
3. Fit ln τ_ind = ln A + T_a/T by least squares. Report T_a, R² and τ_ind(T_VN).
4. **Cross-check:** Δ_I,real = u_VN·τ_ind(T_VN) should be within 2× of λ/29 ≈ 28 µm.

### A.3 Two-step chemistry (D12, D14)

- Rates:
  - **ω_λ** = ρ·k_I·exp(−T_a/T) if λ < 1, else 0;
  - **ω_ξ** = ρ·k_R·(1 − ξ) if λ ≥ 1, else 0.
- Constants: k_I = (u_VN/Δ_I)·exp(T_a/T_VN), k_R = u_VN/Δ_R, where T_VN and u_VN come from the single-γ model (A.1), and Δ_I, Δ_R from `model.yaml`.
- Clip λ and ξ to [0, 1] after each stage.
- Heat release enters through E (A.4). There is no separate energy source.

### A.4 Conservative variables, fluxes, sources

- U = (ρ, ρu, ρv, E, ρξ, ρλ); E = p/(γ−1) + ½ρ(u² + v²) + ρq(1 − ξ).
- x-flux F = (ρu, ρu² + p, ρuv, (E + p)u, ρξu, ρλu); y-flux G is the same with v as the normal velocity and p in the v-momentum entry.
- Sources:
  - chemistry, (0, 0, 0, 0, ω_ξ, ω_λ);
  - friction, −(C_f/gap)·ρ|**u**|·(0, u, v, 0, 0, 0), which is the "2 walls × ½" factor of D16b;
  - optional heat loss, (0, 0, 0, −(C_f/gap)·ρ|**u**|c_p(T − T_w), 0, 0).

### A.5 Numerics

- **Primitives** W = (ρ, u, v, p, ξ, λ), with p = (γ−1)(E − ½ρ|**u**|² − ρq(1 − ξ)).
- **MUSCL–minmod at face i+½:**
  - W_L = W_i + ½·minmod(W_i − W_{i−1}, W_{i+1} − W_i);
  - W_R = W_{i+1} − ½·minmod(W_{i+1} − W_i, W_{i+2} − W_{i+1});
  - minmod(a, b) = 0 if ab ≤ 0, otherwise whichever of a and b has the smaller magnitude.
- **HLL (Davis wave speeds):**
  - s_L = min(u_nL − a_L, u_nR − a_R) and s_R = max(u_nL + a_L, u_nR + a_R);
  - flux = F_L if s_L ≥ 0, F_R if s_R ≤ 0, otherwise (s_R F_L − s_L F_R + s_L s_R (U_R − U_L))/(s_R − s_L).
  - **Compute each face flux once** and store it, then difference.
- **Time step:** Δt = CFL / (max(|u| + a)/Δx + max(|v| + a)/Δy).
- **SSP-RK2:** U¹ = Uⁿ + Δt·L(Uⁿ); Uⁿ⁺¹ = ½Uⁿ + ½(U¹ + Δt·L(U¹)). Apply floors and clipping after each stage.
- **Ghost cells:** 2 per side.
  - x: periodic copy.
  - Bottom: zero-gradient copies, used only for MUSCL slopes; the bottom face flux itself is the injector flux (A.6).
  - Top: zero-gradient extrapolation (D26).
  - Unit tests: reflective walls by mirroring with the normal velocity negated.
- **Floors** (D21) with a counter.

### A.6 Injector face flux (D24)

- Per bottom face, with p_w = pressure of the first interior cell, plenum (p₀, T₀), σ and C_d:
  - p_cr = p₀(2/(γ+1))^{γ/(γ−1)}.
  - **If p_w ≥ p₀:** flux = (0, 0, p_w, 0, 0, 0).
  - **Otherwise:**
    - G* = C_d·p₀·√(γ/(RT₀))·(2/(γ+1))^{(γ+1)/(2(γ−1))} if p_w < p_cr;
    - else G = C_d·√[2γ/(γ−1)·p₀ρ₀·((p_w/p₀)^{2/γ} − (p_w/p₀)^{(γ+1)/γ})] with ρ₀ = p₀/(RT₀).
  - Jet velocity u_j = √[2c_pT₀(1 − (p_w/p₀)^{(γ−1)/γ})].
  - Flux = (σG, 0, σG·u_j + p_w, σG(c_pT₀ + q), 0, 0), the second-to-last including the chemical energy of fresh gas.
- Record σG per column for the mass-in diagnostic.

### A.7 Domain, initial state, ignition

- **Annulus:** width W = π(r_o + r_i); depth = gap.
- **Coreless:** W = 2πr_o; depth = r_o/2 (so W·depth = πr_o²).
- Height = L. nx = round(W/Δx), ny = round(L/Δx), then reset Δx = W/nx and Δy = L/ny.
- **Initial state (D27):**
  - p = p₀ everywhere;
  - y < h₀: T = 300 K, ξ = λ = 0. h₀ = Eq. 4.5 with the paper's measured f where one exists (3.8 mm for Run 937), otherwise Mundt's mean of 3.25 mm;
  - above: T = 1500 K, ξ = λ = 1;
  - u = v = 0.
- **Ignition (D28):** for each of N_ign patches at x₀ = 0.1W + n·W/N_ign:
  - cells x₀ ≤ x < x₀ + 10 mm, y < h₀ → p = 2p_CJ, T = T_CJ, ξ = λ = 1;
  - cells x₀ − 20 mm ≤ x < x₀, y < h₀ → products (T = 1500 K, ξ = λ = 1).

### A.8 C_d tuning (D25)

Start at the value that gives ṁ_target with always-choked injection: C_d = ṁ_target/(σ·A_e·G*(C_d = 1)). After the first 3 ms run, set C_d ← C_d·ṁ_target/⟨ṁ_in⟩ and rerun once. Report both.

---

## Appendix B: Contents of the three data files (D2b)

### B.1 `paper_data.yaml` (from Mundt 2023 unless stated)

Every entry stores the value, its units in the key name, and `src: "<table/figure/eq>, p. <printed page>"`. Values read off plots also carry `read_off_plot: true` (±5%).

| Group | Entries |
|---|---|
| Geometry (Table 2-1 p. 28, Table 4-1 p. 80), per config | 76-FI-5: OD 76.2, gap 5.0, L 76.2, r_i 33.1, pairs 72, fuel Ø 0.79, ox Ø 1.24, σ 0.110. 51-FI-5: 50.8 / 5.0 / 50.8 / 20.4 / 72 / 0.64 / 0.99 / 0.110. 25-FI-5: 25.4 / 5.0 / 25.4 / 7.7 / 48 / 0.51 / 0.81 / 0.110. 25-FI-3: 25.4 / 3.0 / 25.4 / 9.7 / 48 / 0.51 / 0.81 / 0.164. 25-FI-7: 25.4 / 7.0 / 25.4 / 5.7 / 48 / 0.51 / 0.81 / 0.0856. 25-FI-12.7: 25.4 / 12.7 / 25.4 / 0.0 / 48 / 0.51 / 0.81 / 0.0684 (all lengths mm). V/(SA·L): 0.033, 0.049, 0.098, 0.059, 0.138, 0.250 |
| Injector (§2.2.4 pp. 34–35) | inclination 30°; impingement height 2.16 mm; impingement diameter = OD − 5 mm; O/F area ratio 2.50; pair spacing 2.34 mm (25 mm engines) |
| Instrument z-locations (Table 2-2 p. 37), mm | 76-FI-5: 0 (front wall), 22.2, 34.9, 47.6, 60.3, 73.0 (pre-detonator also at 73.0), duct 85.7, 98.4. 51-FI-5: 26.7, 33.7 (pre-det), 40.6. 25-FI: 16.5, 18.5, 20.3, 22.4 (pre-det 22.4), duct 38.1. Stations at 62.4% / 66.3% / 65.0% of length for 76 / 51 / 25 mm (p. 59) |
| Run 937 (Table 3-2 p. 52) | mass flux 240.21 kg/s/m²; φ 1.176; ṁ 268.65 g/s; burn 0.696 s; back pressure 100.2 kPa; initial engine T 293 K; N 2; counter rotation none; video f 15.84 kHz; periphery speed 1893 m/s; D_CJ 2471 m/s; fraction of CJ 0.766; PCB f 15.89 / 15.89 kHz; orifice p O₂ 5991.5, CH₄ 5500.0 kPa; orifice T 297 / 295 K; plenum p O₂ 1309.5, CH₄ 1399.4 kPa; plenum T 303 / 301 K; p(z) at 0 / 22.2 / 34.9 / 47.6 / 60.3 / 73.0 / 85.7 / 98.4 mm = 368.5 / 323.3 / 292.3 / 281.1 / 255.4 / 238.4 / 68.4 / 59.5 kPa |
| Table 3-3 (25-FI-5 back-pressure sweep, p. 69) | rows (ṁ g/s, mass flux, φ; result at 3.5 / 52 / 97 kPa): (102.29, 319.20, 1.19; 1 / 1 / 1), (89.53, 279.40, 1.19; 1 / 1 / 1), (83.36, 260.10, 1.18; 1 / 1 / 1+weakCW), (76.57, 239.00, 1.17; 1 / 1+wCW / 1+wCW), (70.51, 220.10, 1.17; 1+wCW ×3), (63.76, 199.00, 1.18; 1+wCW ×3), (57.36, 179.00, 1.17; 1+wCW ×3), (51.38, 160.30, 1.16; Defl / 1+wCW / 1+wCW), (44.96, 140.30, 1.17; Defl / 1+wCW / 1+wCW), (38.97, 121.60, 1.16; Defl / Defl / 1+wCW), (33.06, 103.20, 1.16; Defl / Pulsing / Unsteady det.), (26.48, 82.60, 1.17; Defl / Pulsing / Unsteady det.), (20.23, 63.10, 1.18; Defl / Pulsing / 1 wave) |
| Section 4 constants | Eq. 4.1 coefficients (−531.2, 2.965, 526.6, 0.0009336, −1.418, −54.73; R² 0.998; p. 74); cell size = 29 × induction length (p. 74); induction time = time of max dT/dt (p. 74); initial T 300 K (p. 74); fill height mean 3.25 mm, range 2–7 mm (pp. 78, 103); h/λ ≥ 4.5 efficient-thrust guideline (p. 90); r_i/λ boundaries 6 and 26 (p. 85); Fig. 4.6 regions: deflagration r_i/gap < 2.5 & mflux < 200, counter wave r_i/gap < 4.8 & mflux < 280 (p. 80); p(65% L) ≈ 0.73·p₀ (p. 103); f predicted to +5% mean with h = 3.25 mm (p. 103); u_VN ≈ 270 m/s (p. 98); ≈ 9% heat-release power to angular momentum (p. 98, scaling argument only); D/D_CJ mostly 0.50–0.80 (pp. 60, 64, 103) |
| Section 2 constants | counter-wave threshold 58% of primary power (pp. 42–43); averaging = last 100 ms (p. 42); wave speed uses the outer circumference (pp. 42, 59); camera 240,000 fps (p. 23); facility back pressure down to 2 kPa (p. 23); 25-FI-5 pulsing ≈ 16.6 kHz (p. 57) |
| Plot readings (±5%) | q(φ 1.18, 400 kPa) ≈ 5.5 MJ/kg, q(φ 1.18, 500 kPa) ≈ 5.6 (Fig. 4.4 p. 77); D_CJ(φ 1.18, ~500 kPa) ≈ 2530 m/s (Fig. 4.3 p. 76); λ(φ ≈ 1.18, 350 kPa) ≈ 0.8 mm (Fig. 4.2 p. 75). At 320 kg/s/m², φ 1.15 sweep (Figs. 3.19–3.22 pp. 60–61): 76-FI-5 N 3, f 21.5 kHz, D_spin 1715 m/s; 51-FI-5 N 2, f 20.6 kHz, D_spin 1640; 25-FI-5 N 1, f 21.0 kHz, D_spin 1670; p(~65% L) ≈ 395 / 395 / 420 kPa. Modes at 320 from Figs. 3.13, 3.16–3.18: 51 → 2 waves; 25-FI-5 / 25-FI-3 / 25-FI-12.7 → 1 wave; 25-FI-7 → 1 wave at ~240 (Fig. 3.14) |
| Sawada et al. 2022, J. Propulsion & Power 38(1) 59–70 | torque 0.149 ± 0.009 N·m; thrust 48.1 ± 0.9 N; azimuthal shear force 8.8 ± 0.6% of thrust; ṁ 87 ± 9 g/s; φ 1.43 ± 0.28; 0.77 ± 0.10% of exit kinetic energy azimuthal |
| Molecular weights | CH₄ 16.043, O₂ 31.999 g/mol |

### B.2 `model.yaml` (defaults)

```yaml
chemistry:   {T_a_K: fit_gri30, T_a_fallback_K: 20000, delta_I_mm: 0.25, delta_R_mm: 0.25,
              delta_debug_mm: 0.5}
walls:       {C_f: 0.003, C_f_sweep: [0.0015, 0.003, 0.006], heat_loss: false, T_wall_K: 300}
numerics:    {dx_mm: 0.25, dx_debug_mm: 0.5, cfl: 0.4, rho_floor: 1.0e-6, p_floor_Pa: 1.0,
              t_end_ms: 3.0, avg_window_ms: 1.5, n_subwindows: 3}
init:        {products_T_K: 1500, fill_height: eq45}
ignition:    {width_mm: 10, p_factor_of_CJ: 2.0, products_behind_mm: 20, n_patches: 1}
injector:    {Cd_initial: auto, Cd_retune_once: true}
logging:     {every_n_steps: 5, probe_y_mm: 1.0, snapshot_every_us: 2.0, snapshot_last_ms: 0.3,
              checkpoint_every_ms: 0.25, live_every_us: 5.0}
classify:    {cw_none_below: 0.05, cw_strong_at: 0.58, deflag_D_over_DCJ_below: 0.4,
              deflag_peak_over_mean_below: 5.0, steady_f_tolerance: 0.05,
              contact_burn_distance_mm: 2.0, fill_detect_xi: 0.5, fill_detect_ahead_mm: 2.0}
roll:        {example_inertias_kgm2: [0.005, 0.01, 0.05]}
```

### B.3 `config.yaml` (example: Run 937)

```yaml
name: run937_76FI5
geometry:  {r_outer_mm: 38.1, r_inner_mm: 33.1, length_mm: 76.2, area_ratio: 0.110}
operating: {propellant: CH4-O2, phi: 1.176, mass_flux: 240.21, p_plenum_kPa: 1350.0,
            T_plenum_K: 300.0, p_back_kPa: 100.2}
calibration_targets: {D_CJ: paper:run937.D_CJ, q_MJkg: paper:plot.q_phi118_400kPa}
```

`paper:` references resolve into `paper_data.yaml`. Your own engine replaces the numbers; for a non-Mundt operating point, D_CJ and q come from Cantera/CEA (iteration 2).

---

## Appendix C: Diagnostics definitions (exact)

- **Averaging window:** the last `avg_window_ms` of the run; every time average is weighted by Δt.
- **x–t data:** pressure at row j_p = floor(probe_y/Δy), every logged step, resampled onto a uniform time grid by linear interpolation before any FFT.
- **2D FFT:** subtract the mean, multiply by a Hanning window in time (none in x, since it's periodic), P = |fft2|². The wavenumber axis is `fftfreq(nx, 1/nx)` (integers); the frequency axis is `fftfreq(nt, Δt)`. Consider only f > 2 kHz.
  - The primary peak is the maximum over k ≠ 0, giving N = |k|, with direction from the sign (convention §0.4).
  - Counter power = max over f > 2 kHz at wavenumber −k_peak.
  - Pulsing power = max at k = 0.
- **Arrival-time frequency:** at each probe, find pressure peaks exceeding 3× the local median that are at least 0.5/f_FFT apart in time. f = 1/mean(spacing), averaged over probes. Report the spread.
- **Camera signal:** at each x, the sum over j of ω_ξ·q·Δy (heat-release rate per unit width). Logged like the probes. The counter-wave ratio uses the 2D FFT of this signal.
- **Wave-frame Mach:** at each snapshot, locate the front as the argmax of probe-row pressure.
  - M₁ = (D_sim − u_ahead)/a_ahead, averaged over 3–12 cells ahead of the front.
  - M₂ = |D_sim − u|/a at the first cell behind the front with ξ > 0.95.
- **Fill height:** in the column 2 mm ahead of the front, the number of cells from y = 0 with ξ < 0.5, times Δy.
- **Contact burning fraction:** in each snapshot, find the wave fronts as pressure peaks along the probe row. Heat release ω_ξ·q in cells whose x-distance from the nearest front exceeds 2 mm counts as contact burning. Report its time integral divided by the total heat release.
- **Thrust:** F_exit = depth·Σ_i(ρv² + p − p_a)Δx in the top row. F_inj = depth·Σ_i(σG·u_j + p_w − p_a)Δx − (axial friction integrated over the domain). They must agree within 5% when averaged.
- **Torque:**
  - τ_engine = −r_m·depth·Σ_cells S_fric,u·ΔxΔy (the negative of the friction torque on the gas);
  - exhaust angular-momentum flux = r_m·depth·Σ_i(ρuv)Δx in the top row;
  - in a steady average, τ_engine + exhaust flux ≈ 0 (within 5%).
  - Circumferential wall-shear force = |τ_engine|/r_m; ratio to F_exit is compared with Sawada's 8.8%.
- **Pressures:** time-mean, x-mean pressure per row, interpolated to the paper's z locations. Use the bottom row as z = 0.
- **I_sp** = F_exit/(⟨ṁ_in⟩·9.80665).

---

## Appendix D: Lessons from the partial build (don't repeat these)

1. **One-step chemistry with low E_a burns the fill layer at the injector face** (fresh gas numerically mixed with ~2,500 K products in the first cell). The wave died within ~90 µs. That's why the plan uses two-step chemistry.
2. **One-step with high E_a (50–70)** stopped that burning, but 1D detonations failed to initiate at 0.25 mm (1,400–1,500 m/s).
3. **Ignition energy matters:** a 5 mm patch at the CJ state gave a decoupled shock (870 m/s); 10 mm at 2× p_CJ worked.
4. **Floors must suit the units:** a 1 Pa floor silently clipped the nondimensional Sod test (p = 0.1). Unit tests set their own floors.
5. **A thick reaction zone kills layer detonations:** a reaction zone comparable to the fill height lets the wave lose energy upward. Keep the full reaction length ≤ h/5.
6. **Performance:** computing every face flux twice and logging every step cost about 2–3× (measured ~3×10⁶ cell-steps/s on 2 slow cores).
7. **Don't `pkill -f` a pattern that matches your own shell command line.**
