# Flow-structure animations: shocks, interfaces and shear

These movies replace the default final-report GIF view with a numerical-schlieren
and flow-structure view. They use the existing `radial_active` run, all 96 saved
frames from 0 to 189.393939 us. **This is the original hot-patch startup with
zero initial circumferential and axial velocity, not the formed traveling-wave
initializer.** No new CFD or parameter changes were made.

- [Unwrapped flow structures](flow_structure_gifs/unwrapped.gif).
- [Wrapped flow structures](flow_structure_gifs/wrapped.gif).
- [20 us annotated snapshot](flow_structure_gifs/unwrapped_010.png).
- [Saved definitions, gates, frame metrics and hashes](flow_structure_gifs/manifest.json).

## Paper reference and interpretation

We inspected complete printed pages 1 and 13 (PDF pages 17 and 29) of
[Mundt2023.pdf](../../Mundt2023.pdf), including Figures 1.1 and 1.10. Figure 1.1
shows a characteristic cylindrical RDE design and flow visualization, reproduced
from another source. It is not the experimental Run 937 validation field.
Figure 1.10 labels A: detonation, B: oblique shock, C: slip line, D: secondary
shock, E: mixing region, F: blocked injectors, G: fresh reactants.

**C separates new and old products. It is not the fresh/reactant-product boundary.**
The saved one-step progress variable distinguishes reaction progress, not the age
or origin of fully burned products. Therefore the cyan progress contour cannot
be labeled C, nor can this postprocessor positively identify C from an age tracer
that does not exist. Shear/contact diagnostics expose possible structures for
inspection; they do not prove a material slip surface or its identity.

