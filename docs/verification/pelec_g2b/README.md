# Native formed-wave initialization and transport diagnosis

**G2b is not passed.** The initial cell-average import and a 2 ns first-order
reacting probe pass their numerical field checks. This is not evidence of a
sustained planar detonation, much less a rotating engine wave. Longer-window,
mesh/timestep, wave-speed/reaction-distance and open-boundary budget checks remain.

The native initializer is the only new C++ case code. All evolved physics is
pinned PeleC/PelePhysics. Full GRI chemistry, source-derived generated constants,
FP64, native MOL/CVODE, the documented 5000 K inverse interval, and no continuing
ignition are used. A 2.048 mm domain starts with a right-moving independent ZND
wave at x=0.512 mm; 256/512 x cells give 8/4 um spacing, with 8×8 uniform periodic
transverse cells. Ends use native first-order extrapolation. The short reaction
window is initially outside the boundary characteristic cones; this is checked,
not permission to extend indefinitely with the same domain.

## Initialization issues found and fixed

- The first tightened ZND profile still contained a -2.54e-12 trace-species
  residue. Tightening the absolute integration tolerance from 2e-12 to 1e-14
  reduced the subsequent bounded cleanup to 4.00e-14. No native field clipping
  was introduced and the original failed reference is preserved.
- Four/eight-point cell quadrature differed by 1.29e-4 in the coarse profile's
  worst normalized species L1 diagnostic. Exact integration of the independently
  computed piecewise-linear **conserved** profile replaces quadrature. Domain
  integral errors are 2.50e-14 / 1.53e-13. This does not make the spatial CFD
  solution exact; the profile interpolation and CFD resolution remain separate.
- Native initial conserved fields agree with the imported averages to <3.3e-17
  relative L1. CGS/SI conversions and shock placement are checked in native data.
- A launch-bound equality rejected 2e-10 versus floating-point 8e-6/40000; a
  1e-12 relative comparison allowance fixes only roundoff, not the timestep.

## Transport root-cause controls

All rows below cover the same physical 2 ns interval. The elemental quantity is
the largest **local mass-fraction deviation** from the uniform premixed elemental
composition; it is distinct from a global conservation defect.

| Native control | Smallest species Y (magnitude if negative) | Maximum local elemental deviation |
|---|---:|---:|
| Second-order, 8 um | -6.13e-10 | 0.002350 |
| Same grid, timestep halved | -7.77e-10 | 0.002342 |
| Second-order, 4 um | -1.22e-9 | 0.008474 |
| Chemistry disabled, 8 um | -4.55e-10 | 0.002711 |
| Actual first-order, reacting, 8 um | -6.38e-14 | 5.74e-14 |

The original strict species/local-composition gates are retained. Total elemental
mass ratios stay within 8e-15 in the measured controls: the local deviations are
not evidence of globally created atoms. Timestep halving does not cure them,
chemistry removal reproduces them, and changing actual spatial reconstruction
removes them. Source inspection shows independently limited characteristic
species slopes in `MOL.H`/`MOL.cpp`; these can alter local elemental ratios even
with conservative species fluxes. The finer-grid maximum gets worse for this
profile, so do not claim this defect is converged or will disappear automatically.

A configuration trap was also measured: setting `mol_iorder=1` alone leaves the
solution unchanged to roundoff, because pinned `Diffusion.cpp` passes
**`plm_iorder`** to the MOL flux routine. Both are now explicit. No custom flux or
upstream solver repair was written. First-order is only the simplest native
candidate for a subsequent accuracy check; its additional diffusion can itself
cause false decay or alter reaction coupling.

The corrected first-order probe also passes species sum, EOS pressure/energy,
transverse invariance and boundary-cone checks. Energy consistency is 1.69e-10;
transverse velocity is zero. It takes 4.85 s on one H100, including native startup
but excluding cloud queue/build. The native initializer build took 107.56 s.
These numbers do not predict full-engine runtime or establish CPU/GPU scaling.

## Failed infrastructure/configuration attempts are retained

A frozen-control attempt reached its final time but failed strict unused-input
checking because CVODE tolerances were still supplied while reactions were off.
It is marked failed. Removing only those inactive inputs allows clean completion;
the transport defects remain. A report initially failed on NumPy boolean JSON
serialization; converting check values to ordinary booleans fixes the report,
without rerunning or changing the solver. One first-order launch lost its local
Modal connection. App listing confirmed it stopped with zero tasks before one
repeat. New launches save their function-call ID before waiting, enabling recovery;
probe queue/startup/execution is bounded to 600 s, separately from image building.

Raw native fields and unsuccessful attempts are retained under ignored `runs3d`
and the task's temporary logs. Compact commands, reports and source/binary hashes
are committed here. Reproduce a fresh reference with `prepare_wave.py NEW_DIR`,
then run `modal_wave.py` with its case/profile paths, collect through the existing
checksum verifier, and call `analyze_wave.py RUN_DIR REFERENCE_DIR`. The default
`--reconstruction-order 1` selects the verified short-probe candidate; use 2 only
for the explicitly failed higher-order diagnostic. Keep all
longer runs bounded and never interpret mere final-time completion as a pass.

![Native transport diagnosis](transport_diagnosis.png)
