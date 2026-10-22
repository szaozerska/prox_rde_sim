> Historical planning snapshot. Follow [the current handoff](../../HANDOFF.md) for implementation status.

# Handoff for the next coding session

Snapshot: **October 21, 2026, approximately 20:48 PDT**, in `/Users/sgfx/Desktop/Projects/prox_rde_sim`.

## 1. Start here

**Authoritative plan: [first_sim_plan.md](../../first_sim_plan.md), revision 6.** Read **§0 (deadline scope)** and **§4.5 (file separation)** first, then the relevant physics/verification sections. The user needs the smallest useful deliverable tonight/tomorrow morning: at this snapshot, October 21–22, 2026, Pacific time. Recheck remaining time in a fresh session.

This session was **planning/documentation only**. No simulation source or configuration was changed, no dependency was installed, and no new CFD result was generated. The last request was to write this handoff. It does not itself start implementation; proceed with the concrete steps below when the next session is instructed to code. Do not repeat the full research/planning exercise.

**Next concrete coding step:** establish the local Python environment, then make the existing starter safe to import and suitable for a short run: separate tests/rendering, correct the invalid ghost-state conversion, add explicit state validity checks, and fix time limits/averaging/output. Establish short numerical baselines before changing the reaction model. See §9 for the complete immediate sequence.

### Document precedence and stale material

| Document | Status / how to use it |
|---|---|
| [first_sim_plan.md](../../first_sim_plan.md), revision 6 | **Current instructions.** Its short-test/deadline override takes precedence over the longer project milestones. |
| [Figure validation roadmap](../../docs/plans/figure_validation_roadmap.md) | Current companion, also updated for revision 6. All 66 Chapter 3–4 figures reviewed. Only the Run 937 reference subset and basic G1 diagnostics are immediate; the complete catalogue is a backlog. |
| [sim_plan_review.md](../../sim_plan_review.md) | Local, Git-ignored review of revision 3. Useful detailed scientific/code findings. Its old milestone sequence is superseded; some source line numbers are approximate. This file is intentionally absent from normal commits. |
| [Revision 4](../../docs/plans/first_sim_plan_rev4.md) | Historical archive; only link paths adjusted on archival. Earlier duration/scope requirements do not override revision 6. |
| [Revision 3](../../docs/plans/first_sim_plan_rev3.md) | Historical, preserved unchanged; contains incorrect physics claims and obsolete gates. Its detailed formulas/defaults are **not** automatically approved implementation specifications. |
| [Starter STATUS.md](../../rde_sim_starter/STATUS.md) | Supplied pre-revision-3 status, not a current validation report. “Works/passes” means reported by the previous prototype author. Its instruction to replace the outlet with zero-gradient is not the current blanket policy. |
| Starter Python comments / `Dxx` references / `config.yaml` | Refer to old plans and contain obsolete behavior. Current plan uses a different organization. |
| [Mundt2023.pdf](../../Mundt2023.pdf) | Experimental source. Printed page + 16 = PDF page. |

The actual plan filename is `first_sim_plan.md`, not the initially mentioned `first_plan_sim.md`. Revisions 5 and 6 were edits to this same file; there is no separate revision-5 archive.

## 2. User decisions that must persist

