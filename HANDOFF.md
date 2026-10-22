# Handoff after D2 coupling diagnostics

Snapshot: **October 21, 2026**. Repository:
`/Users/sgfx/Desktop/Projects/prox_rde_sim`.

## Start here

The current plan remains [revision 6](first_sim_plan.md). Foundation and D0 were
pushed through commit `5ed8aa7`; this publication adds the implemented D1/D2
source, tests, selected evidence and unresolved-case record. The user authorized
pushing these increments with clear limitations. Bulk simulation runs remain local
and Git-ignored.

**D2 result:** the 7.6 mm starting layer produces a stronger early transient than
the D1 3.8 mm layer, but neither demonstrates sustained rotating detonation by
189.394 µs. Both complete without invalid states. The larger layer also enlarges
the ignition/product masks: initialization energy rises from 5.027 to 9.425 J.
This is a startup sensitivity, not a pure fill-height change at fixed ignition.
See [D2 verification](docs/verification/d2_coupling.md) and its comparison figures.

**OPEN RDE-001:** [Run 937 sustained detonation unresolved](docs/verification/run937_unresolved.md)
is the canonical issue record. D0-D2 are short development increments; they do not
mean the broader numbered physics stages have passed. Physical-reference/refinement
work in Stage 1 remains incomplete, Stage 3's sustained-wave criterion is not met,
and the first working physical 2D iteration has not been delivered. The reactive
solver can attempt propagation and passes its short 1D check, but the tested 2D
configuration fails to demonstrate the intended phenomenon. Missing reference work
and unresolved model/numerical behavior must be investigated; no automatic recovery
with a longer run or a guaranteed chemistry fix is established.

**Next work:** a controlled hot-product/fresh-gas contact problem with fixed-chemistry
spatial refinement, and the Run 937 physical-reference subset of G0 (Cantera with
SDToolbox / GRI-Mech 3.0 CJ/ZND; CEA heat-release reproduction or an explicitly
labeled independent equilibrium cross-check). Use the evidence to select a bounded
2D refinement, boundary experiment or verified chemistry change. RDE-001 records
candidate causes, startup confounding, evidence provenance and fix criteria.
No longer run or parameter sweep is justified by D2 alone.

## D2 additions

- `coupling.py`: chemical-to-thermal conversion, full-height distributions,
  periodic pressure-peak candidates and conservative tracking across saved frames.
  Dropouts, ambiguous matches and inadequate cadence break tracks. These are
  inspection operators, not a shock detector or detonation/mode classifier.
- `plot.py --coupling`: full-height pressure/reaction fields, conversion-height
  histories and several ring heights with candidate tracks. `--compare-run`
  renders both cases and explicitly reports every changed input and source equality.
- `cases/run937_fill_7p6mm.yaml`: only fill_height_mm differs from the D1 case.
  Chemistry, numerical sources, grid, plenum and outlet are byte-identical to D1.
- Eight new tests plus import coverage. The full 51-test suite passed, including
  the opt-in 1D reactive baseline. The log records Matplotlib pending-deprecation
  notices; no failures or skips occurred. Existing dependencies were reused.
- Run data: `rde_sim_starter/runs/d2_fill_7p6mm/`; derived comparison:
  `rde_sim_starter/runs/d2_coupling_comparison/`. Both are Git-ignored. Selected
  figures, compact metrics and the test log are retained in `docs/verification/`.

The diagnostic quantity rho*q*omega measures internal chemical-to-thermal
conversion; do not add it to total energy again. Pressure peaks and high-pressure
conversion fractions do not establish shock/reaction coupling on their own.
D2 numerical source files and checkpoint format are unchanged, so D1 checkpoints
remain compatible. Plot/report hashes identify the analysis implementation.

## Earlier D1 changes

- Added a conservative global reaction-slope time-step bound. For the inherited
  calibration, `source_cfl=0.05` gives **14.455 ns**. The bound includes reactant
  depletion and constant-energy thermal acceleration. It does not change k, Ea,
  q, gamma or reaction length, and it is not an adaptive error estimator.
- The independent closed-reactor reference uses SciPy DOP853 and the scalar
  constant-total-energy ODE. Fresh, preheated and partly reacted states were
  checked. Halving the source fraction gives about fourfold error reduction in
  the active cases. Source tests conserve total energy without adding heat twice.
- The first strict 1D baseline stopped on progress `1.0000000000000002`.
  Validation now permits **64 float64 epsilons** (~1.42e-14) around [0,1], records
  the maximum excursion, and leaves conserved values untouched. Substantial
  excursions, NaNs and nonphysical density/pressure still stop the run. The source
  rate is zero beyond complete reaction within that roundoff tolerance. There are
  no state floors, clipping, repairs or repair budgets.
- Corrected the equivalent converging injector opening. Choked flow uses one sonic
  opening-plane pressure/temperature/velocity; the old implementation combined
  choked mass flow with further expansion to chamber pressure. Normal momentum
  now includes nominal open-area jet pressure plus chamber pressure on the closed
  area. Cd still scales transmitted flow, and its inherited value 0.76 is not
  retuned or independently validated. Separate fuel/oxidizer mixing is unresolved.
