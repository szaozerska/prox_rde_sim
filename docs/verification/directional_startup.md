# Directional versus non-directional startup

October 22, 2026. RDE-001 remains OPEN.

## Implementation and publication order

The user explicitly requests implementation and push before any further tests.
This first publication is unverified; no tests or new CFD were run before it.
The existing conservative formed initializer is now the default, with explicit
+theta/-theta launch direction, signed momentum and a recorded imposed wave
speed. It seeds pressure, density, reaction progress and velocity consistently
with the surrogate's traveling profile. It is not simply velocity added to a hot
patch, not continuing tangential forcing, and not a resolved pre-detonator tube.

Original chemistry has a 23.768 mm tabulated tail, so the new charge is 30 mm;
copying the older 20 mm shortened-chemistry case would reject these inputs.
Chemistry (1 mm half-reaction length), mesh (0.5 mm) and feed remain unchanged.
The historic hot-patch cases and saved data remain intact.

## Matched comparison after publication

- Directional: `cases/run937_radial_directional.yaml`, +theta formed charge.
- Non-directional: unchanged `cases/run937_radial.yaml`; reuse `runs/radial_active`.
- Identical geometry, radial/wall closures, chemistry, mesh, feed and diagnostics.
- Both start with a nominal 3.8 mm layer, but spatial masks, initial mass, fresh
  inventory, energy and momentum differ. This compares startup protocols, not
  momentum alone or equal-energy ignition. Record these differences explicitly.
- Stop the new run at the first accepted checkpoint at/after 40 us, using the
  runner's normal interrupt/recovery path. Compare saved data through 40 us.
  This is an early coupling check, not a sustained-rotation acceptance test.
- Inspect pressure and reaction together at several heights; record whole-ring
  maxima, near-front reaction, initial inventories and conservation budgets.
  Use the same extraction/scales for both cases. Do not infer detonation from
  pressure motion alone. Stop on invalid states or a critical inconsistency.

## Verification after the first push

Run the initializer/runner tests, including direction-reflection symmetry and
unchanged non-initialization inputs. Exercise both default and radial production
initializations. Then run the bounded directional case above. Record all outcomes
here before the next commit. No pre-publication success is claimed.

## Results after implementation push 411a895

The 19 initializer/runner checks passed after the first push. A complete default
suite then ran 144 tests: 142 passed, one historical fixture failed and one opt-in
95 us reactive baseline was skipped. The fixture had assumed `config.yaml` still
contained the old hot patch. It now explicitly uses `cases/run937_hotpatch.yaml`;
all eight coupling tests passed on rerun. No physical assertion was weakened.

The directional run reached an accepted 40 us checkpoint at step 2780, in about
four minutes while the regression suite also ran. The old control is reused,
not recomputed. Identical non-initialization case settings are asserted in the
comparison script. Checkpoint/inputs/history/summary consistency and field hashes
were checked before reading this prefix.

| Quantity | Historical hot patch | Tangential formed launch |
|---|---:|---:|
| Initial total mass, mg | 82.3231 | 83.1642 |
| Initial unreacted mixture, mg | 15.3509 | 15.0175 |
| Initial tangential momentum, kg m/s | 0 | 0.00579854 |
| Initial total energy, J | 237.615 | 249.256 |
| Initialization energy change relative to each construction's reference, J | 5.02651 | 21.7868 |
| 40 us strongest lower-ring pressure, MPa | 1.76082 | 2.56288 |
| Reaction maximum within +/-8 mm of that peak, 1/s | 1.28394 | 7.08923 |
| Entire lower-ring maximum reaction, 1/s | 10.7720 | 837.375 |
| Maximum scaled native budget residual, 0–40 us | 9.25e-16 | 5.47e-16 |

The lower ring is z=0.751974 mm. At 40 us the directional main pressure peak is
x=74.310 mm; substantial residual lower-ring reaction is farther behind it.
Reaction also persists at higher axial locations. Directional startup changes
and strengthens early propagation, but does not retain strong reaction adjacent
to the leading near-injector pressure pulse through this window. This is not a
claim that all chamber reaction ceases or that later reinitiation is impossible.

The finite formed charge also has a trailing pressure/velocity discontinuity.
It can launch a weaker disturbance in the other direction; directional initial
momentum does not eliminate every secondary pressure wave. The comparison is
explicitly not an isolated direction or equal-energy experiment. The nominal
fresh-layer height matches; the cell averaging/masks and actual inventories differ.

Artifacts: [space–time comparison](directional_startup_comparison/space_time.png),
[40 us profiles](directional_startup_comparison/profiles_40us.png),
[animation](directional_startup_comparison/comparison.gif), and
[metrics/provenance](directional_startup_comparison/metrics.json).
The GIF uses the same fixed scales and saved timestamps for both protocols,
shows the lower 20 mm, and is an early-startup comparison only.

## Stop-handling issue found and fixed

The deliberate SIGINT after the 40 us field arrived inside a Numba dispatcher.
Python's KeyboardInterrupt surfaced as SystemError during the next attempted
step, at about 40.116 us. The native status remains `failed`; it is not relabelled.
The runner preserved the coherent 40 us checkpoint, with zero invalid states.
Analysis uses only that verified prefix, not the subsequent attempted step.

CLI SIGINT handling now records a stop request without raising inside compiled
kernels; the driver raises KeyboardInterrupt at the next coherent step boundary.
A regression sends SIGINT during a step, verifies interrupted status, one accepted
step, restored signal handling and successful restart. No exceptions are broadly
reclassified as harmless. The 40 us CFD was not repeated to hide the stop error.

The changed runner/initializer/coupling checks passed after this fix (28 actual
checks). A combined invocation could not import the workflow module because its
sibling-test import requires discovery; the workflow checks are rerun separately
using discovery. An earlier root-directory coupling invocation likewise lacked
the module path; the successful rerun used the documented working directory.
Raw failed and successful logs are retained. During artifact QA a GIF duration
list typo and a floating-point 40 us endpoint comparison were fixed; native
simulation data were not edited.

Reproduction from the repository root, in a checkout without the named output:

```sh
.venv/bin/python docs/verification/run_directional_startup.py
.venv/bin/python docs/verification/compare_directional_startup.py
```

The updated launcher benefits from deferred CLI interruption. The reader requires
a verified checkpoint covering the requested window before producing results.
Next physical gate remains the actual-refill-layer/chemistry/resolution assessment;
this result does not authorize treating the sustained-wave issue as resolved.

Final verification: the six workflow checks passed with discovery. Across the
full-suite run and corrective reruns, 144 distinct checks pass; the opt-in long
baseline remains skipped. The 34 affected initializer/runner/coupling/workflow
checks pass after the interrupt fix. This is an aggregate of the documented
runs, not a claim of one completely green full-suite invocation.

Artifact QA: 21 GIF frames, 5.5 s display duration, no loop; identical 0–40 us
sampling and fixed scales. Source and all 42 comparison-frame hashes verified;
PNG profiles/space-time maps and the final GIF frame visually inspected. Local
links and whitespace checks pass. Native data and unrelated working files are
unchanged.