- Reuse the small starter; do not rewrite the same 2D solver from scratch or build a general CFD framework overnight.
- Immediate case: **76-FI-5 / Run 937**. First model is a straight, constant-gap, radially averaged circumferential–axial domain with simplified premixed injection.
- Wave assessment is primarily human inspection. Prioritize pressure/reaction fields, front tracks, short space–time plot, pressure stations, and conservation/force diagnostics.
- **Short test policy:** default **three expected wave-passage intervals**, from simulation start. Extend the same saved run to **five intervals total only if needed**. At 15.84 kHz these limits are **189.394 µs** and **315.657 µs** (0.189394 / 0.315657 ms).
- The user's earlier “500–700 ns” cap was explicitly replaced by “a few wave passages.” Do not retain a literal nanosecond cap, use 500–700 µs by assumption, or launch the older 3 ms/10 ms campaigns.
- Set a finite time cap using reference frequency for budgeting only. Record actual observed passages separately. Do not wait indefinitely for passages if the wave fails. A passage is a probe crossing, not a full revolution of each wave.
- Include startup inside that cap. If too little clean data remains, report **inconclusive over this short window**. Do not extend automatically to obtain a desired answer.
- Save time by reducing scope, case count and unnecessary output, not by increasing CFL beyond accuracy requirements, changing chemistry to fit the grid, or suppressing failure reporting.
- **Separate physics, tests, analysis, and plotting files**; one simple run → saved results → plots workflow. No workflow engine, service, plugin registry or separate scripts per figure/engine.
- All 51 mm/25 mm sweeps, full operating maps, detailed spectra, measured-thrust campaigns, CAD, external backend installation and 3D are deferred beyond the immediate deadline.
- Communicate concrete progress regularly. The user asked for clear explanations of what is being checked, and is sensitive to unnecessary delays or confirmation requests.

Short-run pressure/thrust/torque are **transient estimates**. A few crossings cannot establish converged mean loads, long-term stability, or predictive agreement with the experiment.

## 3. Progress completed

- Read the substantive thesis chapters and relevant appendices; inspected the starter's five Python files, config, saved calibration/test JSON and images.
- Audited the old plan's chemistry, boundaries, force/torque definitions, data use, and implementation ordering.
- Created the detailed review, initially in `/private/tmp/prox_rde_review_20261021/review.md`, then moved it to root `sim_plan_review.md` at the user's request. Added a dedicated `.gitignore` entry to keep that review out of Git.
- Preserved revisions 3 and 4; updated the master plan through revision 6 and README navigation.
- Inspected detonationFoam's README, executable, build files and a tutorial. Planned an external executable/case adapter; did **not** download/build/run it.
- Reviewed **all 35 Chapter 3 figures, Table 3-3, and all 31 Chapter 4 figures**, including their surrounding text and rendered pages. Added reusable calling/analysis/plotting order and a per-figure disposition.
- Resolved the Fig. 3.35 high-flow discrepancy using the original conference paper: use **160 kg/(s m²)** from the figure and AIAA 2023-1104, rather than 180 in the dissertation prose.
- Replaced longer default tests with the three-to-five-interval policy and a deadline-specific D0–D3 sequence.
- This handoff also identifies the short-run averaging bug in §6. It has not been fixed.

### Starter inventory

| File | Existing implementation |
|---|---|
| `solver.py` | Five conserved variables; one-step Arrhenius reactive Euler; uniform-grid finite volume, MUSCL/minmod, HLL, SSP-RK2; Numba; simplified injector/outlet. |
| `calibrate.py` | Constant-gamma surrogate CJ/ZND calibration; reads config and writes JSON/PNG at top level. |
| `test_1d.py` | Top-level Sod and 95 µs detonation examples; prints results and overwrites saved JSON/PNG; no assertions. |
| `run.py` | Top-level one-case CLI; all histories/snapshots held in memory; output written at end; no restart. |
| `analyze.py` | Top-level numerical reductions, classification, Markdown/JSON report, and plotting combined. |
| `config.yaml` | Old single-file inputs; 0.5 mm grid, 1 ms duration, pressure averaging starts at 0.4 ms. |

**Not implemented:** `physics.py`, `plot.py`, `tests/`, new case CLI, `--test-passages`, restart/checkpoint support, two-step chemistry, wall-friction/heat-loss models, native flux-budget logging, new graph suite, CAD or 3D.

## 4. Decisions and physics reasons

### Model and chemistry

