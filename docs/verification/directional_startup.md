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
