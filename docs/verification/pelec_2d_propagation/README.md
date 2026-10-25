# Native 2D propagation prerequisite: unresolved

**No Run 937 or additional-engine movie was computed in this increment.**
The requested long engine campaign is blocked by P2 propagation checks. This
folder contains real native PeleC GPU controls and their diagnostics; it does
not contain sustained-engine evidence. The old custom solver is unchanged.

## What ran

Pinned upstream PeleC/PelePhysics, 2D double precision, one H100 per invocation,
4 CPU cores and 16 GiB host memory. No native flux, kinetics or thermodynamics
source patches. The candidate upstream FFCM1_Red has 21 species / 124 reactions
and NASA polynomial intervals 200–5000 K. It is not FFCMy-12 or a validated
Run 937 mechanism. P1 GRI chemistry remains available separately.

Independent Cantera/SDToolbox at 377916.972 Pa, 300 K, phi 1.176 gives:
CJ speed 2530.813 m/s, equilibrium product temperature 3988.422 K, and half
chemical-heat length 45.7689 µm. Tightening the reference integrator changes the
half-heat length by 6.0e-8 relative. `reference.json` records jump, sonic, element
and integration checks. `znd.npz` contains the finite formed launch profile.
This different mechanism need not reproduce the earlier GRI 39.5 µm value.

The planar domain is 4.096 mm long with a formed +x wave initially at 2.048 mm;
8 identical periodic transverse cells. Duration is 0.2 µs, deliberately a
prerequisite, not the requested 2 ms engine history. Launch cell averages are
integrated conservatively. There is no ongoing ignition or imposed wave speed.
Initial and boundary gas carry the same elemental composition, so local element
fractions should remain constant for these non-diffusive controls.

| Control | Cell / time step | Fitted speed, m/s | Result |
| --- | --- | ---: | --- |
| Godunov order 2 | 8 µm / 0.2 ns | 3425.94 | negative species, local element error, wave checks fail |
| Godunov order 2 | 4 µm / 0.1 ns | 3033.43 | negative species, local element error, EOS and wave checks fail |
| Godunov order 1 | 8 µm / 0.2 ns | 3061.99 | intermediate negative species missed by snapshots; wave checks fail |
| Godunov order 1 | 8 µm / 0.1 ns | 3055.48 | state/element/EOS/budgets pass; wave checks fail |
| MOL order 1 | 2 µm / 0.1 ns | 3266.85 | state/element/EOS/budgets pass; wave checks fail |
| MOL order 1 | 1 µm / 0.05 ns | 3359.56 | state/element/EOS/budgets pass; wave checks fail |
| MOL order 1, moving frame | 2 µm / 0.1 ns | 3483.74 | Tmax 5116.50 K; local element, EOS and wave checks fail |
| MOL order 1, moving frame | 1 µm / 0.05 ns | 3491.67 | Tmax 5400.88 K; local element, EOS and wave checks fail |

Speeds are laboratory-coordinate fits over 0.05–0.2 µs; three pressure thresholds
are retained in each report. The boost is exactly m'=m-rho*V and
E'=E-V*m+rho*V²/2, with V=CJ. This changes coordinates, not physical forcing.
The source references remain the same. It did not cure the numerical concerns.

A separate uniform hot native control follows the same mechanism from about
3881 to 4064 K. It **passes** against independent Cantera: maximum relative
T/P errors 1.60e-8 / 1.05e-8, maximum absolute species error 1.09e-8, and energy
change 3.96e-11 relative. This checks hot chemistry integration, not shock
transport, native source-term clipping, detonation stability, or all temperatures.

The eight completed wave controls used about 25.8 H100-minutes in aggregate;
the hot control took 4.14 seconds. Image building, queueing, analysis and rendering
are additional. This does not establish runtime for a resolved engine.

## What can and cannot be inferred

The initial lab-frame fine solutions overdrive and contract their reaction zone.
The 2/1 µm fitted speeds differ by 2.84%; the finest final half-heat distance is
2.10 µm. That final zone is inadequately resolved even though the initial CJ
length spans roughly 46 cells. A separate steady overdriven reference at the
late local speed predicts 5.51 µm. That comparison is diagnostic, not acceptance
of a transient solution as steady.