- Keep physical thermochemical references separate from the fitted constant-gamma surrogate. A CJ-speed fit does not validate product thermodynamics, reaction structure, injection or thrust.
- Two-step induction/reaction chemistry is a **candidate repair**, not a proven fix. Verify source timing and partially advanced induction before relying on it.
- Revision 3's proposed `Delta_I = Delta_R = 0.25 mm` does **not** make a 0.75 mm full reaction zone. Scratch integration of its own ZND model gives shock-to-50/90/95/99% distances of approximately **0.518 / 1.652 / 2.275 / 3.882 mm**.
- Freeze physical model parameters during mesh/time-step checks. Rate/length changes are separate model-sensitivity studies.
- The starter stores unused chemical energy in total energy. Do not add released heat a second time to the energy equation.
- A transported induction state mixed to 0.5 is already partially advanced. The old example's remaining delay was about 51 µs, not 103 µs. Also, clipping induction at 1 within an RK stage then averaging can leave the final state below a strict reaction threshold. Design/test this event handling.

### Boundary conditions and loads

- Zero-gradient outlet does not impose choking. Inspect **axial/normal Mach**, not total speed including swirl; use appropriate subsonic pressure coupling and later outlet sensitivity checks.
- Specify whether mass flow is imposed or predicted from plenum conditions. A discharge coefficient fitted to target flow makes that flow a calibration quantity.
- `integral[rho*u_z² + p - p_ambient] dA` at the planar exit is an **annulus-exit contribution/estimate**, not automatically whole-engine thrust.
- Use actual RK-weighted numerical boundary fluxes and source integrals for discrete conservation; retain mass, energy, axial momentum and angular momentum storage.
- Local rotating gas/waves do not alone imply engine torque. The smooth axisymmetric Euler model has no wall shear or azimuthal pressure traction; do not label transient exported angular momentum as steady engine torque.
- A modeled wall-friction source can support an explicitly qualified torque estimate; full geometry permits pressure torque on nonaxisymmetric features. With consistent signs, engine reaction torque includes inlet/outlet angular flux and gas storage.
- “Roll stability” is outside the computed torque alone. Roll acceleration needs inertia; structural survival needs a separate thermal/structural model.

### Gap, later backend and CAD

- `W = 2*pi*r_mean` and `A_exit = W*gap` preserve annular area, not radial dynamics.
- At fixed mean radius/local feed conditions with wall closures off, changing uniform gap depth leaves reduced local fields unchanged while integrated flow/force scale with depth. This limiting invariance must not be presented as realistic gap prediction.
- Mundt's radius study kept absolute gap **5 mm** while relative gap/curvature changed. The gap study reused the 25 mm injector, changing area ratio and relative jet placement; the 3 mm core has a relevant chamfer.
- Coreless, cross-gap mixing, radial wave structure and variable gaps require appropriate later geometry/3D work. A wrapped 2D image is not 3D CFD.
- detonationFoam is a compiled OpenFOAM backend, not a drop-in Python chemistry library. Inspected branch `detonationFoam_V2.0_OF8` targets OpenFOAM 8. Preserve physical case definitions, geometry metadata, observables and plotting; implement native case/mesh/IO/reduction adapters later. Build compatibility remains unverified.
- CAD import is explicitly “TO BE IMPLEMENTED after the first working iteration”; independent importer work can proceed in parallel. Agree units, transforms, fluid volume and stable boundary roles without coupling the importer to solver arrays/dictionaries.

## 5. Failed approaches and rejected claims

These are **inherited observations or audit findings**, not newly rerun experiments:

