# Handoff after the foundation coding session

Snapshot: **October 21, 2026**, in `/Users/sgfx/Desktop/Projects/prox_rde_sim`.

## 1. Start here

**Authoritative plan: [first_sim_plan.md](first_sim_plan.md), revision 6.** Its §0
short-test policy and §4.5 file separation still apply. The user approved only the
foundation and initial small tests for this first coding session. That increment
is complete; the 2D run is deliberately left for the next increment.

**Next concrete step:** finish the remaining D0 run orchestration and diagnostics
before launching a short Run 937 case. Implement valid short-window averaging,
early/failure-safe incremental output, immutable run inputs, actual numerical
flux budgets, and checkpoint/restart support. Keep source-accuracy work explicit.
Do not begin by rebuilding the environment or repeating the full paper review.

Current verification and artifacts: [foundation record](docs/verification/foundation_session.md).
The [previous planning handoff](docs/archive/HANDOFF_planning_20261021.md) retains
the detailed scientific audit, inherited failure history and prior source-line
references. Those line numbers and its environment/status statements are historical.
The original Python files, config and status are preserved in
[the pre-session source archive](docs/archive/starter_pre_foundation.zip).

## 2. Completed in this increment

- Created workspace-local `.venv` and a pinned `requirements.txt`. Verified imports
  and `pip check`. Used prebuilt packages; no OpenFOAM, Cantera or mesher installed.
- Extracted `physics.py`: EOS/chemical energy, one-step source, inherited injector
  law, conservative-state validation and interior-only primitive conversion.
- Kept the original HLL flux, minmod reconstruction, SSP-RK2 and one-step chemistry.
  Reused the physical energy function in both conversion and numerical fluxes.
- Fixed the zero-density ghost conversion. Primitive boundary fill initializes
  ghosts, including the single-row tube-test case. Fixed left transmissive
  extension and reject unpaired periodic x boundaries rather than silently
  ignoring the right setting.
- Added `InvalidStateError` with stage, cell, component and value; `last_failure`
  and `invalid_state_count` record failures. Zero/negative/nonfinite density,
  nonfinite conserved variables, invalid pressure and progress outside [0,1]
  are rejected before subsequent flux evaluation. Failed initialization or RK
  stages leave the last accepted conserved state and time intact.
- Removed silent state floors/clipping. `rho_min`/`p_min` are rejection thresholds;
  set them explicitly for nondimensional tests. The legacy `floor_hits` counter
  remains zero for compatibility. There are no repair mass/energy budgets because
  this implementation performs no state repair.
- Added optional `Solver.step(dt_max=...)` for bounded test steps. **This is not
  general reactive-source time-step control**, and the legacy 2D runner does not
  yet pass its remaining run time to it.
- Made every starter module safe to import. Calibration is a pure function with
  explicit-output CLI; plotting lives in `plot.py` and imports Matplotlib only
  inside rendering functions. `run.py` has a main guard.
- Moved the useful tube checks into assertion-based `tests/test_solver.py`.
  `test_1d.py` is a compatibility runner for that same file.
- Added pure numerical analysis helpers for weighted means, window overlap,
  planar exit contribution and directional FFT reduction. The old unsupported
  automatic mode/roll-stability report is retired, not presented as repaired.
  Full front tracking, native force budgets and run reporting are still future work.
- Preserved supplied `calib.json`, `test_1d.json`, all three supplied PNGs and
  `config.yaml` byte-for-byte. Added ignores for `.venv`, caches and generated runs.

## 3. Verification and how to run it

From the repository root, with the existing environment:

```sh
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

**21 tests passed; one explicitly skipped opt-in reactive baseline.** Checks cover
chemical-energy consistency, the exact constant-rate closed-reactor solution,
injector blocked/choked/unchoked limits, calibration regression, import side
effects, ghost boundaries, invalid-state rejection, atomic failed steps,
uniform HLL fluxes, periodic conservation, nondimensional Sod, weighted windows,
known-flow exit force, and signed frequency/mode indices on an analytic signal.

The 95 microsecond inherited 1D detonation test is available with
`RDE_RUN_REACTIVE_BASELINE=1` added to the test command, but **was not run**.
Its old saved +0.8% CJ-speed result remains inherited evidence. A strict-state
failure is possible now that clipping cannot hide it; diagnose that failure
before changing model parameters or enabling repairs.

No 2D engine run, long convergence study, physical CJ/ZND calculation, new
chemistry model, wall-friction closure, backend installation or CAD work occurred.

New Sod/calibration artifacts are in `rde_sim_starter/runs/foundation_session/`.
These generated files are ignored; the small durable verification record is in
`docs/verification/`. The test suite itself never overwrites supplied baselines.

## 4. Environment

- Python **3.12.0**, macOS **x86_64**; interpreter: `.venv/bin/python`.
- NumPy **2.3.5**, SciPy **1.18.1**, Numba **0.62.1**, llvmlite **0.45.1**,
  Matplotlib **3.11.2**, PyYAML **6.0.3**. Full resolved versions in `requirements.txt`.
- A new environment can be installed using
  `.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt` after
  `python3 -m venv .venv`. The binary-only policy avoided an automatic source build
  of a newer Numba without a matching Intel macOS wheel.
- Initial Numba compilation costs more than subsequent checks. Two threads were
  used for the small tests; no 2D throughput claim follows from their run time.
- This chat's sandbox initially retained the old writable workspace path, despite
  the folder change. Environment installation and final project writes used the
  normal approval mechanism. Temporary staging was used for edits/tests; the
  actual repository is the path at the top of this file.

## 5. Remaining issues before the first 2D run

1. **Runner limits/output:** `run.py` still has legacy defaults and only saves at
   completion. Implement the planned case/run-directory CLI and finite remaining-
   time cap, save initial/early fields, retain partial results on failure, and
   resume from checkpoints to a total cap. The new per-step cap is only a primitive.
2. **Averaging:** inherited config begins at 0.4 ms, later than both short caps.
   The legacy runner can still write a fake zero mean for an empty window. Wire
   validated window handling into run output/analysis; absent means stay absent.
   The pure window helper alone does not fix the runner.
3. **Source accuracy:** time steps still use flow CFL unless explicitly capped.
   Add targeted source-integration accuracy/robustness work. Two-step induction is
   only a candidate; verify partially advanced material and event crossing first.
   No chemistry retuning with grid size. Reproduce the opt-in 1D baseline as useful.
4. **Native budgets:** the runner still duplicates the injector formula and uses
   cell-centre exit values. Log actual RK-weighted boundary fluxes/source integrals
   with mass, energy, axial and angular momentum storage. A pure force helper or
   periodic closed-domain check does not implement these open-domain budgets.
5. **Feed/outlet:** define imposed versus plenum-driven flow and the two-feed to
   premixed reduction. Preserve both measured feed states. The original subsonic
   pressure outlet remains; assess normal/axial Mach and boundary behavior, not
   total-speed Mach. Do not blindly apply the old zero-gradient recommendation.
6. **Initialization:** make ignition masks wrap periodically, document deposited
   energy and distinguish selected initial wave count from predicted behavior.
7. **Analysis/visibility:** implement pressure/reaction fields, front tracks,
   observed passages, pressure stations and partial/failed/inconclusive outcomes.
   The isolated FFT helper is not a validated classifier. New `plot.py` currently
   supports calibration and a supplied Sod field only; run-directory plots are pending.
8. **Model-dependent loads:** compute annulus-exit contribution with clear scope.
   Do not infer engine torque from transient exit angular flux alone. Wall-friction
   torque and independent measured-force validation remain later work.

## 6. Decisions to preserve

- Reuse this small prototype; do not build a general CFD framework overnight.
- Start with **76-FI-5 / Run 937**, straight constant-gap circumferential–axial 2D,
  simplified premixed injection. Physical case/reference inputs are in master §2.1.
- Default 2D cap: **three expected passage intervals = 189.394 microseconds** at
  15.84 kHz, from simulation start. Extend the same saved run only if useful to
  **five intervals total = 315.657 microseconds**. Record actual observed passages
  separately; never wait indefinitely for an extinguished wave. Startup counts.
- Do not restore the obsolete 500–700 ns cap or the 3 ms/10 ms campaigns.
  The short record cannot establish converged means or long-term wave stability.
- Human wave inspection comes first; a pressure pulse alone is insufficient.
  Show pressure and reaction together. Failure and inconclusive outcomes are useful.
- Keep physical thermochemistry separate from the fitted constant-gamma surrogate;
  its total energy already stores unspent chemical energy. Do not add heat twice.
- Do not inherit revision 3's incorrect 0.75 mm reaction-zone claim. Its proposed
  two-step model had approximately 1.65/2.28 mm shock-to-90/95% lengths in the audit.
- The 2D gap depth preserves area, not radial dynamics. At fixed mean radius and
  local feed with wall closures off, varying depth only scales integral quantities.
  Wide-gap/coreless/CAD predictions require later geometry-resolving work.
- Mundt's wave speed uses outer radius. Keep mean-radius speed separate. Mundt
  supplies no measured thrust/torque target; external force cases must be matched
  independently. Roll response also needs inertia; it is not a stability verdict.
- Full figure campaigns, 51/25 mm cases, detailed spectra, force-validation
  campaigns, CAD, a replacement backend, and 3D remain deferred. The figure roadmap
  is a backlog; only the Run 937 subset is immediate.

## 7. Repository and document handling

The master plan remains revision 6, with only its status updated. The review and
historical revisions are unchanged. The review is intentionally Git-ignored.
The previous planning handoff and source snapshot are archived as historical
reference, not competing instructions.

Publication update: the user requested committing and pushing this foundation
iteration to GitHub (`origin/main`, repository `szaozerska/prox_rde_sim`). Include
the source, tests, plans, reference dissertation and inherited baselines. Keep the
local review, virtual environment, caches and generated run data excluded. No
reset, clean or checkout is needed. Previously untracked project files are part
of this initial project snapshot; do not treat them as disposable.
