# P2 prerequisites for long native 2D animations

The 2026-10-25 request adds Run 937 and additional engine geometries, two GIFs per
case (unwrapped and wrapped), and a 2 ms target rather than a short smoke run.
The engine catalog is `../engine/cases.json`. The smaller cases reproduce paper
geometry only and use explicitly assumed Run 937 equivalent feed. No experimental
run identity, separate injector mixing, or measured wave mode is invented.

Before those runs, this increment tests a candidate **unmodified FFCM1_Red**
mechanism (21 species, 124 reactions) in native 2D GPU PeleC. Its upstream NASA
thermodynamics cover 200–5000 K; GRI's native inversion stops at 3000 K. P1 and its
GRI implementation remain unchanged. FFCM1_Red is not FFCMy-12 used in some RDE
papers and is not assumed interchangeable with full FFCM-1. Its ignition-delay
sensitivity and missing low-temperature pathways limit predictive use. Selection
here is conditional on numerical checks, not proof of experimental validity.

Sources: pinned PelePhysics files and Stanford's FFCM-1/FFCM-2 documentation:
https://web.stanford.edu/group/haiwanglab/FFCM1/
https://web.stanford.edu/group/haiwanglab/FFCM2/docs/TrialModel/PreliminaryTest/
The RDE chemistry comparison in Batista et al. 2021 distinguishes GRI, FFCM-1,
and FFCMy-12: https://doi.org/10.3390/en14123387 .

## Numerical checks

- Independent CJ/ZND with the bundled mechanism; energy/momentum/species checks
  and tighter ZND integration. Save the complete finite directional profile.
- Native 2D Godunov and MOL transport, CVODE chemistry, no source/thermo/flux patches.
- Planar 8, 4, 2 and 1 micrometer cells; temporal check separately. A 2 mm left buffer
  avoids using the inadequate causal buffer found in independent 3D controls.
- Inspect every logged step for invalid states; compare saved pressure-front
  motion and reaction structure with the reference. Require speed within 5%,
  reaction-distance agreement within 20%, meaningful spatial behavior, and
  no unexplained conservation error before interpreting an engine result.
- A critical numerical failure blocks longer engine interpretation. Do not
  describe a pressure pulse as a sustained detonation or enlarge tolerances to
  obtain an attractive animation.

The 2 ms engine target is roughly 16 Run 937 experimental reference revolutions.
It is an early sustainment window, not the experimental 0.696 s burn or a promise
of an equilibrated wave mode. Longer plots need pressure, heat release, fuel
inventory, wave tracks and actual inflow/outflow alongside the two GIFs.

## Recorded outcome

P2 has not passed. Eight wave controls and a passing hot-reactor check are in
[the evidence report](../../../docs/verification/pelec_2d_propagation/README.md).
The engine catalog is still pending; `engine/visualize.py` is a renderer for
future native SI engine exports, not evidence that an engine adapter ran.