| Approach | Reported outcome / reason not to repeat blindly |
|---|---|
| One-step chemistry with `Ea/(R*T1) = 20` | Starter 2D wave reportedly dies near **90 µs**, with premature burning near the injector. Numerical mixing is plausible; the saved evidence does not uniquely isolate the cause from boundaries/ignition/reaction thickness. |
| Halving reaction length to rescue that case | Old plan reports no rescue; arbitrary shortening is not verification. |
| Raising activation parameter to 50–70 | Old plan reports underdriven/failed 1D initiation at 0.25 mm, around 1,400–1,500 m/s instead of 2,471. |
| 5 mm ignition patch at CJ pressure | Reported shock/reaction decoupling and decay to about 870 m/s. A 10 mm patch at 2×CJ pressure worked in the saved 1D example; this does not guarantee a correct 2D selected mode. |
| Applying a 1 Pa pressure floor to nondimensional Sod | Would clip the 0.1 initial state. Existing script explicitly lowers the floor. |
| Changing kinetics with grid size | Invalidates a numerical-convergence comparison. |
| Strongest FFT peak = wave count; 58% pressure-spectrum threshold = paper camera classification | Harmonics and measurement mismatch; prefer front tracking for the short test. |
| Forcing Sawada's 8.8% shear/thrust ratio or Mundt's approximately 9% power scaling | Neither is a universal calibration or target-engine torque measurement. |
| Shortening only the CLI duration | Fails to adjust the pressure averaging window; see §6. |

## 6. Known code errors and immediate traps

Line numbers below refer to the unchanged starter at this handoff; recheck after edits.

1. **Required dependency absent:** `solver.py:10` imports Numba; it is not installed in the inspected interpreter.
2. **Invalid ghost conversion:** `solver.py:25–35` divides by density over all storage, including zero-initialized ghosts, before boundary values are filled. Convert only valid cells or initialize safely.
3. **State repair is unsafe/incomplete:** `solver.py:188–204` can divide by an old zero/negative density, clips progress without accounting, changes energy through floors, and does not explicitly reject NaN/Inf. Record repair counts/budgets; do not hide invalid states.
4. **Time step:** `solver.py:236–248` uses flow CFL alone and can overshoot the requested end time. Add a bounded remaining-time step and adequate source timing/accuracy handling; preserve source physics.
5. **Boundary consistency:** when the left x-boundary is periodic, both sides are made periodic regardless of the right setting. Left transmissive ghost copying differs from constant extension. Keep the actually used symmetric-periodic case correct and test supported combinations.
6. **Short-run averaging bug:** `config.yaml` starts pressure averaging at **0.4 ms**, later than both **0.189/0.316 ms** caps. `run.py:107–121` then writes a zero profile by dividing zero accumulation by `max(weight,1e-30)`. Analysis may silently use a different window. Define a valid recorded short window or mark it unavailable; never report fabricated zero means.
7. **Late snapshots/progress and no restart:** `run.py:83` starts snapshots halfway through short runs; the reported 90 µs failure can precede the first 189 µs-run snapshot. It reports progress only every 500 steps, buffers output, and saves only at completion. Capture initial/early fields, retain partial results on failure, and support a genuine extension to five intervals rather than restarting.
8. **Incorrect conservation diagnostic path:** `run.py:62–72, 92–100` duplicates injection formulas and uses cell-centre exit values instead of the actual stage-integrated numerical boundary fluxes. Compute authoritative discrete budgets from fluxes that updated the state.
9. **Wrong Mach for choking:** `run.py:101–102` reports total-speed Mach. Add axial/normal Mach.
10. **Torque/storage error:** `analyze.py:119–124` takes engine torque as negative exit angular flux without gas storage or modeled wall traction; its swirl “power” is `mdot*D*u`, not azimuthal kinetic-energy flux.
11. **Speed convention mismatch:** although both speeds are computed, the comparison at `analyze.py:168` uses mean-radius `D/D_CJ` against the paper's outer-radius ratio.
12. **Short-record analysis assumptions:** spectral/subwindow code assumes enough samples, nonzero peaks and usable arrays; report code formats potentially absent fill-height metrics as floats. Empty/failed/inconclusive runs need explicit handling.
13. **“Camera” data are average temperature**, `run.py:106`, not luminosity or heat release. Label any replacement synthetic; do not claim measured brightness replication.
14. **Mutable inputs/import side effects:** scripts execute on import and read shared config/calibration after the fact. Save immutable inputs with each run; add main guards.
15. **Ignition is not periodic:** patches/products-behind masks are truncated at the seam; wrap consistently.
16. **Performance/output:** faces are computed twice and full fields are collected in memory. Fix redundant work where useful, but do not undertake a broad optimization project before the numerical checks work.