A numerical-schlieren view reveals gradients that a pressure color field can
obscure. This follows the general density-gradient visualization approach described
in [NASA's CFD visualization report](https://www.nas.nasa.gov/assets/nas/pdf/techreports/1999/nas-99-002.pdf)
and its [VULCAN application examples](https://vulcan-cfd.larc.nasa.gov/WebPage/vulcan_apps.html).
It is a computed gradient visualization, not an optical schlieren experiment.

## What each color actually means

| Display | Saved-field definition | Interpretation limit |
|---|---|---|
| Black/gray background | Magnitude of the density gradient | Both shocks and contacts can make density edges. |
| Red | Pressure-gradient and compressive-velocity gates both pass | Compression-front candidate, not independently verified shock jump conditions; no automatic B/D identity. |
| Orange | Volumetric heat release exceeds 5% of the global saved-frame maximum | Strong reaction, not a detonation label; weaker reaction still exists below this display threshold. |
| Cyan | Cells adjoining progress=0.5 | Fresh/product transition, not the new/old-product slip line C. |
| Magenta | Product-dominated cell with entropy gradient and shear, but small pressure gradient | Possible product shear/contact structure; can include diffuse interface effects. No validated slip-line classifier. |
| Pale blue | Progress < 0.1 | Mostly unreacted mixture; not proof of a detonable thermodynamic state. |
| Green/black injector strip or ring | Instantaneous face-adjacent pressure below/at-or-above plenum pressure | Open/blocked branch of the actual model; not a measured jet or time-integrated flux. |

The unwrapped movie additionally shows signed vorticity and velocity divergence
with fixed symmetric-log scales: vorticity exposes shear, negative divergence
compression, and positive divergence expansion. These are independent fields,
so an overlay can be checked against the raw diagnostic instead of being accepted
as a named wave. No front-following camera, imposed propagation speed, decorative
swirls, or idealized detonation geometry is inserted.

The cylindrical movie wraps the same composite onto the mean-radius surface,
with stationary opposite cameras. Its display faces average RGB blocks to bound
rendering cost; use the native-mesh unwrapped movie to inspect exact relative
positions. Wrapped color overlap is not a shock/reaction-coupling criterion.

## Operators and display gates

For uniform spacings dx,dz and h=min(dx,dz):

- x derivatives are centered and periodic; z derivatives are centered internally
  and one-sided at the two endpoint rows. No periodic wrapping in the axial direction.
- Density display intensity: `1-exp(-4*|grad rho|/gscale)`. `gscale` is the largest
  per-frame 99th percentile over the requested window. It stays fixed for every frame.
- Pressure sensor `Jp=h*|grad ln p|`; compression sensor
  `C=max(-div u,0)*h/sqrt(gamma*p/rho)`.
- Red: `Jp >= 0.08` and `C >= 0.04`.
- Entropy proxy `S=ln(p/p1)-gamma*ln(rho/rho1)`, proportional to entropy difference
  in the current constant-gamma gas model. `Js=h*|grad S|`.
- Vorticity `omega=du_z/dx-du_theta/dz`.
- Magenta: progress >=0.9, Jp <0.025, Js >=0.04,
  and `abs(omega)*h/sound_speed >=0.02`.
- Heat release `rho*q*reaction_rate`; its 5% threshold is fixed over time.

These explicit, grid-dependent thresholds are **visualization gates**. They are
not fitted to the experiment and not sufficient conditions for shocks, slip lines
or detonations. Smooth compression, baroclinic shear and numerical mixing can
contribute to the displayed signals. No Rankine-Hugoniot test or tracked material
surface is claimed. Lowering a gate does not turn the case into a sustained wave.

## What the actual case shows

At 20 us, the new view exposes curved startup compression fronts and reflected/
interacting structures much more clearly. It also exposes their spatial relation
to the thin fresh layer and reaction near the lower interface. It does not reveal
a verified steady version of the canonical A–G structure. Late fields retain
interface burning and pressure disturbances, as already documented in RDE-001.
The original initialization is a hot patch, not a fully established rotating wave.
An animation cannot supply the stable shock/slip-line geometry missing from the
computed solution. We retain the original failure rather than drawing the paper's
idealized geometry over it.

## Reproduction and checks

From `rde_sim_starter`, with the local saved run available:

```sh
../.venv/bin/python flow_structure.py --run runs/radial_active --out ../reports/flow_structures
```

Optional `--start-us`, `--end-us`, `--seconds` select the physical window and
playback duration. Final static `plot.py --workflow` reports now use this view;
`animate.py` retains the previous pressure/reaction-panel exporter. Live previews
remain lightweight. Both GIFs keep all saved timestamps, proportional intervals,
14 seconds playback plus a 1.5 second final hold, with no loop extension.

Analytical controls cover periodic gradients including the seam, known constant
vorticity/divergence, a pure contact that must not appear as a compressive shock,
a shear contact, reversed compression/expansion, the inlet pressure branch, and
progress contours without axial wrapping. Small native-run tests cover both GIFs,
encoded timings, failure markers, native-file immutability, refusal of native output
paths and no solver calls. Workflow integration and import isolation are also checked.

Visual review of the initial draft found legend and colorbar-label overlaps;
these were corrected before publication. No physics changes followed from these
presentation checks. Tests and final artifact verification are recorded below.

Affected verification: **12 tests passed**, zero skips, 159.332 s, comprising
the five new operator/export tests, six workflow checks, and import isolation.
[Test log](flow_structure_tests.txt). The prior full 137-test acceptance result
belongs to the preceding increment; this change does not claim a new full-suite
run. The solver and physical configuration were not modified.

Final artifact check: both GIFs contain 96 frames at 1170 x 792 pixels with
15.5 s total display time and no loop extension. First, early (20 us), middle
and final views were inspected. All 96 source-frame hashes and committed native
input/summary/history hashes remain unchanged; the renderer matches its manifest.

## Directional ignition versus angled injection

The user correctly identified that the displayed startup is an expanding blast,
not an already established circumferential detonation. The actual case uses
`initialization.kind: ignition`, u_theta=0 and u_z=0. A 20 mm product strip behind
the 10 mm hot patch gives a thermal/composition asymmetry, but does not supply a
traveling wave's consistent pressure, momentum and reaction profile. Disturbances
can spread axially and in both circumferential directions. The x direction is
circumferential and periodic; z is axial. The coordinate mapping is not reversed.

The inlet is explicitly a reduced premixed axial flux: injected theta momentum
is zero (`physics.injector_flux`, F[1]=0). The solver subsequently evolves theta
momentum; zero injected swirl does not prohibit circumferential wave propagation.
A detonation propagates through the reactants and need not be advected at the gas
injection velocity. NASA describes the annular detonation as propagating
[transverse to the flow direction](https://techport.nasa.gov/projects/116281).

For this follow-up we re-read Mundt printed pp.26,34-35,37 and inspected Figure
2.10. The paper specifies impinging methane/oxygen holes inclined 30 degrees
from the engine axis, meeting 2.16 mm above the face. This is not a stated
30-degree azimuthal swirl angle and supplies no basis to add arbitrary net theta
momentum. Ignition uses a separate pre-detonator through a radial instrument port;
for 76-FI-5 its location is z=73 mm, clocking 210 degrees. Our inlet and hot patch
are approximations, not a reconstruction of those jets or that ignition system.

A directional initializer is already implemented as `initialization.kind: formed`:
it places a finite +theta ZND charge with consistent laboratory-frame momentum
and conservative energy/progress. [C6a](c6a_functional_pipeline.md) records its
2 us engine benchmark; that benchmark is too short to establish sustained
rotation. Isolated formed-wave controls also exist, and the original-chemistry
thin-layer case lost coupling even with a directional formed start. Therefore
startup is an important hypothesis, but not an established sole cause or cure.

The radial-on/off experiment intentionally retained the original ignition to
isolate the radial intervention. These movies visualize that controlled baseline;
they do not imply that the formed initializer is missing. A future startup-only
comparison must hold chemistry, mesh, feed and boundaries fixed and document its
changed initial inventories. The existing C6a named case changes chemistry and
mesh as well as startup, so simply comparing its movie to this one would not
isolate directionality. No new engine study or unphysical swirl source is launched
in response to this clarification.
