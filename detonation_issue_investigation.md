# RDE-001 detonation issue: external investigation notes

**What this is:** a detailed record of a read-only review and Q&A session about
why the reduced 2D Run 937 simulation shows no sustained detonation (RDE-001),
plus the follow-on discussion on chemistry modelling, 2D vs 3D, torque, and GPU
compute planning.

**Author / provenance:** Claude Code (Opus 5.5) session with the repository owner,
October 21–22, 2026. Repository snapshot at the time of the main analysis:
commit `b8b2b51` ("Audit physical reaction scales and gate further engine
changes"), branch `main`, clean working tree. Until this file was written, no
repository files were changed during the session.

**Status:** analysis and recommendations only. It is **not** the project plan and
does not override [first_sim_plan.md](first_sim_plan.md), [HANDOFF.md](HANDOFF.md)
or [docs/verification/run937_unresolved.md](docs/verification/run937_unresolved.md).
Everything marked *estimate* was not measured. Literature statements marked
*(abstract/snippet only)* come from abstracts or search excerpts because the
full texts were paywalled.

---

## 0. Executive summary

1. **Root cause of RDE-001 (high confidence, confirmed by Codex's C3 controls):**
   the one-step surrogate's reaction zone was artificially thickened to
   L½ = 1 mm (shock-to-50% heat release; 95% at 4.18 mm) so a 0.5 mm grid could
   resolve it. The fresh-mixture layer stayed at its physical height of
   **~3.8 mm**. The layer is thinner than the model's own reaction zone:
   - fill height ÷ L½ ≈ **3.8 in the model**, versus **~96 in reality**
     (real half-heat distance 0.0395 mm from the D3 Cantera/GRI reference);
   - the lateral expansion through the hot products above the layer quenches
     the wave before most of its heat is released.

   C3 showed a formed detonation **fails in a 3.8 mm layer** (on both grids and
   with an aligned interface) but **stays coupled in a 15 mm layer**.
2. **The 2D solver itself is not the problem.** C1/C2: planar formed waves
   propagate within ~0.3% of the surrogate CJ speed; no direction or row bugs;
   conservation at round-off.
3. **The blast igniter was also weak** (C4). The D1 engine wave never became a
   detonation; it decayed to ~1000 m/s shocks within ~30 µs. Ignition realism
   is not the main issue, though.
4. **Why it isn't fixed yet:** the remedy choice is blocked by framing, not by
   missing knowledge. C5a treats the options as either "physical chemistry"
   (infeasible: 0.04 mm zones, 91M+ steps) or "arbitrary rate tuning"
   (forbidden). The middle option was never adopted: a **declared surrogate
   reaction length chosen in advance from a measured criterion** (fill height ÷
   L½ ≥ ~15–25), together with a better chemistry step. Revision 3 of the plan
   had such a rule ("full reaction length ≤ h/5"). Revision 4 correctly fixed
   revision 3's arithmetic error but dropped the constraint entirely.
5. **Fix options:**
   - (a) shorten the surrogate's L½ to ~0.18–0.25 mm, with ~0.09–0.125 mm cells
     near the layer;
   - (b) replace the worst-case global chemistry step limit with a per-cell /
     substepped / stiff split chemistry step;
   - (c) start from a formed detonation profile instead of the blast patch;
   - (d) alternatively, as NETL does, use fast near-physical kinetics with split
     stiff chemistry and accept an under-resolved reaction zone, after a 1D
     calibration of the numerics.
6. **Longer-term direction discussed:** a two- or three-tier simulation stack
   for a design-iteration loop:
   - a fast 2D tier on the cylinder surface, with gap-averaged friction,
     heat-loss and centrifugal closures ("2.5D");
   - an optional thin 3D annulus (structured r, θ, z grid);
   - a precise 3D tier: an established GPU-capable code such as PeleC, a
     12–20-species reduced mechanism, LES, ~100 µm cells, roughly one 8×H100
     node.

   Torque needs wall shear modelling in every tier, and will need calibration
   against torque measurements (Sawada et al.).

---

## 1. Repository context at review time

- Commits (oldest → newest): `1c66d43` first commit → `6ae65ad` foundation →
  `5ed8aa7` bounded runs/checkpoints/budgets → `b5a1960` propagation diagnostics
  and RDE-001 documented → `0f435aa` … `b8b2b51` (controlled 2D tests C1–C5a).
- Key documents:
  - [HANDOFF.md](HANDOFF.md) and [first_sim_plan.md](first_sim_plan.md)
    (current plan; revision 6, later updated);
  - [docs/verification/run937_unresolved.md](docs/verification/run937_unresolved.md)
    (the RDE-001 issue record);
  - [docs/verification/controlled_2d_progress.md](docs/verification/controlled_2d_progress.md)
    (C1–C5 results);
  - [docs/verification/c5_model_readiness.md](docs/verification/c5_model_readiness.md)
    (C5a gate);
  - [docs/verification/mundt_model_audit.md](docs/verification/mundt_model_audit.md)
    (paper versus implementation audit);
  - [docs/verification/d3_investigation.md](docs/verification/d3_investigation.md)
    (Cantera/SDToolbox reference, contact burning, refinement);
  - [docs/plans/first_sim_plan_rev3.md](docs/plans/first_sim_plan_rev3.md) and
    [first_sim_plan_rev4.md](docs/plans/first_sim_plan_rev4.md) (historical);
  - [sim_plan_review.md](sim_plan_review.md) (local, Git-ignored review of
    revision 3).
- Code:
  - `rde_sim_starter/`: `solver.py` (~309 lines; HLL, minmod MUSCL, SSP-RK2) and
    `physics.py` (~127 lines; one-step EOS and source, injector);
  - the rest (`run.py`, `controlled.py`, `experiments.py`, `analyze.py`,
    `plot.py`, `reference.py`, `coupling.py`, `model_audit.py`) is
    orchestration, checks, references and plotting;
  - total ~3,000 lines.
- Environment: macOS x86_64 (Intel), Python 3.12, Numba; **4 physical CPU
  cores**; no CUDA GPU.
- Surrogate calibration (`calib.json`, `config.yaml`):

  | Parameter | Value |
  |---|---|
  | γ | 1.23845 |
  | R | 318.673 J/(kg K) |
  | q | 5.5 MJ/kg |
  | Ea/(R T₁) | 20 |
  | k | 2.5225e6 /s |
  | L½ | 1.0 mm |
  | p₁ | 377.917 kPa |
  | T₁ | 300 K |
  | D_CJ | 2471 m/s (fitted) |
  | von Neumann state | 21.53 MPa / 2116 K |
  | CJ state | 10.95 MPa / 4885 K |

---

## 2. Early review of the PNG outputs (before D1–C5)

### `rde_sim_starter/` supplied PNGs (inherited, pre-foundation)

- **`znd_profile.png`** shows the calibrated one-step ZND structure. It is
  physically consistent:
  - Mach 7.18 upstream; 0.335 just behind the shock, rising to 1 at the end of
    the reaction (CJ condition);
  - pressure 21.5 → 11 MPa (von Neumann/CJ ≈ 2);
  - the temperature peaks slightly before the end of the reaction and then dips
    (correct for constant γ);
  - half-reacted at 1.00 mm, ~95% at ~4 mm.

  Issues:
  - T_CJ = 4885 K is too hot (real ≈ 3994 K, no dissociation);
  - the zone is deliberately thickened;
  - there is effectively no induction zone: Ea/R·T_vN ≈ 2.8 means reaction
    starts immediately behind the shock.
- **`test_1d.png`** is a 1D detonation in a closed tube at 95 µs.
  - VN spike 20.4 MPa versus 21.5 MPa theory; closed-end plateau ~4 MPa versus
    ~3.8 MPa ideal Taylor-wave theory.
  - Wave speed 2490 m/s (+0.8%). This is circular: γ was fitted to 2471 m/s.
  - Ignition transient: ~1550 m/s for the first ~30 µs.
  - Produced by the old solver, which clipped values silently.
- **`dbg_fields.png`** is an old 2D snapshot (60 and 90 µs).
  - Width 224 mm (correct mean circumference), but the axial extent is only
    25 mm (the config says 76.2 mm).
  - The fresh layer is only ~1 mm (~2 cells).
  - At 90 µs, the pressure structures are shocks running through burned gas,
    decoupled from any fresh mixture.
  - No colorbars or units.
  - Consistent with the inherited "extinction near 90 µs" report.

### `runs/foundation_session/`

- **`sod.png`:** nondimensional Sod at t = 0.2 matches the exact solution
  (p* 0.30314 vs 0.30313; u* 0.92747 vs 0.92745; shock 0.849 vs 0.850).
  The contact is smeared over several cells. That's typical of HLL and relevant
  to the fresh/product interface in 2D.
- **`znd.png`:** the same ZND as above with clearer labels; the calibration
  reproduces.

---

## 3. RDE-001 diagnosis from the D1/D2 engine runs

### D1 evidence (`runs/d1_run937/plots/`)

- **Setup:**
  - 447 × 152 cells (~0.5 mm);
  - 3.8 mm fresh layer with 1500 K products above;
  - 10 mm ignition patch at 2×p_CJ and T_CJ, clipped to the fresh layer;
  - 20 mm burned strip "behind" the patch;
  - everything starts at rest;
  - run to 189.394 µs (three reference passage intervals at 15.84 kHz).
- **Space-time plot at z = 0.752 mm (the key evidence):**
  - reaction at the ring stops within ~25–35 µs;
  - the reaction front moves only ~17 mm in the first ~15 µs (~1100 m/s);
  - after ~40 µs only ~1000 m/s pressure ridges remain. In the fresh gas that's
    about Mach 3, with a post-shock temperature around 630 K and a chemical
    time around 5 ms, so no ignition.

  **The wave never became a detonation.** A CJ wave would cross the 224 mm
  circumference in ~90 µs.
- **Refill works:**
  - the fresh layer grows from 3.8 mm to ~12–25 mm, consistent with an
    injection speed of ~57 m/s (240 kg/s/m² ÷ ~4 kg/m³);
  - inflow 267.8 g/s.
- **Totals:**
  - total chemical conversion ~87 J, against ~92 J in the initial layer plus
    ~280 J injected;
  - final peak pressure 0.45 MPa.
- **The outlet is ruled out as the cause:** outflow begins only at ~43 µs, after
  the failure, and the exit is mostly at axial Mach > 1 afterwards.
- **D2** (7.6 mm initial layer, `runs/d2_fill_7p6mm`) also failed. A bigger
  layer improves startup, but the refill height returns to ~3.8 mm in operation
  anyway.

### Ranked causes

1. **Layer too thin for the thickened reaction zone** (main cause).
   - The lateral expansion crosses the 3.8 mm layer in ~4 µs, at the post-shock
     sound speed of ~914 m/s.
   - The surrogate needs ~5 µs to reach 95% heat release.
   - In reality, heat release is ~30–40× faster than the relief.
   - The product gas above the layer is ~5× lighter (1500 K), which weakens
     confinement.
2. **Igniter too weak and venting** (contributes).
   - The direct-initiation energy rises steeply with reaction length.
   - The 10 × 3.8 mm patch vents upward into the hot products.
   - The 1D tube needed ~30 µs and ~50 mm to transition, even with no venting.
3. **Grid resolution** (aggravating): ~2 cells per L½; spatially unconverged.
4. **Low priority or ruled out:**
   - the outlet (timing, see above);
   - injector refill (works; the failure happens before refill matters);
   - numerical contact burning: D3 measured ~726 J/m² per 20 µs at 0.5 mm,
     against a layer inventory of ~83,000 J/m² (~1%);
   - a 2D-specific bug (later ruled out by C1/C2);
   - thermochemistry fidelity (secondary).

---

## 4. Codex's controlled tests C1–C5a (summary of `controlled_2d_progress.md`)

| Test | What it did | Result |
|---|---|---|
| C1 | 1D, 8-row strip, rotated strip and open-ended cases, 0.5 mm, 95 µs | Fields identical; 2455.944 m/s fits; residuals ~4e-15 |
| C2 | Conservative formed CJ/ZND profile, filled strips at 0.5/0.25/0.125 mm, 40 µs | 2478.2/2473.0/2472.1 m/s vs 2471; attached reaction; source-step halving negligible |
| C3a | Formed wave in **3.8 mm** vs **15 mm** layer under 1500 K products, 0.5 mm, 40 µs | 3.8 mm: shock and reaction separate, gap 20–30 mm, wall pressure 2.74 MPa, front ~1300 m/s. 15 mm: reaction stays 1.5–2 mm behind the front |
| C3b | 3.8 mm at 0.25 mm | Same loss of coupling (2.76 MPa, ~1297 m/s); conversion changes 15.6% |
| C3c | 3.8 mm with face-aligned interface | Same loss of coupling. The initial mixed cell is not the explanation |
| C3d/e | 15 mm at 0.25 mm (continued after a diagnostic speed-bound stop) | Coupling retained to 40 µs; wall pressure 27.4 MPa; transverse structure |
| C4 | Blast patch vs formed wave in the 15 mm layer | Blast weaker (6.5 MPa, 1590–1650 m/s), with some continuing reaction. "Change only the igniter" is not a fix |
| C5a | Algebraic feasibility of physical lengths | Rate-only changes can't match 50/90/95% lengths simultaneously (factors 25.3/69.3/81.8). A two-point Ea/k fit gives Ea/RT₁ = 71.6, k = 2.18e10/s (not adopted). With the current global source limit: 2.079 ps steps, ≥91M steps. Engine run (C6) blocked |

**Interpretation given in the session:** C3 confirmed the layer-thickness
hypothesis. C5a stopped because physical-scale chemistry is infeasible and
anything in between was framed as "tuning". That framing is the blocker.

### Scale-similarity observation

The inviscid Euler equations with a one-step source at fixed Ea are invariant
under x → x/s, t → t/s, k → s·k. So **C3's 15 mm / L½ 1 mm / 0.5 mm-cell /
40 µs case is mathematically equivalent to a 3.75 mm layer / L½ 0.25 mm /
0.125 mm cells / 10 µs.** Evidence that L½ ≈ 0.25 mm sustains a ~3.8 mm layer
already exists, but only over a short window (10 µs).

---

## 5. Why the reaction zone is thick, and is it correct? (Mundt evidence)

### Origin in the project

- The 1 mm length comes from the original starter. It has no paper source.
- The only written rationale is in revision 3 of the plan
  ([first_sim_plan_rev3.md:303](docs/plans/first_sim_plan_rev3.md#L303)):

  > "deliberately thickened … to fit the grid. This is the one chemistry
  > parameter that can't follow the paper. Using Mundt's 28 µm directly would
  > need cells of about 3 µm, roughly 10⁸–10⁹ cells in 2D."

- **Revision 3 already identified the problem:**
  - decision R11: an effective cell size "4× the fill layer";
  - it proposed the constraint **"full reaction length ≤ h/5"**, citing Mundt
    pp. 11–12 and 90;
  - it proposed Δ_I = Δ_R = 0.25 mm in a two-step model
    ([:36](docs/plans/first_sim_plan_rev3.md#L36), [:290-306](docs/plans/first_sim_plan_rev3.md#L290-L306)).
- **Revision 3's arithmetic was wrong.** It claimed 0.75 mm "full", but the zone
  actually reaches 0.518/1.652/2.275 mm at 50/90/95%. The review
  ([sim_plan_review.md](sim_plan_review.md) §4.1) caught this.
- **Revision 4/6 removed the error and the constraint together** ("do not impose
  an unsupported universal reaction-length/fill-height ratio",
  [first_sim_plan.md:143](first_sim_plan.md#L143)), and reverted to the
  inherited 1 mm one-step model. Nothing then stopped a reaction zone as thick as
  the layer.

### What Mundt (2023) says (printed page numbers; PDF page = printed + 16)

- **p. 9, Eq. 1.11:** the one-step Arrhenius law is introductory. k and Ea are
  just "constants", with no values. "Activation energy has the largest effect on
  the ZND structure." The paper provides no rate constants.
- **p. 10:** ZND/CJ speeds "agree reasonably well with the mean velocity seen in
  experiments". This supports thickening for *speed and pressure*.
- **pp. 11–12:** curvature lowers wave speed 15–20%, with complete decay at the
  smallest radius (Frolov). Cell size varies across curved channels (Pan,
  Nakayama). "Detonation cell size has often been linked to minimum dimensions
  and operating range limitations in RDEs" (Bykovskii). Kawasaki: the wave
  detaches from the inner core as the inner radius shrinks; the ratio of fill
  height to cell size governs efficient thrust.
- **p. 13, Fig. 1.10 (Kailasanath):** fresh-reactant layer (G); burning in the
  mixing region (E) is a loss.
- **p. 19:** Nordeen & Schwer: resonance "reduced the allowed detonation
  height" → instability and failure. Shepard et al.: the "ignition transient did
  not affect the results of steady-state operation".
- **pp. 74–75:** Mundt's actual chemistry is physical: Cantera + SDToolbox +
  GRI-Mech 3.0, premixed, 300 K. Induction time is taken at the maximum dT/dt,
  and cell size = 29 × induction length. The calculated cells "tend to
  underestimate cell size".
- **pp. 77–78, Eq. 4.5:** fill height h = mflux·R·T₀/p₀ · 1/f, ranging 2–7 mm
  (mostly 2–4 mm). It is set by the flow, not chosen.
- **p. 90:** h/λ ≥ 4.5 is a "theorized efficient thrust limit … a guideline and
  not a rule"; every engine had results above it.
- **p. 21:** the 76 mm engine "closely follows" the AFRL RDRE. Both were tested
  for a multi-university CFD validation workshop; "example CFD results" are in
  Strakey & Ferguson [52] and Pal et al. [53].

### Comparison

| | Real Run 937 | Current model |
|---|---:|---:|
| Fill height h | ~3.8 mm | ~3.8 mm |
| Half-heat distance | 0.0395 mm | 1.0 mm |
| h ÷ half-heat distance | ~96 | ~3.8 |
| h ÷ cell size | ~4.8 (λ ≈ 0.8 mm, Fig. 4.2 estimate) | ~0.13–0.25 *if* the ×29 rule applied |

The review correctly notes the ×29 factor doesn't transfer to the surrogate, so
treat that last cell as indicative only. C3 measured the outcome directly.

**Verdict:** thickening the reaction zone is necessary and standard. Thickening
it 25× regardless of fill height contradicts the paper's framing, which ties
wave survival to detonation length scale relative to fill height.

---

## 6. Fix options for RDE-001 (none implemented; user decision pending)

1. **Declared surrogate reaction length from a measured criterion.**
   - Target fill height ÷ L½ ≥ 15 (minimum, as evidenced by C3) to ~20–25
     (margin). That means **L½ ≈ 0.25 mm (minimum) or ~0.15–0.19 mm (margin)**,
     with ≥ 2 cells per L½ (C2 shows 2 cells per L½ propagates planar waves
     correctly).
   - Label it a surrogate. Fix it *before* the engine run. Update the plan's
     "no rate tuning" rule so it explicitly permits a pre-declared,
     criterion-based length.
   - Optionally make it a two-step induction/heat-release model fitted to
     Cantera/GRI ignition delays (revision 3 step D13), with event-timing and
     mixed-state checks first.
2. **Fix the chemistry time step.**
   - The current global worst-case bound k(1 + 4e⁻²A/B) gives a 14.45 ns step at
     a source fraction of 0.05. That's ~4× smaller than the flow step at 0.5 mm.
   - The bound is ~3.5e6 /s, while actual peak rates in C3 are ~2.8e5 /s, so it
     is ~12× conservative.
   - Use a per-cell actual-rate bound, per-cell substepping, or operator-split
     stiff ODE integration. Verify against the existing closed-reactor and
     DOP853 tests.
3. **Start from a formed detonation profile** (the C2/C3 machinery), not the
   blast patch.
4. **Alternative, as practised by NETL (section 8):** fast near-physical kinetics
   with split stiff chemistry, accepting an under-resolved reaction zone. This
   needs a 1D calibration of wave speed against time step and scheme first,
   because under-resolved detonations are scheme-sensitive.
5. **Suggested sequence:**
   1. rerun the C3 3.8 mm layer at the new L½ over a longer travel distance;
   2. fix the chemistry step;
   3. run the engine from a formed start for 189 µs;
   4. then run milliseconds long for steady operation.

### Cost estimates for option 1 (*estimates*)

Engine at L½ = 0.25 mm with 0.125 mm cells: ~1.09M cells.

| Chemistry step | Steps for 189 µs |
|---|---|
| Current global limit | ~52k |
| Flow-limited | ~14k |

D1 throughput was ~9e8 cell-steps in ~8 min (~1.9M cell-steps/s on 2 threads).

| Run | CPU (current step limit) | CPU (flow-limited) |
|---|---|---|
| 189 µs | ~8 h | ~2 h |
| 5 ms (steady operation) | — | ~2–3 days |

---

## 7. Cantera/GRI: reference, not the engine inside the solver

- **The repo already uses Cantera 3.2 + GRI-Mech 3.0 + vendored SDToolbox** for
  the physical reference: `reference.py`, `requirements-reference.txt`,
  `rde_sim_starter/vendor/sdtoolbox`.
  - D3 results: CJ 2531.86 m/s; q 5.41847 MJ/kg; T_CJ 3994.14 K; half-heat
    distance 0.03952 mm; 95% at 0.05108 mm.
  - The 2.46% difference from Mundt's tabulated 2471 m/s is unreconciled; NASA
    CEA was not run.
- **GRI (53 species, 325 reactions) in every CFD cell is not viable here:**
  - ~58 transported quantities instead of 5;
  - stiff chemistry dominates the cost;
  - it must resolve 0.04 mm zones, i.e. ~0.004–0.01 mm cells, which means
    ~10⁸–10⁹ cells in 2D.

  The thickness problem is about resolution, not about which library is used.
- **Standard practice:**
  - detailed chemistry provides the reference;
  - a calibrated reduced model (two-step, or a small reduced mechanism) runs in
    the CFD;
  - production 3D uses a 12–20-species reduced mechanism in an established
    solver with mesh refinement, validated against the detailed mechanism in
    0D/1D.

---

## 8. How the reference work was done

- **Mundt's thesis** (University of Washington PhD, 2023; chair Carl Knowlen) is
  experimental. Its only calculations are ZND (Cantera/SDToolbox) and NASA CEA,
  laptop-scale. The text mentions no computing resources.
- **CFD of the matching AFRL engine** (Mundt's citations [52] and [53]):
  - [52] **Strakey & Ferguson (NETL, DOE), AIAA 2022-1113.** Full text read; it
    models the **AFRL** engine against **AFRL** data, not Mundt's.
  - [53] **Pal, Demir, Kundu & Som (Argonne, DOE), AIAA 2021-3642.** Not read
    (inaccessible).
- **NETL setup and results:**

  | Item | Detail |
  |---|---|
  | Geometry | 76.2 mm OD / 66.2 mm ID / 76.2 mm long, 72 impinging pairs (same as 76-FI-5); exhaust plenum included |
  | Operating point | O₂ 0.207 kg/s, CH₄ 0.060 kg/s, φ = 1.16 (≈ Run 937's 268.65 g/s, φ 1.176) |
  | Code | ANSYS Fluent 20.1, full 3D, LES; pressure-based implicit and density-based explicit (AUSM, RK4) solvers |
  | Chemistry | 12 species / 38 steps, operator-split stiff ODE |
  | Walls | 300 K fixed-temperature (heat loss) |
  | Grids | 400 / 200 / 100 / 70 µm in the detonation region → 2.1M / 9.2M / … / 85.2M cells |
  | Start | Kernel in a 2° sector of the first 5 mm at 4 MPa / 3000 K; steady operation after 3–5 ms; averaged over 2–3 ms |
  | Wave count | 400 µm → **1 wave (wrong)**; ≤ 200 µm → 2 waves |
  | Wave speed | Approaches the measured **1810 m/s** at 70 µm |
  | Thrust | Within 8% of **370 N**; heat loss matters |
  | Mean wall pressure | "Fairly insensitive" to grid |
  | 1D scheme study | Wave speed 1400–3000 m/s depending on scheme and time step; explicit solver +115 m/s when dt went from 5e-9 to 1e-9 s |
  | Cost | 200 µm: **7.1 h per wave lap on 2000 cores** (pressure-based), 11.1 h (density-based); 20–30 laps to steady + ≥ 10 to average; 100 µm explicit: **~5 weeks on 2000 cores** |

- **Key lessons:**
  1. Production simulations **do not resolve the real reaction zone** (70 µm ≫
     40 µm). They use fast kinetics with split stiff chemistry and converge on
     engine-level quantities.
  2. Under-resolved detonations need a 1D calibration of the numerics.
- **University of Michigan ICNC 2025 abstract** (AFRL engine) *(snippet only)*:
  wave count and speed accurate, ~20% error in the pressure distribution;
  sensitive to grid and local resolution.

---

## 9. Ignition: real versus model

- **Real (Mundt pp. 26, 37–39):**
  - spark-ignited pre-detonator tube, L/D = 50, with its own CH₄/O₂ supply at
    φ ≈ 0.95 from dedicated 1000 cc tanks;
  - fill 200 ms, then sparks at ≥ 500 Hz for 100 ms;
  - enters through a **3.2 mm radial port at z = 73 mm** (near the exit),
    clocked at 210°;
  - visible ignition 10–20 ms after the command;
  - rotating waves emerge through a transient;
  - ignition reliability was a practical issue for the 25 mm engines (p. 40).
  - Whether the annulus was full of propellant at the moment of ignition isn't
    stated in the text (Fig. 2.11 is a timing chart).
- **Model:** a pre-layered running-engine state (3.8 mm fresh layer + 1500 K
  products, hot products before any combustion), with an energy-only 10 mm patch
  at the injector face (2×p_CJ, T_CJ, at rest) and a direction-steering burned
  strip.
- **Assessment:**
  - For **steady-operation predictions** (the design-loop goal), an artificial
    start is standard (NETL uses a kernel) and acceptable, provided:
    - it reliably forms a wave (formed profile rather than blast, per C4);
    - the run lasts long enough to forget the start (**ms, not 189 µs**);
    - start-independence is checked, e.g. 1 vs 2 initial waves, because of
      possible multiple stable modes.
  - Predicting **ignition reliability** needs the pre-detonator jet, the startup
    filling and deflagration-to-detonation transition in 3D. A separate study;
    out of scope for now.

---

## 10. Multi-tier simulation strategy for a design-iteration loop

The goal: eventually use the repo to validate design upgrades of a new RDE.
The user's priority quantities are **wave propagation stability** and
**mechanical torque**.

### Tiers

- **Tier A (fast, 2D/2.5D):**
  - unrolled or cylinder-surface (θ, z) model;
  - calibrated reduced chemistry with fill height ÷ L½ ≥ ~15–25;
  - closures: per-wall friction (inner r_i, outer r_o, injector face), wall heat
    loss, centrifugal pressure split;
  - an optional curvature-loss term calibrated elsewhere;
  - used for screening and ranking designs.
- **Option B (focused 2D):** an (r, θ) curved channel, for curvature and
  inner-wall detachment limits and to calibrate Tier A's curvature terms.
- **Option C (middle tier):** a thin 3D annulus on a structured cylindrical
  (r, θ, z) grid. A natural extension of the existing solver. Captures
  curvature, inner/outer walls and detachment; still premixed unless injection
  is extended.
- **Tier B (precise 3D):**
  - established solver: PeleC (open source, GPU, mesh refinement, embedded
    boundaries for CAD) or Fluent/CONVERGE (commercial);
  - 12–20-species reduced mechanism validated against GRI;
  - LES, injectors, exhaust plenum, wall heat loss;
  - ≤ 200 µm (wave count), 100 µm for production numbers.

### Precision targets

Converge engine-level quantities, not reaction-zone resolution:

| Quantity | Target |
|---|---|
| Wave count / mode | Correct |
| Wave speed | ≤ ~5–10% (AFRL 1810 m/s) |
| Thrust | ≤ ~8% (AFRL 370 N) |
| Mean wall pressure | ~10–20% |

Procedure:
1. validate the mechanism against GRI in 0D/1D;
2. calibrate the numerics in 1D (wave speed vs dt and scheme);
3. run a grid convergence on these quantities;
4. validate on the AFRL/NETL point and Mundt Run 937;
5. recalibrate Tier A against Tier B whenever designs move outside the range it
   was validated for.

### Validation datasets for this engine size

- **Mundt Run 937** (UW): 2 waves, 15.84 kHz, 1893 m/s at the outer radius
  (≈ 1769 m/s at the mean radius); wall pressures 368.5 → 238.4 kPa at
  0–73 mm; **no thrust or torque measured**.
- **AFRL baseline**, via NETL: 1810 m/s, 2 waves, 370 N thrust, CTAP pressures.

---

## 11. What 2D loses for stability and torque

### Torque

- On smooth axisymmetric walls, pressure can't create torque about the axis.
  Torque comes only from:
  - **wall shear** (inner and outer walls, injector face);
  - pressure on non-axisymmetric features (injector holes, ports, centre-body
    end, nozzle features);
  - any injected swirl (Mundt's impinging pairs are not designed to swirl).
- With inviscid/slip walls, gas angular momentum is conserved. Injection carries
  zero, so **the time-averaged torque is exactly zero** (already noted as R3 in
  revision 3).
- **2D loses:**
  - the inner and outer wall boundary layers, so friction must be a closure;
  - the different shear and lever arms of the two walls (r_i/r_o = 0.87);
  - the ports and features;
  - the centrifugal pressure difference across the gap, ≈ ρu_θ²·g/r_m ≈ 14% of
    dynamic pressure (g/r_m ≈ 0.14).
- **2D keeps:** the core u_θ(θ, z, t) history. With a friction closure that
  gives relative or plausibility torque estimates only.
- **3D still needs wall models:** the viscous sublayer is µm-scale; NETL's
  70–200 µm grids don't resolve it.
- **A torque measurement is needed** to trust any tier. The repo has none for
  Mundt's engine; Sawada's data is for a different engine (section 13).

### Stability

- **2D keeps:** the refill/survival mechanism (RDE-001), wave–wave interactions,
  counter-rotating collisions, oblique shock/slip line, and calibrated trends.
  Best for thin annuli (gap/r ≈ 0.14 here).
- **2D loses:**
  - curvature compression at the outer wall and expansion at the inner wall,
    and **inner-wall detachment** (Mundt pp. 11–12);
  - discrete non-premixed impinging injection and mixing (jets meet 2.16 mm
    above the face; pp. 15–17);
  - wall losses (real waves run ~28% below CJ), so a lossless model is too
    stable;
  - the 3D cellular front (Fig. 4.12 r_i/λ limits; p. 90 h/λ);
  - downstream geometry and resonance (p. 19);
  - reliable mode selection.
- **Net:** 2D tells *whether* a wave can survive under idealized conditions and
  how designs *rank*. It can't reliably give absolute margins, wave count or
  detachment for radius/gap changes. Which way it errs isn't fixed, so it must
  be calibrated.

### The "wrapped cylinder" question

**Wrapping the 2D rectangle onto a cylinder adds no physics by itself.**
- The cylinder surface is intrinsically flat (developable): x = r·θ exactly, and
  the surface equations are identical to the unrolled ones.
- The centrifugal ρu_θ²/r term acts normal to the surface and only enters the
  radial momentum equation, which a surface model doesn't solve.
- All ρu_r·(…)/r terms vanish with u_r = 0.

Radial effects must be added deliberately as closure terms (the 2.5D model).
The gap then appears as a parameter, not a grid dimension:

| Effect | Closure | Quality |
|---|---|---|
| Inner/outer wall friction | τ = ½ρ c_f u\|u\| per wall; area per volume 2r_i/(r_o²−r_i²) and 2r_o/(r_o²−r_i²); torque = r_i∫τ_i dA + r_o∫τ_o dA | Structure good; magnitude = c_f assumption |
| Injector-face friction | Same law on the z = 0 boundary | Same |
| Wall heat loss | Energy sink with a heat-transfer coefficient (Reynolds analogy) | Assumed; gives a realistic speed deficit |
| Centrifugal split | Δp ≈ ρu_θ²·g/r_m → reconstructed p̄ ± Δp/2 at the two walls | Physically derived; little effect on averaged dynamics; distinguishes the walls |
| Curvature compression/expansion | Calibrated loss vs r_i ÷ λ and g/r | Empirical; calibrate from option B or 3D |
| Inner-wall detachment | **Cannot be simulated**; indicator only (reconstructed inner-wall state, r_i ÷ λ criterion) | Indicator |

Revision 3's wall-friction closure (D16b) was planned but never implemented.

### Option C (thin 3D) on a few CPUs (*estimates*)

Assumed throughput: ~2M cell-steps/s on 4 cores, ~4M on 8, and a flow-limited
dt of ~14 ns.

| Configuration | Cells | 189 µs | 1 ms | 5 ms |
|---|---:|---:|---:|---:|
| Full engine: 1790 (θ, 0.125 mm) × 272 (z, stretched, 0.125 mm near the face) × 10 (r, 0.5 mm) | ~4.9M | ~9 h | ~2 days | ~10 days |
| Smoke test: half circumference, 25 mm axial, 8 radial cells | ~1.3M | ~2–3 h | ~13 h | ~3 days |
| Software check only: 0.5 mm, current thick chemistry | ~0.7M | ~1 h | — | — |

- Halve for 8 cores.
- **Multiply by ~4 if the global chemistry step limit stays.**
- The half circumference forces an even, symmetric mode.

### Expected distortion from coarse cells

- **Dominant effect:** the thickened chemistry sets the model's length scale.
  With L½ 0.25 mm versus real 0.04 mm, all margins are ~6× smaller than reality:
  fill height ÷ L½ 15 vs 96, r_i ÷ L½ 130 vs 840, g ÷ L½ 20 vs 125.
- So the model is **biased pessimistic**: earlier failure, detachment and mode
  loss. Contact smearing (D3) adds premature burning in the same direction.
- **Robustness ranking:**
  1. time-averaged pressure (robust);
  2. wave speed (moderate, a few to ~10%);
  3. wave count (fragile);
  4. detachment and stability limits (qualitative, pessimistic);
  5. torque (dominated by the closure, ~×2).
- **How to measure it:**
  - 6 vs 12 radial cells;
  - a fine (r, θ) curved-channel reference with ~100 cells across the gap;
  - L½ 0.25 vs 0.18 mm;
  - c_f ×0.5/×2 sweep, checking whether design rankings hold.

---

## 12. GPU computing

### Fit and constraints

- Explicit structured solvers with per-cell chemistry suit GPUs well.
- They are **memory-bandwidth-bound**: ~0.5–1 floating-point operation per byte
  for the fluxes. The stiff chemistry is more compute-bound.
- **FP64 is required:**
  - data-centre GPUs (A100/H100/H200, AMD MI250X/MI300X) handle it;
  - consumer cards (RTX 4090, L40S) run FP64 at ~1/64 speed — avoid;
  - Apple GPUs have no FP64;
  - the user's Intel Mac has no CUDA GPU, so in practice this means cloud
    GPUs or a cluster.
- Check FP64 specifically for the newest NVIDIA parts; some AI-focused models
  have reduced it.

### Specs (approximate vendor peaks, from my own knowledge)

| GPU | FP64 vector | Memory | Bandwidth |
|---|---:|---:|---:|
| V100 | 7.8 TF | 16/32 GB | 0.9 TB/s |
| A100 | 9.7 TF | 40/80 GB | 1.6–2.0 TB/s |
| H100 SXM | 34 TF | 80 GB | 3.35 TB/s |
| H200 | 34 TF | 141 GB | 4.8 TB/s |
| MI250X | 47.9 TF | 128 GB | 3.2 TB/s |
| MI300X | 81.7 TF | 192 GB | 5.3 TB/s |

Ignore "FP64 tensor" figures; CFD stencils mostly can't use them. **There is no
NVIDIA "A200";** the user likely meant the H200.

### Software options

- **Tier A:** port the ~440-line solver core to JAX (differentiable; JAX-Fluids
  is an example) or numba-cuda/CuPy. Keep the CPU version as the
  reference-test oracle.
- **Tier B:**
  - **PeleC** (AMReX; CUDA/HIP; mesh refinement; embedded boundaries; detailed
    chemistry via PelePhysics, which converts Cantera mechanisms). Used for RDE
    studies; GPU use in those specific studies not confirmed.
  - An AMReX-based hypersonic reacting solver (arXiv 2412.00900).
  - **Fluent GPU solver:** compressible flow since 2024 R2, but **no
    confirmation found** that density-based finite-rate chemistry runs on GPU.
    Check the feature table.
  - **CONVERGE:** RDE features; GPU support not confirmed.
  - **detonationFoam:** CPU only in practice.
  - The University of Michigan ran full-geometry RDE on thousands of GPUs (ORNL
    Summit) with neural-network chemistry.

### Effort and cost (*estimates*)

| | Effort | Run time | Cost per run |
|---|---|---|---|
| Tier A port | ~1–2 weeks (+ a few days for I/O and checkpoints) | 5 ms at 0.125 mm (~4e11 cell-steps): ~10–25 min on one A100/H100 (assumed 0.3–1e9 cell-steps/s); at 0.0625 mm: ~1–3 h | < $1–10 at ~$2–4 per GPU-hour |
| Tier B (PeleC) | ~1–3 months to set up and validate (mechanism conversion, embedded geometry, custom boundary conditions, diagnostics) | See below | See below |

Tier B compute per converged case (~4 ms):

| Grid | Cells | GPU-hours | Notes |
|---|---:|---:|---|
| 200 µm | ~10M | ~10–300 | |
| 100 µm | ~40M | ~100–2,500 | ~$200–10k |
| 70 µm | ~85M | ~300–8,000 | |

For comparison, NETL's CPU runs used ~5e5 core-hours (200 µm) and ~1.7e6
core-hours (100 µm explicit). Fluent's implicit unstructured solver cost about
**2 ms of core time per cell per step**, derived from NETL's numbers.

### GPU count for "good but not insane" precision (100 µm, ~40M cells, ~100 GB)

- **Memory minimum:** 2× H100 or 1× H200.
- **Diminishing returns** below ~2–5M cells per GPU.
- **Sweet spot: one 8×H100 (or H200) NVLink node:**
  - 4 GPUs: ~1–26 days;
  - **8 GPUs: ~0.5–13 days**;
  - 16 GPUs (2 nodes, InfiniBand): ~0.4–9 days.
- 200 µm: 1–4 GPUs. 70 µm: 16–32 GPUs.
- **Pick by cost per unit of work:** an H100 is ~1.7–2.5× an A100 for this
  workload, so it's cheaper overall if priced below ~2× the A100. SXM rather
  than PCIe for multi-GPU. AMD MI300X if the solver supports HIP (PeleC does).

### Storage per 100 µm case (~40M cells, ~18 saved quantities)

| Output | Size | Advice |
|---|---:|---|
| Full 3D snapshot (single precision) | ~3 GB | Every ~50 µs → ~250 GB |
| Checkpoint (double precision) | ~6–10 GB | Keep 2–3 + milestones → ~50 GB |
| 2D slices (mid-gap + injector plane, every ~1 µs) | ~45 MB each | Last 1 ms → ~100–150 GB |
| Probes and integrals | MB–GB | Every step |
| **Working total** | **~0.5–1 TB** | Archive ~50–200 GB after reduction |

- Saving every full field at movie rate would be ~6 TB per case. Reduce
  in-situ: wave tracking, torque and pressure averages.
- A 10-case campaign needs ~5–10 TB of scratch storage.

### Recommended path

1. Benchmark one wave lap at 200–400 µm on 1–2 H100s.
2. Validate at 200 µm on 4 GPUs.
3. Production at 100 µm on one 8-GPU node.
4. Spot checks at 70 µm.
5. Funding options: NSF ACCESS; DOE ALCC/INCITE; university clusters;
   cloud research or startup credits; specialist GPU clouds.

---

## 13. Literature on torque and the friction-closure approach

### Measured torque, and wall shear as the mechanism *(abstract/snippet only)*

- **Sawada et al., "Torque Around the Axial Direction on RDEs", *J. Propulsion
  and Power* 38(1):59–70, 2022, doi 10.2514/1.B38374.**
  - Six-axis force sensor: **0.149 N·m with 48.1 N thrust**.
  - Torque follows the wave direction and is offset when waves run both ways.
  - At ~87 g/s and φ ≈ 1.43: **azimuthal shear force ≈ 8.8% of thrust**;
    ~0.77% of exit kinetic energy goes into azimuthal velocity.
- **Sawada et al., "The circumferential force on a cylindrical RDE", *Proc.
  Combust. Inst.* 40, 105490, 2024.**
  - "These waves induce a strong swirl near the inlet surface, generating
    circumferential shear stress on the surface of the combustion chamber. This
    stress works as torque in the axial direction."
  - Maximum 0.127 N·m.
  - Torque increases with wave speed (largest near CJ) and with wave count.
  - Compares annular and cylindrical chambers.
- **S-520-31 sounding-rocket flight demonstration** (*J. Spacecraft and Rockets*,
  doi 10.2514/1.A35401): roll torque estimated from the roll rate in flight;
  side jet used to control roll; torque "thought to be generated by the
  multidimensional flowfield".

### Friction and heat-loss source terms in reduced detonation models

These exist, but are used for losses and wave propagation, not torque:
- quasi-2D thin-channel H₂–O₂–Ar detonations with a spatially varying
  skin-friction coefficient plus Reynolds-analogy heat loss (*Combustion and
  Flame*, 2025): waves survive losing up to ~30% of released energy to the walls;
- NASA RDE wave-speed study: the source vector "normally" holds wall friction,
  area change and heat transfer, but the study itself runs adiabatic and
  inviscid;
- reduced-order rocket-RDE wall heat flux (Bartz + Darcy–Weisbach; *Aerospace*,
  2026);
- classic detonation loss theory, from my own knowledge, not this search: Fay's
  boundary-layer velocity deficit; Mirels' boundary layer behind moving shocks.

### Torque in models and CFD

- The Caltech EDL analytical thrust model sets torque to zero, neglecting
  friction.
- Many 3D CFD studies use slip adiabatic walls, so zero torque.
- The *Annual Review* (Nonidealities in RDEs) notes much CFD is 2D unwrapped.
- A URANS loss study, cited in a 2020 3D wall-effects paper, found viscous losses
  small versus heat loss. That's fine for thrust, but torque *is* the viscous
  effect.
- **No published study was found that predicts RDE torque from a wall-friction
  closure, or computes it from 3D wall shear** (paywalls; search coverage
  limited).

### Verdict and recommended use

The friction approach is physically grounded (shear is the measured mechanism)
and uses standard source-term machinery, but **predicting torque this way is not
established practice.** Use it as a calibrated model:
1. implement per-wall friction + heat loss, preferably with a moving-shock
   (Mirels-type) boundary-layer closure rather than a steady flat-plate c_f;
2. **calibrate c_f by simulating Sawada's engine and operating point** to match
   the ~8.8% shear-to-thrust ratio (0.149 N·m at 48.1 N);
3. check, without refitting, the PCI 2024 trends: torque vs wave speed and wave
   count, annular vs cylindrical;
4. report design torques as relative estimates with a c_f ×0.5/×2 band;
5. validate against 3D wall-modelled simulation and, eventually, the project's
   own six-axis torque measurement.

---

## 14. Open decisions for the user / suggested next steps

1. **Approve a declared surrogate reaction length** (L½ 0.25 mm minimum, or
   ~0.15–0.19 mm for margin), and amend the "no rate tuning" rule to permit
   pre-declared, criterion-based lengths. Alternatively, choose the NETL-style
   fast-kinetics/split-stiff-chemistry route.
2. Implement a non-global chemistry step (per-cell bound, substepping, or split
   stiff ODE) and verify it against the existing reactor tests.
3. Rerun the C3 3.8 mm layer at the new L½ with a longer travel distance. Then
   run the engine from a formed start for 189 µs, then milliseconds for steady
   operation, with a start-independence check (1 vs 2 initial waves).
4. Add the Tier A closures (per-wall friction, heat loss, centrifugal split) and
   calibrate c_f against Sawada.
5. Decide the strategic stack:
   - GPU port of Tier A;
   - option C thin 3D as the middle tier;
   - PeleC (or a commercial code) for Tier B;
   - validation on AFRL/NETL and Run 937.
6. Plan a project torque measurement (six-axis load cell). No public torque data
   exists for Mundt's engine.

---

## 15. Caveats and unverified items

- All compute times, costs and GPU throughputs are **estimates**, not
  benchmarks. Cloud prices change quickly.
- The Pal et al. (Argonne), Sawada (JPP 2022, PCI 2024) and S-520-31 papers, and
  the Michigan ICNC abstract, were not read in full (403 or paywall).
  Statements come from abstracts and repository listings.
- The NETL paper was read in full (PDF text extracted).
- Mundt PDF text was extracted with pypdf into a session-temporary scratchpad
  (`/private/tmp/claude-501/.../scratchpad/mundt/`). It may no longer exist;
  re-extract if needed. Figures (e.g., Fig. 2.11 timing, Fig. 4.2 cell sizes)
  were not readable as text.
- The fill height ÷ L½ threshold of ~15 comes from one bounded 40 µs C3
  contrast, in a straight layer without injection or curvature. It is not a
  converged critical height.
- The h/λ ≈ 4.8 real-engine value uses the inherited ~0.8 mm plot estimate of
  cell size.

---

## 16. Sources

### Repository

- [HANDOFF.md](HANDOFF.md), [first_sim_plan.md](first_sim_plan.md), [README.md](README.md)
- [docs/verification/run937_unresolved.md](docs/verification/run937_unresolved.md)
- [docs/verification/controlled_2d_progress.md](docs/verification/controlled_2d_progress.md)
- [docs/verification/c5_model_readiness.md](docs/verification/c5_model_readiness.md)
- [docs/verification/mundt_model_audit.md](docs/verification/mundt_model_audit.md)
- [docs/verification/d1_propagation.md](docs/verification/d1_propagation.md)
- [docs/verification/d3_investigation.md](docs/verification/d3_investigation.md)
- [docs/plans/first_sim_plan_rev3.md](docs/plans/first_sim_plan_rev3.md), [docs/plans/first_sim_plan_rev4.md](docs/plans/first_sim_plan_rev4.md)
- [rde_sim_starter/run.py](rde_sim_starter/run.py) (initialization at ~L186–217), [rde_sim_starter/config.yaml](rde_sim_starter/config.yaml), [rde_sim_starter/calib.json](rde_sim_starter/calib.json)
- Run outputs (Git-ignored): `rde_sim_starter/runs/d1_run937/plots/{fields,space_time,diagnostics}.png`, `runs/foundation_session/`, `runs/c*`
- [Mundt2023.pdf](Mundt2023.pdf): T. Mundt, *Geometric Scaling of Cylindrical Rotating Detonation Rocket Engine Combustors*, PhD dissertation, University of Washington, 2023

### External

- [Strakey & Ferguson (NETL), Validation of a CFD Model of a Methane-Oxygen RDE, AIAA 2022-1113](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf)
- [ICNC 2025 abstract: grid optimization, AFRL CH₄/O₂ RDRE (University of Michigan)](https://coms.events/icnc2025/data/x_abstracts/x_abstract_253.pdf)
- [Sawada et al., Torque Around the Axial Direction on RDEs, JPP 2022](https://arc.aiaa.org/doi/10.2514/1.B38374); [JAXA repository](https://repository.exst.jaxa.jp/dspace/handle/a-is/1223675); [Nagoya repository](https://nagoya.repo.nii.ac.jp/records/2003923)
- [Sawada et al., The circumferential force on a cylindrical RDE, PCI 2024](https://www.sciencedirect.com/science/article/pii/S1540748924002980); [Keio record](https://keio.elsevierpure.com/en/publications/the-circumferential-force-on-a-cylindrical-rotating-detonation-en/)
- [Space flight demonstration of an RDE (S-520-31)](https://arc.aiaa.org/doi/full/10.2514/1.A35401)
- [Quasi-2D detonations with friction and heat loss in thin channels, Combustion and Flame 2025](https://www.sciencedirect.com/science/article/abs/pii/S0010218025007953)
- [NASA: Examination of wave speed in RDEs](https://ntrs.nasa.gov/api/citations/20180004332/downloads/20180004332.pdf)
- [Reduced-order wall heat flux in rotating detonation rocket combustors (Aerospace 2026)](https://doi.org/10.3390/aerospace13070637)
- [Caltech EDL: Analytical models for the thrust of an RDE](https://shepherd.caltech.edu/EDL/publications/reprints/rde_model_report.pdf)
- [Annual Review of Fluid Mechanics: Nonidealities in RDEs](https://www.annualreviews.org/content/journals/10.1146/annurev-fluid-120720-032612)
- [High-resolution 3D RDE with parallel AMR (slip adiabatic walls)](https://www.sciencedirect.com/science/article/pii/S2666352X24000712)
- [Wall effect on 3D rotating detonation flow structures](https://www.sciencedirect.com/science/article/abs/pii/S0360319920328068)
- [NREL PeleC RDE study (2022)](https://www.nrel.gov/docs/fy22osti/83466.pdf); [NREL slides](https://www.nrel.gov/docs/fy22osti/82891.pdf); [Valencia et al. 2024, PeleC RDE with discrete inlets](https://investigacion.pucp.edu.pe/grupos/fpce/publicacion/flow-field-analysis-and-performance-assessment-of-rotating-detonation-engines-under-different-number-of-discrete-inlet-nozzles/)
- [AMReX-based compressible reacting flow solver (arXiv 2412.00900)](https://arxiv.org/html/2412.00900v2)
- [University of Michigan GPU RDE simulations on Summit](https://beyster.engin.umich.edu/profile/2020-fellow-3/)
- [Ansys Fluent 2024 R2 (GPU compressible)](https://www.ansys.com/en-gb/blog/whats-new-ansys-fluent-software-2024-r2); [Fluent product updates](https://www.ansys.com/en-gb/products/fluids/ansys-fluent/product-updates)
- [Convergent Science: Advancing RDEs using CFD](https://convergecfd.com/event/advancing-rotating-detonation-engines-using-cfd)
- [Li, Mi & Higgins, yielding confinement (arXiv 1405.7753)](https://arxiv.org/abs/1405.7753), cited in the repo's C3 review