## 7. Environment and setup

Observed here, not inferred from generic laptop estimates:

| Item | Result |
|---|---|
| OS / architecture | macOS 15.7.9, **x86_64** |
| Shell / cwd | zsh; `/Users/sgfx/Desktop/Projects/prox_rde_sim` |
| Python | `/usr/local/bin/python3`, **3.12.0**; `python` is not on PATH |
| Present package metadata | NumPy 1.26.3; SciPy 1.12.0; Matplotlib 3.8.2; PyYAML 6.0.1 |
| Missing | **Numba**, **Cantera** |
| PDF tools | pypdf 6.16.1, Pillow 10.2.0, `/usr/local/bin/gs`; no `pdftoppm` or `pdfinfo` on PATH |
| Other tools | `uv` at `/Users/sgfx/.local/bin/uv`; git and ffmpeg present; `wmake`/`foamVersion` not on PATH |
| Project setup | No `.venv`, dependency manifest/lockfile, or local AGENTS.md found in this review |

Dependency presence was checked with `find_spec` and package metadata; this is not an import/runtime compatibility test of the numerical stack.

The sandbox permits workspace and temporary-directory writes; network is restricted and `.git` writes may require approval. If an installation fails because of network/sandbox policy, use the available escalation flow rather than attempting a workaround. No setup escalation or package installation was attempted here.

### Proposed setup commands — not yet run

Use a workspace-local environment once implementation is authorized. A minimal starting sequence is:

```sh
cd /Users/sgfx/Desktop/Projects/prox_rde_sim
python3 -m venv .venv
.venv/bin/python -m pip install numpy scipy matplotlib PyYAML numba
.venv/bin/python -c "import numpy, scipy, matplotlib, yaml, numba; print('Numerical imports OK')"
```

Dependency resolution/version compatibility has not been verified; record the versions that actually work in a small manifest. Do not add Cantera, OpenFOAM or a mesher merely to implement this short surrogate check; install them when their particular reference/backend work is needed. Add local environment/cache/generated-run exclusions before commits; the present `.gitignore` only excludes the local review.

### Existing and planned CLIs

The existing CLI accepts `--dx`, `--cd`, `--waves`, `--tend` **in ms**, `--out` and `--calib`. Its `--out` is a basename resolved relative to the script, not the planned run-directory interface. Defaults run **1 ms**, beyond the new budget. Do not blindly run them or overwrite supplied baselines.

The following are **planned commands, currently unsupported**, to implement:

```sh
cd /Users/sgfx/Desktop/Projects/prox_rde_sim/rde_sim_starter
../.venv/bin/python -m unittest discover -s tests
../.venv/bin/python run.py --case config.yaml --test-passages 3 --out runs/run937_short
../.venv/bin/python plot.py runs/run937_short
```

The optional five-interval extension must resume saved state to the total cap, not start a second full run. Keep syntax simple; implement one convention and document it.

### Reusing the paper work

`/private/tmp/prox_rde_review_20261021/` contains full/per-page extracted text and rendered figures. It is temporary and may disappear; the PDF and repository docs are sufficient durable sources.

- Text: `paper_pdf_###.txt` uses **PDF page numbering**; `paper_full.txt` contains the extraction.
- Older images: `paper_p55.png`, etc., use printed page numbering.
- Latest figure audit: `figure_audit/page_001.png` = printed p. 46; `page_026.png` = printed p. 71. Contact sheets are named `pages_46_49.jpg`, etc.
- Ghostscript rendering was successfully used without installing Poppler. Example **command already used** from the repo root:

```sh
mkdir -p /private/tmp/prox_rde_review_20261021/figure_audit
gs -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=png16m -r110 \
  -dFirstPage=62 -dLastPage=119 \
  -sOutputFile=/private/tmp/prox_rde_review_20261021/figure_audit/page_%03d.png \
  Mundt2023.pdf
```

## 8. Verification actually performed

### This planning/documentation session

**No CFD simulation, automated numerical test suite, detailed-chemistry calculation, OpenFOAM build, or new performance benchmark was run.** Do not claim the solver was validated in this session.

Completed checks:

- Static source review of all five Python files and their input/output behavior.
- Independent scratch calculations of reaction-zone distances, induction timing, annular areas, reference quantities and short-test limits. These are arithmetic/model checks, not simulation results.
- PDF extraction/rendering and visual inspection of the relevant figures/pages.
- Programmatic figure-register check: all **35 + 31** figure entries present exactly once, with each recorded printed page matching its extracted caption — passed.
- Documentation link/whitespace checks on the current plan, roadmap, README and review — passed.
- `git diff --check` — passed; it only covers tracked diffs, so explicit document checks also covered untracked files.
- `git check-ignore -v sim_plan_review.md` — dedicated root `.gitignore` entry confirmed.
- Revision 3 hash preserved; revision 4 content preserved except the two archive link paths.
- Interpreter/dependency/tool discovery repeated for this handoff; results in §7. No numerical package installation attempted.

### Inherited baseline evidence, not rerun

The supplied [test_1d.json](../../rde_sim_starter/test_1d.json) reports:

| Quantity | Saved result |
|---|---|
| Sod star pressure / velocity | 0.3031368282 / 0.9274698472 |
| Sod shock coordinate | 0.85125 |
| 1D detonation speed | 2490.139 m/s against CJ 2471 m/s |
| Speed error | +0.774545% |
| Mean recorded peak / VN reference | 20.4266 / 21.5251 MPa |
| Stored run time | 1.5871 s on the previous environment; **not this machine's benchmark** |

The script has no pass/fail assertions. It runs a nondimensional Sod case to `t = 0.2` (not a dimensional 0.2 s engine test) and a 1D detonation to 95 µs. The supplied status reports the **2D wave dies around 90 µs**. None of this proves current two-step chemistry, a sustained 2D RDE or trustworthy thrust/torque.

Saved `calib.json` is a **one-step surrogate**: gamma 1.2384499, R 318.6733 J/(kg K), q 5.5 MJ/kg, initial p 377,916.97 Pa, initial T 300 K, VN shock-frame speed 306.033 m/s. Do not confuse the fitted initial pressure with measured front-wall pressure or the plenum pressure.

## 9. Immediate unfinished work and next sequence

1. **D0: environment and minimal safe structure.** Check for user changes, create the local environment, verify Numba import, add a minimal dependency record. Keep the starter directory. Extract `physics.py`, move rendering into `plot.py`, leave reductions in `analyze.py`, and add small `unittest` files under `tests/`. Main guards are required; avoid a wholesale architecture rewrite.
2. **Fix actual blockers before a short run:** invalid ghost conversion, nonfinite/repair reporting, short-window averaging, exact bounded end time, early/failure-safe output, and immutable inputs. Preserve the old saved JSON/PNGs as inherited baselines.
3. **Add meaningful quick assertions:** energy/primitive consistency, source timing, injector limiting states, a short known shock case, and force/flux signs including storage. Tests must call production functions; keep 2D integration outside the fast default suite.
4. **Evaluate the candidate reaction repair in a small 1D/source case.** Preserve conservative chemical energy, distinguish reference/surrogate parameters, and check induction-event handling. Do not guess that two-step gating or rate shortening fixes the 2D failure. Record changes and resulting evidence.
5. **D1: one capped 76-FI-5 run**, default 189.394 µs. Save fields/probes early enough to observe the inherited near-90-µs failure. Stop on clear numerical failure. Extend from a checkpoint to 315.657 µs total only if it answers a specific unresolved question.
6. **D2: analyze and plot the same saved run.** Pressure/reaction fields, space–time/front paths, actual observed passages, station traces/profile, finite-window budgets, and qualified force/torque diagnostics. Mark absent/insufficient data explicitly. Plot changes never rerun CFD.
7. **D3: focused check and report.** Rerun only affected tests after fixes; at most a targeted short time-step/grid comparison if a material concern remains. Deliver a runnable workflow and candid results, including failure if the wave does not survive. Do not hide failure by extending, tuning to the desired mode, or rebranding startup values as validated performance.