The original screening limits are 5% speed and 20% half-heat-distance error
against steady CJ/ZND. They remain failed. However, this 0.2 µs window spans only
about 1.3 reference induction times; methane/oxygen can be intrinsically
unstable. A short transient deviation alone does not prove a solver bug. The
important independent failures are negative species, local element changes,
frame sensitivity, and excursions outside the mechanism's stated temperature
range. Longer, buffered, converged planar results are needed after those are
understood. No conclusion about experimental sustainment follows yet.

In the moving-frame cases the maximum absolute elemental-fraction errors are
4.36e-4 / 3.75e-4 despite valid saved species bounds and sum(Y)≈1. In the 2 µm
case the element error is already visible at 0.0901 µs before the first saved
snapshot above 5000 K. The cause is not established. Inspect species transport,
reaction/advection coupling and any intermediate corrections; do not simply
blame thermodynamic extrapolation. Source inspection found EB cleanup only near
cut cells; these controls have none, so that routine is not an established cause.
The dual-energy fallback hypothesis also does not match the active defaults.

Cantera normalizes invalid species when reconstructing states; an EOS residual
in a run with negative species is not independent proof of an EOS bug. Global
budgets use saved boundary fluxes and are screening checks, not flux-register
accounting. They cannot replace local species/element checks.

These controls have no annular wall, plenum, discrete jet or fuel depletion.
They therefore do not establish that gap geometry, injector angle or a missing
supply causes the discrepancies. Conversely, they do not eliminate those factors
from a real engine. RDE-001 remains open; the new backend has not retested it.

## Actual diagnostic animation

[Planar pressure and chemical-heat comparison](planar_comparison.gif) is rendered
from the saved 2 and 1 µm native lab-frame fields, with actual times and the
independent steady CJ position. It is **not an engine GIF**. The wrapped engine
movie is deliberately absent; wrapping a planar verification strip would imply
an engine result that was not computed.

## Evidence and reproduction

`summary.json` indexes all controls. Each subdirectory includes native inputs,
case, remote call ID, status/archive SHA256, compressed solver log, every-step
and field analysis, and compact SI profiles. Full checksummed native archives
remain in ignored `runs_cfd/`; they are not uploaded to Git. `build_manifest.json`
records upstream pins, mechanism and initializer hashes and the executable.
`hot_reactor/` records the independent high-temperature check. Python adapter
checks are in `adapter_tests.txt`; successful software tests do not override
failed physical acceptance.

From the repository root, use the isolated environment and the mechanism YAML
from the exact pinned PelePhysics source (hash in `source_lock.json`):

```sh
.tooling/pelec-venv/bin/python cfd/pelec/propagation/prepare.py NEW_REFERENCE --mechanism /absolute/path/to/pinned/FFCM1_Red/mechanism.yaml
.tooling/pelec-venv/bin/modal run --profile prox --env main cfd/pelec/propagation/run_modal.py --case-file NEW_REFERENCE/case_n512.json --profile-file NEW_REFERENCE/profile_n512.dat --output NEW_RUN --dt 2e-10
.tooling/pelec-venv/bin/python cfd/pelec/propagation/analyze_wave.py NEW_RUN --reference NEW_REFERENCE/reference.json --output NEW_ANALYSIS
```

The generated cases default to Godunov order 2. For the recorded MOL controls,
copy the case to a new path and set `hydro_method` to `mol` and
`reconstruction_order` to 1. Use the matching Nx profile and recorded time step.
`boost.py` creates an exact conservative moving-frame case/profile; never edit
a saved original. `hot_reactor.py` prepares/analyzes the separate reactor check.
Analysis returns a nonzero exit code for failed acceptance even if native CFD
returned zero. All runs here completed their specified native window.

Encountered workflow issues: one finest-grid submission stopped before CFD due
to floating-point equality in the time-step guard; the guard now allows 1e-12
relative roundoff and the retry is recorded. The first analysis JSON serialization
rejected NumPy booleans; conversion to Python bool fixed reporting without
changing raw results. Live container inspection helpers hung and were cancelled;
the actual CFD invocations were allowed to finish. An independent SciPy reference
integration emitted an internal overflow warning; it completed and the tighter
reference/invariant checks passed. No temperatures or wave fields were clipped
by this adapter to force acceptance.

The [updated plan](../../plans/pelec_2d_transition.md) lists the next isolated
checks and keeps the long Run 937 / 51-FI-5 / 25-FI-5 campaign pending.