- Verified that outlet selection uses axial Mach even with large azimuthal
  velocity. The inherited pressure outlet remains a simple closure; reverse-flow
  behavior and downstream sensitivity are not physically validated.
- Extended `test_1d.py` with a saved, bounded 1D experiment; its initialization is
  shared with the opt-in propagation test. Added native fixed-probe histories and
  reaction-rate fields to the engine runner.
- Added read-only `plot.py --tube` and `--run` interfaces: field panels,
  pressure/progress/reaction space–time maps, station traces/profile, mass-flow,
  conservation and axial-Mach diagnostics. Hysteretic pressure event times are
  explicitly not confirmed detonation passages or mode counts. Plotting never
  advances or mutates a saved run; the reader ignores post-checkpoint tails.

## Results and artifacts

The 95 µs, 0.25 mm 1D experiment gives **2490.157 m/s**, **+0.7753%** relative to
its fitted CJ reference. Halving the source fraction changes the speed by
**0.0222 m/s** (~0.00089%). The final pressure-to-50%-reaction-front separation is
1.25 mm, measured on the grid; this is not a spatial convergence study or detailed-
chemistry validation. Both source fractions complete without invalid states.

The Run 937 experiment uses the frozen one-step chemistry, 0.5 mm requested grid,
447 × 152 cells, the documented initial patch, corrected injector and three
expected passage intervals. It completed 13,165 steps to 189.394 µs without
invalid states, but the pressure fronts weakened and sustained rotating detonation
was not demonstrated. Reaction remains near the fresh/product interface. One
initiation pressure crossing is not a confirmed detonation passage. No extension
was made; short-window averages include startup. See the report and saved figures.

Generated data (Git-ignored):

- `rde_sim_starter/runs/d1_tube_default/`
- `rde_sim_starter/runs/d1_tube_half_step/`
- `rde_sim_starter/runs/d1_run937/`

Selected figures and compact metrics are in `docs/verification/`. The earlier
foundation/D0 reports are historical evidence. Original calibration and supplied
JSON/PNGs remain unchanged. Updated source intentionally cannot resume D0
checkpoints: resume requires the original numerical implementation/environment.
D1 checkpoints use format version 2 and persist the roundoff diagnostic.

## Commands

With the existing environment, from the repository root:

```sh
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
RDE_RUN_REACTIVE_BASELINE=1 NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -v
```

The first command keeps the 95 µs propagation check opt-in; the second includes it.
The final D2 full run passed all 51 tests, including the opt-in reactive check. To create new artifacts:

```sh
NUMBA_NUM_THREADS=2 ../.venv/bin/python test_1d.py --out runs/new_tube
../.venv/bin/python plot.py --tube runs/new_tube --out runs/new_tube/plots
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --out runs/new_run937
../.venv/bin/python plot.py --run runs/new_run937 --out runs/new_run937/plots
```

Output destinations must be new. Reuse saved flow data for plot changes. The
optional `source_cfl=None` solver API exists only for explicit baseline/failure
experiments; the production case runner requires a positive source fraction.

## Preserve these limits

- Run 937 default: three expected intervals = **189.394 µs**. Extend the same saved
  run only for a specific unresolved observation, to five total = **315.657 µs**.
  Reference frequency budgets duration and does not impose a wave count or speed.
- Pressure fronts alone are insufficient evidence of detonation. Compare pressure
  and reaction in the same saved fields. Failure and inconclusive outcomes are useful.
- Initial pressure is an inherited empirical fit, and initial fill/ignition can
  select transients. Startup pressure agreement is not independent validation.
- Native flux closure verifies discrete accounting, not correct boundary physics.
  The annulus-exit contribution is not whole-engine thrust. Angular storage/flux
  balance does not determine mechanical torque without wall-traction physics.
- No wall-friction/heat-loss closure, physical thermochemistry, independent force
  validation, CAD mesher or 3D solver was added. Constant depth does not resolve
  radial dynamics. Keep outer-radius and mean-radius wave speeds distinct.
- Do not restore the historical incorrect 0.75 mm reaction-zone claim or retune
  reaction length with the mesh. Two-step event timing needs independent tests.
- Keep `.venv`, caches, bulk runs and the local review out of Git. This publication
  includes D1/D2 source, tests and selected evidence under the user's push request;
  no sustained-wave fix or new CFD experiment is part of the publication.

## Environment and workspace

Python 3.12.0, macOS x86_64, workspace `.venv`; versions remain pinned in
`requirements.txt`. No new dependency or backend installation was needed.
Use two Numba threads for these small checks. See the verification metrics for
measured timings; they are not general solver throughput benchmarks.

The sandbox still lists the removed `RDEPathwaySpaceXBackyard` folder. Edits and
D2 experiments and tests were staged under `/private/tmp/prox_rde_d2_work` using
the repository environment. Transfer uses concurrent-change checks and byte
verification through the normal approval path. The first transfer request timed
out in automatic review before process creation; the staged work was unaffected.
The abandoned Google Drive troubleshooting is unrelated and must remain stopped.
