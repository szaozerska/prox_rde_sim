# NETL startup and multi-GPU engine continuation

October 27, 2026. Work is in progress on `3d-modelling`. **The original trajectory stopped at 67.2 microseconds after a species-closure failure. A corrected checkpoint branch, with all embedded walls refined, has passed bounded closure/finite-state checks through 60 microseconds and is continuing under the unchanged emergency guard. Small negative species remain failures; this is not a validated engine.** The requested long result is **200 microseconds**, starting from the same initial charge and continuing through native checkpoints. A requested duration is not evidence that a detonation completed a revolution.

## Initialization

The new `RDEStartup` native case follows the initial-state prescription in [Strakey and Ferguson's NETL/Fluent study, section III](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf): a stoichiometric methane/oxygen layer in the first 5 mm at 1 MPa; air beyond it with pressure tapering to 0.1 MPa at the exit; a 2-degree sector at 4 MPa and 3000 K. No tangential velocity or continuing ignition source is imposed.

Explicit assumptions: the unheated gas is 300 K; dry air is O2:N2 = 1:3.76; the hot sector retains the fresh local composition; its angular position ends at 90 degrees. The paper does not fully specify these initialization details. Native initial fields confirm zero velocity and the intended narrow hot sector.

This is **NETL-style initialization in the existing prototype**, not a reproduction of Fluent LES. The current equations remain reactive Euler. Resolved plenums/channels, molecular diffusion, LES, wall heat transfer, downstream core expansion, and NETL's mass-flow/pressure boundary conditions are not yet reproduced. Existing reservoir-fed injector mouths and extrapolating outlet remain. The public compact mechanism has not been established identical to NETL's mechanism. These limitations matter when interpreting longer engine behavior.

## Resolution and parallel execution

The base grid is 192³ (396.875 micrometres), with 198.4375 or 99.21875 micrometre cells around the first 10 mm and tagged pressure/temperature fronts. These are **finest local spacings**, not uniform meshes. Native embedded-boundary-aware gradient tagging avoids reacting to solid-cell values. The default volume-fraction rule initially refined all walls; disabling that blanket rule reduced first-level cells from 26.2 million to 8.3 million.

One MPI rank is explicitly bound to each GPU. The implementation supports one, two or four active ranks, native chemistry/flow work estimates for load balancing, AMR time subcycling, and CPU analysis while integration runs. A one-rank comparison inside the same four-GPU allocation used only one GPU for the solver. On the short 200-micrometre control, median coarse-step times were 2.99 seconds with one active GPU and 1.59 seconds with four. Pressure samples differed by at most 0.00022 Pa. This is a startup measurement, not a scaling promise for the developed engine.

A separate, checksum-verified Open MPI 4.1.8 build enables CUDA-aware buffers. The matched four-GPU control reduced the median step from 1.59 to 1.31 seconds (about 18%) while sampled pressures agreed within 0.00017 Pa. It is enabled in the longer continuation. The existing pinned solver binary is retained; cached images must match the native case source hashes.

## Checks so far

- 33 software tests pass, including startup units/composition, refinement levels and rank-to-GPU assignment and rejection of incompatible animation histories.
- The streaming AMR analyzer reproduces independently checked uniform-grid inventories to roundoff. It integrates leaf cells with volume fractions and samples actual native fields; it never rotates or synthesizes a wave.
- Both refined startup pilots reached 0.2 microseconds. The corrected 200-micrometre pilot passes saved-field checks, but logged coarse steps include a brief mass-fraction undershoot of about −1.1e-5. Its 100-micrometre counterpart has only roundoff-sized logged negatives (about −1.7e-14).
- Those short runs establish neither settled wave speed nor engine mesh convergence. At 0.2 microseconds the peak pressures still differ materially between meshes.

The first continuation reached 7 microseconds and was deliberately checkpointed to switch MPI transport. This was an operator stop, not a numerical crash. Its worst logged species mass fraction was −9.09e-4; the final negative-species inventory was about 2.0e-12 kg against 5.68e-4 kg total mass. The small integrated amount does not make the local undershoot physically valid. The checkpoint chain has now reached 14.6 microseconds; a detached continuation targets 200 microseconds. The worst logged species value through 14.4 microseconds was −1.01e-3. Burning-phase steps take roughly 4 seconds per 20 ns, with later burning-phase steps around 4–6 seconds, implying roughly 11–17 hours for 200 microseconds if those rates persist. The short-pilot scaling numbers therefore cannot be used as the engine runtime.

All raw fields and checkpoints are retained in Modal volume `prox-rde-netl-startup`. Compact previews contain pressure, temperature, methane, oxygen and native chemical heat release. Between-frame extrema are reported separately so snapshot selection cannot hide a transient failure.

A matched 14.4–14.6 microsecond restart comparison tested the native CVODE/cuSparse analytical-Jacobian backend against GMRES. Pressure relative L2 difference was 1.17e-5; maximum temperature difference was 0.043 K; integrated inventories agreed within 1e-12 relative. Both reproduced approximately −6.10e-4 minimum species mass fraction over that interval. The candidate was 6.49 times slower per median step and was rejected. This narrows the diagnosis: GMRES alone does not explain the undershoot. It does not prove which spatial, AMR or flow–chemistry coupling operation introduces it.

## Which ignition method to use later

Keep this NETL initial-state prescription as the reproducible baseline for studying propagation and sustained operation. Once a persistent wave exists, vary kernel width, energy, composition assumption and position to determine how strongly the eventual wave pattern depends on startup. Separate fixed-energy comparisons from fixed-pressure/temperature comparisons; changing sector width otherwise changes the ignition energy too.

An explicit spark/pre-detonator model becomes useful when the question is whether the intended hardware can ignite the engine, how reliably, and with what delay. [Argonne's CONVERGE study](https://doi.org/10.2514/6.2021-3642) includes that tube and its temporary connection to the annulus. It is a different physical question, not an automatic upgrade for every geometry. The baseline should not claim realistic ignition reliability or prescribe clockwise rotation.

## Continuation status

A follow-up in this chat checks the bounded campaign every 30 minutes, with no duplicate jobs and at most four GPUs. It will continue native checkpoints toward 200 microseconds, inspect whether reacting fronts actually circulate, and render the completed available history. If needed to observe two revolutions, the physical-time ceiling is 300 microseconds. The operational cutoff is October 27 at 8 p.m. Pacific; this is not a promised completion time. Nonfinite states, a crash, closure error above 1e-6, or local species values below −0.01 trigger investigation rather than automatic continuation. These emergency stop bounds are not acceptance criteria: even smaller negative concentrations remain physically invalid.

[Current native-field animation, 0–14.4 microseconds](progress_14p4us/pelec_annulus.gif) and [pressure/heat-release/reactant history](progress_14p4us/azimuth_time.png) are diagnostic progress artifacts, **not the requested 200–300 microsecond result**. They show two outward-propagating reacting fronts from the initial sector, not a demonstrated sustained rotating mode. Unequal snapshot time intervals are labeled explicitly.

### Observed startup collision

[Native animation through 45 microseconds](progress_45us/pelec_annulus.gif) and [matching chemical/pressure history](progress_45us/azimuth_time.png) show two oppositely moving startup fronts meeting near 270 degrees, on the opposite side of the annulus, between the 40 and 45 microsecond snapshots. At 45 microseconds the chamber methane inventory is 3.29e-8 kg, 0.278% of its initial 1.19e-5 kg. This is an open-system inventory ratio, not a closed-system fuel-conversion measurement. No full revolution or sustained co-rotating mode has been established. The banner reports the historical minimum species fraction (−1.02e-3), not the minimum in the final frame. The run continued after this event but was subsequently checkpoint-stopped for the closure diagnosis below.

### Species-closure stop and diagnostic replay

Eight logged steps between 55.98 and 56.12 microseconds report species sums between 0.96516 and 1.06166. Saved snapshots on either side have roundoff closure, so saved-frame checks alone missed the event. The long run was checkpoint-stopped when the between-frame error was found. This remains unresolved; it is not reclassified as a pass.

The event coincides with one AMR regrid interval. In the pinned PeleC source, `monitor_extrema()` constructs an ordinary `sumY` MultiFab and reduces all cells without an active-fluid/fine-coverage mask. A replay will therefore distinguish active leaf fluid, coarse fluid covered by finer grids, and solid cells before interpreting the error. The analyzer now records these regions separately. A native-log guard requests checkpoint-stop for nonfinite extrema, species closure error above 1e-6, or species fractions below −0.01; these remain emergency bounds, not physical acceptance criteria. Four new tests include the actual transient pattern and prove a later good step cannot erase it.

### Active-fluid failure confirmed by dense replay

The guarded 55.8–56.2 microsecond replay stopped at 56.12 microseconds. At 56.0 microseconds, 168 active leaf-fluid cells exceed the 1e-8 closure tolerance; the maximum species sum is 1.0915469. The worst cell is on level 0 at (26.789, −26.789, 27.583) mm, with fluid volume fraction 0.97222. Coarse cells covered by finer grids and solid cells also have errors, but they do not explain away the active-fluid failure. Fields remain finite and native chemical heat release is available. The replay reproduces the event timing, although its maximum error differs from the original run; it is not a bitwise reproduction.

[Dense replay evidence](evidence/closure_capture/checks.json) and the raw extrema log are preserved. No guard was relaxed and no state was renormalized. A matched bounded replay freezes the existing mesh hierarchy (`amr.regrid_int=-1`) while retaining the same checkpoint, chemistry, time step, reflux and ignition history. This isolates the involvement of mesh changes; it is not yet a correction suitable for a long engine run.

The fixed-hierarchy control's native solver log reached 56.2 microseconds with maximum species-closure error 6.66e-16 across all 20 coarse steps. Its minimum species value remains −6.84e-10. This implicates mesh adaptation or its interaction with embedded-wall/coarse–fine synchronization, without identifying the faulty operation. The next bounded candidate retains mesh adaptation but refines every embedded wall, avoiding coarse/fine transitions through cut cells. That bounded candidate completed normally; a longer validation remains necessary.

The fixed-hierarchy control finished normally, and saved native fields confirm roundoff closure in active fluid. Both replays have finite sampled pressure, temperature and native chemical heat release; the heat-release field includes both exothermic and endothermic values. See [comparison](closure_replay_comparison.json).

### Wall-refinement candidate and longer validation

Refining every embedded wall while retaining adaptive flow refinement kept species closure at roundoff through 56.2 microseconds, including the previously failing interval. Saved-field maximum closure error was 7.77e-16; the minimum saved species fraction was still −1.16e-9, so positivity remains a diagnostic failure. Pressure, temperature and sampled native chemical heat release were finite. The native [mesh audit](evidence/closure_refined_walls/mesh_audit.json) confirms zero active cut cells below the finest level in all five snapshots. This is evidence for the configuration change, not proof of the exact faulty operation in the earlier solver setup.

The median coarse-step cost rose from 2.90 seconds for the frozen-hierarchy control to 4.69 seconds for the refined-wall candidate. Allocated level-1 cells are about 26.2 million. A bounded continuation from the candidate's 56.2-microsecond checkpoint now targets 60 microseconds, retaining the same ignition history and emergency guard. The invalid 67.2-microsecond checkpoint remains stopped. No sustained rotating mode or 200-microsecond result is claimed.

### Review at 60 microseconds

The wall-refined continuation completed normally at 60 microseconds. All 190 logged coarse steps and 24 mesh-adaptation events retained roundoff closure (maximum 8.88e-16); nine native mesh audits found no active wall-cut cells below the finest level. Saved pressure, temperature, density/energy/species checks and sampled native chemical heat release remained finite. The minimum saved species fraction was −2.25e-10, so the run still fails positivity acceptance. These results justify guarded diagnostic continuation, not a claim that every numerical or physical issue is fixed.

The new long segment restarts `closure_walls_validation_56p2_to_60us/chk03010` at 60 microseconds and targets 200 microseconds. It retains the same ignition history and chemistry. The policy change at 55.8 microseconds must remain explicit in any later animation; the invalid suffix of the original trajectory must not be merged into the corrected history. Raw fields and checkpoints remain on the volume.

### Remote interruption and recovery from 90 microseconds

The corrected segment logged 97.62 microseconds with roundoff species closure and finite extrema, then remote execution was interrupted. The reported call error was an attempt encountering the existing-directory guard; the original interruption cause is not established. There was no result file and no remaining Modal container. The last completed checkpoint is at 90 microseconds, confirmed by its native header and completed write in the log. A uniquely named detached recovery starts there without another ignition. Fields from the interrupted suffix will not be spliced into this recovery.

[Actual 60–90 microsecond animation](progress_60_to_90us/pelec_annulus.gif) and [pressure/heat-release/reactant history](progress_60_to_90us/azimuth_time.png) show the retained corrected segment. Peak pressure declines from 13.06 to 4.29 MPa and methane inventory remains very small; these fields do not establish a sustained rotating detonation. The segment's worst logged species value was −3.96e-9 and remains a diagnostic failure. The requested 200-microsecond result is unfinished.

The recovery keeps all numerical guards, checkpoints every 5 microseconds, and rechecks an absolute campaign cutoff on the worker after cloud queuing. It requests a native checkpoint stop before the cutoff or segment wall limit. Three new cutoff tests cover queue delays, timezone handling and refusal to start near/after the deadline; all 36 software tests pass.

### Full retained history, zero to 130 microseconds

[Startup-to-current native animation](progress_zero_to_130us/pelec_annulus.gif) uses 46 actual snapshots from zero through 130 microseconds. Each restart was checked against its parent checkpoint header and allocation record. Parent histories stop at the checkpoint used by the child, excluding both abandoned suffixes. At the 55.8-microsecond wall-policy change, the parent frame is retained at the shared timestamp and the next child frame follows; the fields are never averaged together. [Provenance](progress_zero_to_130us/trajectory_provenance.json) records the original full-run checks separately from checks of the retained intervals.

The animation shows two opposed startup waves, their collision around 40–45 microseconds, and weakening downstream disturbances. Methane inventory begins to rebuild after roughly 100 microseconds. This does not establish sustained rotating detonation. The orange warning reports the worst species value over the retained history, including early startup errors, rather than the value in the displayed frame. Read the timestamps: unequal native output intervals are played at a fixed frame rate. The live solver continues beyond the exported movie's endpoint.

### Planned segment stop at 150.46 microseconds

The recovery from 90 microseconds checkpoint-stopped at its four-hour wall limit. Native checkpoint `long200_recovery_from90us/chk07533` has a completed write and matching header time. The call finished with the expected checkpoint-stop code 6, successful final analysis and no emergency guard violation; no container remained before continuation. Closure stayed at roundoff (maximum 1.11e-15), while the segment minimum species fraction was −3.96e-9 and remains a diagnostic failure. Final active-fluid pressure spans 0.552–1.370 MPa and temperature 249.8–3401 K; sampled native heat release is finite. Methane inventory has increased to 1.760 mg, which alone does not establish reacting circulation.

A unique four-GPU continuation, `long200_from150p46us_final`, retains this checkpoint, ignition history, wall refinement, chemistry and all guards. The worker started at 18:25:37 PDT after a substantial launch delay, so its requested 7800-second limit is shortened by the unchanged 20:00 PDT cutoff. The target remains 200 microseconds but may not fit that operational bound. No directional ignition has been introduced in response to the review; that remains a separate comparison.