The required simple split is:

```text
rde_sim_starter/
  physics.py       # EOS / chemistry / physical source laws
  solver.py        # Fluxes / reconstruction / integration / BC application
  calibrate.py     # Reference calculations, no rendering
  run.py           # Inputs / execution / saved results
  analyze.py       # Numerical reductions, no rendering
  plot.py          # Figures from saved data, no solver execution
  config.yaml
  tests/
    test_physics.py
    test_solver.py
    test_analysis.py
  runs/<run_id>/
```

## 10. Durable reference points and deferred work

Run 937 inputs/targets are fully tabulated in the master plan §2.1. Key values: radii 38.1/33.1 mm, length 76.2 mm; flow 268.65 g/s; mass flux 240.21 kg/(s m²); phi 1.176; back pressure 100.2 kPa; measured N=2, f=15.84 kHz, outer-periphery speed 1893 m/s. Do not force the measured wave count into the simulated answer.

First plot comparisons: Table 3-2 / Fig. 3.2 axial pressures, Fig. 3.5 space–time structure. Figs. 3.8–3.10 are **plenum PCB** signals, so chamber signals are only analogous; full spectral amplitudes need richer models. A short test's profile is not equivalent to the paper's last-100-ms mean.

Later ordering remains: 76 mm mass-flux then phi sweeps → 51 mm anchors/sweeps → qualified 25 mm subset → back-pressure profiles → 51 mm map → supported gap/coreless cases → derived Chapter 4 plots/holdouts. Plot functions and canonical condition IDs are reused across figures.

Chapter 4 CJ, heat-release and cell-size curves are **reference calculations**; formula-derived fill height and energy flux are not independent CFD measurements. The full roadmap explains circularity and per-figure limitations. No complete digitized dataset has been created.

Mundt has **no measured thrust or torque** for validation. Later thrust benchmark: Bennewitz et al., Scientific Reports 13, 14204 (2023), DOI `10.1038/s41598-023-40156-y`; independently match its facility, geometry and operating point rather than pairing its forces with Run 937. A possible torque benchmark is Sawada et al., DOI `10.2514/1.B38374`; full case matching is unfinished.

Earlier 51 mm map estimates (days/weeks and 3 ms/10 ms campaign costs) are explicitly deferred, not tonight's schedule or verified runtime forecasts. Actual code still needs its first local numerical run.

## 11. Git/workspace caution

At handoff preparation, **only README.md is tracked**. It is modified; the PDF, current plan, archives/roadmap, `.gitignore`, and the entire starter are untracked. `sim_plan_review.md` is ignored. This explains why ordinary `git diff` does not expose most workspace content.

No commit, push, checkout, reset, clean, or other Git write operation was performed. Preserve existing files; do not use `git clean` on this workspace or assume untracked means disposable. No automatic commit/push is requested. `HANDOFF.md` is a normal repository document; the detailed local review must remain excluded unless the user changes that instruction.

Before finalizing implementation, inspect `git status` and generated-file exclusions so `.venv`, caches, bulk results and `.DS_Store` are not accidentally staged with source/docs.
