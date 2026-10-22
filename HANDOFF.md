# Handoff after D0 run plumbing

Snapshot: **October 21, 2026**, in `/Users/sgfx/Desktop/Projects/prox_rde_sim`.

## Start here

The authoritative plan remains [first_sim_plan.md](first_sim_plan.md), revision 6,
especially §0 and §4.5. The foundation was pushed as commit `6ae65ad` on
`origin/main`. The user then asked for the next implementation increment: bounded
runs, saved inputs/output, restart, averaging and native conservation accounting.
These are implemented and checked with small synthetic cases. No reactive Run 937
simulation has been launched in these increments.

**Next concrete step: source-accuracy and focused boundary checks, then D1.**
Assess reactive-source time integration with fixed chemistry and a small 1D
propagation check. Once those checks support it, run one Run 937 case for three
expected passage intervals and inspect pressure/reaction together. Implement the
minimal saved-field plotting needed for that inspection. Extend the same saved run
to five intervals only for a specific unresolved observation.

Do not rebuild the environment or repeat the full paper review. See the
[run-plumbing verification](docs/verification/d0_run_plumbing.md), the historical
[foundation record](docs/verification/foundation_session.md), and the
[README](README.md) for commands and output format. The detailed inherited audit
is in the [archived planning handoff](docs/archive/HANDOFF_planning_20261021.md);
its source lines and environment/status claims are historical.

## Implemented

The existing HLL/minmod/SSP-RK2 solver and inherited one-step surrogate remain.
The foundation extracted `physics.py`, fixed conservative ghost conversion and
single-row/transmissive boundary issues, made imports inert, and replaced silent
floors with explicit initialization/stage/final-state rejection. `calibrate.py`
contains pure surrogate calculations; `plot.py` handles rendering separately.
`test_1d.py` delegates to the common solver tests.

This increment adds:

- A schema-1 case with explicit constant-annulus, equivalent-premixed-feed,
  inviscid-wall and chemistry choices. Measured O2/CH4 feed states remain separate
  reference data; the inherited rounded equivalent feed and surrogate parameters
  are preserved. Supplied calibration is checked against the case, not refitted
  silently. Mass flow remains predicted by the plenum boundary.
- A guarded CLI with a three-interval new-run cap and a same-run extension to five
  total. Steps stop at output events and the remaining end time. Startup counts.
  The reference frequency does not impose or detect simulated wave passages.
- Periodic ignition masks with explicit patch count, widths and offset. Saved
  initialization energy change is signed relative to the specified fresh/product
  baseline; replacing chemical reservoirs can make it negative. It is not a
  universal positive heat-deposition model.
- Initial/early/final field snapshots, per-step station-pressure and axial-Mach
  diagnostics, explicit transient means with clipped window weights, and null
  means when no accepted step overlaps the selected window.
- Actual boundary-face fluxes from both RK stages, weighted consistently with the
  accepted update. Budgets include mass, both momenta, total energy, reacted mass
  and constant-mean-radius angular momentum, with storage. Reaction changes the
  progress reservoir only; it does not add chemical heat to total energy twice.
- Atomic checkpoints with float64 state, cumulative budgets, averaging accumulators
  and output schedule/history position. Input hashes, source/environment matching,
  state checks and a Unix process lock guard resume. Restart archives writes after
  the checkpoint before continuing its history prefix. Failed RK states are never
  saved as accepted states. Interruptions during bookkeeping fall back to the last
  complete checkpoint. Disk failure can prevent a fresh status file.
- Failure details and scoped exit-force diagnostics. Angular residual is a
  conservation check, not mechanical engine torque; detected passages remain null.

`config.yaml` has intentionally changed from the inherited 1 ms/0.4 ms timing.
Its original bytes remain in `docs/archive/starter_pre_foundation.zip`. Supplied
calibration JSON, tube JSON/PNGs, historical plans and local review remain unchanged.
The old baseline hash manifest describes the foundation snapshot, not today's config.

## Verification

From the repository root, with the installed environment:

```sh
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

The suite covers the original physics/Sod/analysis checks plus open-domain native
flux/source closure, rejected-step budget atomicity, depth scaling of integrals,
bounded output, CLI creation/resume, immutable inputs, weighted averages across
restart, bitwise equality with uninterrupted step replay, partial-output recovery,
failed atomic writes and exclusive writer locking. See the current verification
record for the final count and measured metrics.

The inherited **95 µs 1D detonation test remains opt-in and was not run**. Its
old saved +0.8% CJ-speed result is inherited evidence. Removing clipping may expose
failure; diagnose it before changing chemistry or enabling repair. Tiny disabled-
chemistry runner tests use an artificial frequency only to exercise I/O. They say
nothing about wave survival or experimental agreement.

Generated probes are in `rde_sim_starter/runs/d0_plumbing_probe/` (Git-ignored).
Durable metrics are in `docs/verification/`. Test cases never overwrite baselines.

## Remaining work and limits

1. **Reactive time integration:** flow CFL and an optional user step cap do not
   establish source accuracy. Check fixed-parameter source/propagation behavior,
   including partly reacted material. Two-step induction remains a candidate only;
   validate its timing/event crossing before adoption. Do not retune chemistry with grid size.
2. **Feed/outlet physics:** inherited subsonic pressure closure and no-backflow
   injector remain. Basic injector-limit/boundary tests and native conservation
   are implemented, but characteristic/outlet sensitivity and injector-plane
   momentum/enthalpy behavior still need assessment before physical claims.
3. **D1/D2 visibility:** render saved pressure/reaction fields, short space–time
   traces and fronts; count actual observed passages. No full mode classifier or
   fine-frequency spectrum is justified by the short window. The saved outputs
   support later analysis without rerunning the flow.
4. **Focused confirmation:** resolve numerical concerns with a small time-step or
   resolution comparison; short startup-contaminated means are not converged data.
5. **Loads and geometry:** no wall-friction/heat-loss model or full engine force
   balance exists. Exit numerical momentum/pressure contribution is scoped to the
   annulus exit. Angular storage/flux balance does not determine mechanical torque.
   Physical thermochemistry, external force validation, CAD/backend/3D and wider
   figure campaigns remain follow-on work.

## Decisions to preserve

- Run 937: 76-FI-5, straight constant gap in circumferential–axial 2D, simplified
  premixed injection. Three intervals at 15.84 kHz are **189.394 µs**; five total
  are **315.657 µs**. Stop on invalid state; do not wait indefinitely for a wave.
- Human inspection comes first. Failure or an inconclusive short window is useful;
  pressure pulses alone do not demonstrate a shock-coupled detonation.
- Keep physical thermochemistry separate from the fitted constant-gamma surrogate.
  Total energy already stores unspent chemical energy.
- Do not restore revision 3's 0.75 mm reaction-zone claim: audited candidate
  two-step shock-to-90/95% lengths were about 1.65/2.28 mm.
- Uniform depth scales integrals without adding radial dynamics. Gap/CAD claims
  need geometry-resolving work. Mean-radius angular momentum is an approximation.
- Mundt reports peripheral speed at the outer radius; keep mean-radius speed
  distinct. No measured Mundt thrust/torque target exists for validating those loads.
- Keep generated runs, `.venv`, caches and the local review out of Git. No destructive
  checkout/reset/clean is required. The user has authorized committing
  and pushing this D0 increment to `origin/main` alongside the foundation snapshot.

## Environment

Python **3.12.0**, macOS **x86_64**, `.venv/bin/python`; NumPy **2.3.5**, SciPy
**1.18.1**, Numba **0.62.1**, llvmlite **0.45.1**, Matplotlib **3.11.2**, PyYAML
**6.0.3**. `requirements.txt` records the full resolved environment. Install with
`pip install --only-binary=:all: -r requirements.txt` to avoid an unnecessary source
build. Initial Numba compilation costs more than subsequent runs.

The chat sandbox retained the removed workspace path. Edits/tests were staged
under `/private/tmp` and copied to the actual repository with concurrent-change
checks through the normal write-approval mechanism. The repository path above is
current; do not recreate the removed `RDEPathwaySpaceXBackyard` folder.
