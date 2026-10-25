# Native 3D prototype: implemented, physical validation fails

Work on `3d-modelling`, October 24–25, 2026. Both upstream solvers now execute
methane/oxygen chemistry and true three-dimensional annular cases on Modal.
**These are diagnostic startup animations, not validated sustained detonations.**
The requested 1–5 ms circulating-engine result has not been achieved. The latest
user authorization allowed a bounded prototype despite the earlier gate failures;
none of those failures is reclassified as a pass.

[GPU animation](pelec_visual/pelec_annulus.gif) ·
[CPU animation](foam_visual/detonationfoam_annulus.gif) ·
[Reproduction commands](../../../tools/CFD_PROTOTYPE.md)

## What the animations contain

PeleC: **0–10 µs**, 128³ Cartesian cells with embedded annular walls, one H100;
**431.9 seconds integration**. detonationFoam: **0–1 µs**, 576 × 8 × 24 body-fitted
cells, 16 CPU cores; **84.7 seconds integration**, 221 seconds including mesh,
initialization, reconstruction and analysis. GPU timing excludes field analysis,
transfer and image construction. These different meshes and methods are **not a
CPU/GPU speedup benchmark**. Linear extrapolation of this GPU run is approximately
12 hours per millisecond, before output; it is not a prediction of later throughput.
The original 1–2 hour target is therefore not established.

Every frame samples saved native 3D pressure and temperature fields at radius
35.6 mm. Nothing rotates the fields or prescribes wave travel. The GPU pressure
maximum moves from the initialized charge toward increasing azimuth; this alone
does not establish a self-sustaining detonation. A finite 30 mm arc, 3.8 mm-high
charge starts at 10 MPa, 4000 K and 1900 m/s tangential velocity. There is no
continuing ignition source. This is an initialized hot charge, not simulated
spark ignition or a pre-detonator tube.

A local-client disconnection interrupted the first CPU annular attempt. The
retry used Modal's detached mode and completed. Interrupted evidence is retained;
it is not a numerical solver failure.

## Physical assumptions and their cost

| Choice | Benefit | What it prevents us from claiming |
|---|---|---|
| Full annulus: outer/inner radii 38.1/33.1 mm, length 76.2 mm | Native radial, axial and azimuthal flow | The 152 mm downstream outer tube/core expansion and facility are omitted; outlet feedback differs. |
| 72 pairs of separate CH4/O2 mouths, opposed radial jets at 30° from the axis | Retains injection direction and pressure-dependent supply | No resolved channels/plenums, discharge coefficient, losses or reverse flow. GPU cold feed was 0.373 kg/s versus measured 0.269 kg/s. This remains an error, not an implicit calibration. |
| Reactive Euler, adiabatic slip walls | Cheapest compressible finite-rate chemistry prototype | No viscous boundary layers, wall cooling, molecular diffusion or LES mixing model. Mixing depends strongly on numerical diffusion. |
| 0.595 mm GPU spacing; graded CPU grid | Fits modest compute | Compact-model half-heat length is about 62 µm: the engine mesh does not resolve it. Halving all 3D spacings roughly multiplies cells by 8 and explicit steps by 2 (about 16× work before chemistry/AMR effects). |
| FFCMy-12: 12 reacting species + inert N2, 38 reactions | Much smaller native chemistry system than GRI-Mech | Not proven identical to the private Argonne/NETL skeletal mechanism. Low-temperature chemistry differs; neither model is experimental truth. |
| Initially fresh bottom layer; equilibrium products above it | Makes a finite startup experiment possible | Bypasses cold filling, spark development and actual startup history. Cool products and hot charge use separate equilibrium compositions. |

[Mundt’s thesis](../../../Mundt2023.pdf), injector drawing (printed p. 35, Fig. 2.10) supports **radial impingement**,
not steady tangential swirl. Tangential startup momentum is a separate choice.
The 2D source and paper dimensions informed the setup; their numerical validation
does not transfer to this new discretization.

## Incremental results and unresolved errors

- **Homogeneous chemistry passes:** over 0.5 µs, maximum temperature discrepancy
  against independent Cantera integration is 0.000912% for PeleC and 0.0710% for
  detonationFoam. Maximum absolute species discrepancies are 5.04e-6 and 2.04e-4.
  Native GPU/CPU integration took 4.87/16.59 seconds; these tiny controls do not
  predict engine speed. CHEMKIN round-trip forward-rate discrepancy is 4.6e-16.
- **Planar propagation fails:** matched 8 µm initialized profiles over 0.2 µs give
  approximately 3142 m/s (PeleC) and 3345 m/s (detonationFoam), versus compact-model
  CJ 2531 m/s. This short interval does not measure a long-time mean; startup,
  pulsation and discretization require investigation. PeleC's EOS/element checks
  pass in this control; its reaction distance does not. CPU local element error
  reaches 3.47e-6. Extending the buffer removed the boundary-margin ambiguity.
- **GPU annulus fails positivity:** worst logged mass fraction −8.19e-4 over 10 µs.
  Mass fractions sum to one, and pressure/density remain positive. Closing the
  injectors does not remove the error. Extra MOL coupling iterations and the
  tested Godunov option did not fix it. The standard embedded-cell cleanup is
  enabled and must not be mistaken for a conservation proof.
- **CPU annulus fails species closure:** upstream clipping leaves a maximum local
  species-sum error of **0.1254** after 1 µs. Worst pre-clipping species is −0.00275;
  cumulative reacting-species clipping adds 3.60e-7 kg. Nonnegative saved species
  therefore do not imply a valid solution. The instrumentation observes existing
  clipping and does not alter the solver update.
- **Model sensitivity matters:** at 1968 K and 22.984 MPa, constant-volume ignition
  to T+400 K is 156 ns with FFCMy-12 versus 109 ns with GRI-Mech. Similar CJ speeds
  hide this difference. At 1000 K/high pressure, GRI ignites within 2 ms while the
  compact model does not in that observation window.

## Comparison and next decision

Mundt Run 937 reports two waves at 15.84 kHz: about **126 µs per revolution**, or
approximately 1770 m/s at the mean radius. The GPU clip covers less than one tenth of that
period; neither run can reproduce wave count, refill equilibrium or averaged
performance. Argonne's [methane CONVERGE LES](https://doi.org/10.2514/6.2021-3642)
used millions of cells, finer local resolution and a pre-detonator; the
[NETL validation study](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf)
included more complete geometry and millisecond settling/averaging. Our
prototype is not a replication of either study.

**Keep PeleC as the GPU candidate; use detonationFoam as an independent diagnostic
until its closure error is resolved.** Next work should isolate species/energy
transport on a regular mesh and a nonreacting annulus, then repeat matched planar
controls over longer valid windows with mesh/time refinement. Only after those
pass should we spend compute on 1–5 ms circulation, calibrated supply and richer
geometry. [CDSFoam/DeepFlame](https://github.com/ChenHuangwei/CDSFoam-deepflame) is a relevant later alternative, not an installed or
verified replacement. Nineteen existing tests pass; native physical failures above
remain open regardless of unit-test success.

Native log files are stored verbatim with gzip compression; JSON checks and replay samples remain directly readable.
