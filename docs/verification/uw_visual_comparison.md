# UW experimental propagation versus the current saved 2D startup

October 22, 2026. No new CFD or parameter changes. This comparison adds an
end-on view of the same 96-frame `radial_active` run and checks the proposed
pre-collision gas-convergence mechanism. RDE-001 remains open.

## What can actually be viewed

- [Our new end-on GIF](uw_visual_comparison/end_on.gif): pressure and reaction
  at z=0.752 mm, plus the axial integral of chemical heat release. All three
  use fixed scales. The last panel is **not predicted optical brightness**.
- [UW/Mundt published-snapshot flipbook](uw_visual_comparison/mundt_published_snapshots.gif):
  five original photographs from thesis Figure 2.3, with their actual timestamps.
  This is **not continuous high-speed video**. Equal screen holds are used for
  readability; the last frame explicitly jumps from 225 us to 0.75 s.
- [Original full figure image](uw_visual_comparison/mundt_fig2_3_original.png),
  extracted without contrast adjustment from the local user-provided thesis.
- [UW original startup video](https://www.youtube.com/watch?v=zXSsd7uXjt8) and
  [wave-dynamics video](https://www.youtube.com/watch?v=gEYFy3qRNdo), linked by
  [the university's announcement](https://www.washington.edu/news/2020/02/18/simple-fuel-efficient-rocket-engine/).
  Its caption identifies ignition at 11 s of playback. The video players could
  not be fetched here, so no claim is made to have watched or converted them.

The 2020 UW/Koch videos and Mundt's 2023 thesis are distinct experimental records.
The thesis's Figure 2.3 is a 76 mm-engine example, not explicitly Run 937. Run 937
is documented separately in Figures 3.4–3.7 and Table 3-2. Neither animation is
synchronized to the other: time origins, sampling and observables differ.

## Detailed visual and physical differences

| Feature | UW experiments | Current simulation |
|---|---|---|
| Viewing direction | Camera looks from the exhaust end along the axis, collapsing axial depth into a ring-shaped image. | Earlier GIFs showed the cylindrical side or unwrapped x-z plane. The new GIF uses end-on orientation. Upward movement in the old view is axial motion, which the experimental camera largely projects out. |
| Quantity displayed | Light emitted by the reacting/hot gases, affected by exposure and optical integration. | Pressure, reaction rate, or chemical power. No optical emission, absorption or camera response model; brightness cannot be matched numerically. |
| Startup | A localized ignition expands before a rotating mode develops. Mundt Fig.2.3 shows broad luminosity at 225 us. | A 10 mm hot burned patch in a prescribed 3.8 mm fresh layer, with zero initial velocity and an adjacent product strip, generates an expanding blast in both directions. |
| Established rotation | Mundt Run 937 has two co-rotating waves; late x-t tracks repeat with common slope. Other cases can have counter waves and mode changes. | Two prominent opposing pressure paths weaken and interact. Persistent co-rotating shock/reaction coupling through repeated fresh-mixture returns is not demonstrated. |
| Gas versus wave motion | Propellant is supplied and products exhaust mainly along the axis; the combustion front travels circumferentially through the mixture. | Axial and circumferential gas velocities both evolve. A pressure front's position is not a tagged gas particle. Zero inlet swirl does not force the front to move only axially. |
| Where combustion persists | Established detonation has heat release supporting its leading compression, with additional burning possible elsewhere. | Strong near-injector reaction fades while pressure disturbances remain. Higher in the chamber, an extended fresh/product interface keeps reacting; integrated heat is not proof of a rotating detonation. |
| Refilling | Continuous separate gaseous feeds, with local wave-induced interruptions and mixing/recovery. | Continuous equivalent premixed plenum. The saved budget confirms ongoing supply and increasing unreacted inventory. This is not a globally exhausted fuel charge. |
| Injector representation | Mundt uses discrete impinging jets, 30 degrees to the axis and meeting 2.16 mm above the face. | Uniform premixed axial boundary, no resolved separate jets or finite mixing/recovery dynamics; that 30-degree value is not imposed as azimuthal swirl. |
| Chemistry and mesh | Physical methane/oxygen kinetics and mixing operate at their natural scales. | The displayed case still uses the original one-step surrogate with a 1 mm half-reaction length on a nominal 0.5 mm mesh. The separate detailed-chemistry reference gives about 0.0395 mm at the reference state; matching CJ speed does not validate reaction timing. |
| Structure visibility | End-on luminosity identifies traveling bright regions; it does not by itself resolve every oblique shock or product slip line. | Our side-view diagnostics expose pressure/density gradients and contacts, but those candidates do not become the canonical sustained structure just because they are visible. |
| Time covered | UW's 2020 announcement describes 0.5 s recordings; Mundt Run 937 burns 0.696 s. | 0.000189394 s of startup, with 2 us saved cadence. This is only 1.5 revolutions at Run 937's reference rate and cannot exclude later reinitiation. |

Mundt references: printed pp.13, 21, 26, 34–35, 42–43, 47–52 and 171–172 of
[Mundt2023.pdf](../../Mundt2023.pdf). The established-mode comparison is to these
published observations, not an invented reconstruction of the inaccessible videos.

## Can the opposing fronts push the gas together and slow each other first?

**Yes, pre-collision fluid coupling is physically possible.** These cases use
gaseous methane/oxygen, not liquids. Compression and opposing gas velocities
can alter the mixture state, injector response and laboratory-frame wave speed.
For a front moving in a chosen positive direction, its lab speed is the gas
velocity just ahead plus its propagation speed relative to that gas. An adverse
incoming velocity can lower the lab speed, while compression/heating can change
the chemical propagation speed. There is no universal slowdown rule.

The previous timing argument alone did **not** exclude indirect interactions
before the visible fronts meet. A gas is compressible, and disturbances travel
at finite speeds; the whole fresh-gas segment is not displaced instantaneously
like a rigid plug. We therefore inspected saved gas velocity rather than inferring
it from a pressure movie.

[Gas velocity and pressure comparison](uw_visual_comparison/gas_motion.png):

| Time | Far-side region x=110–160 mm |
|---|---|
| 20 us | Circumferential velocity is zero in the saved fields at every height. |
| 40 us | Maximum absolute circumferential velocity across **all heights** is 5.23e-12 m/s, effectively roundoff. At z=0.752 mm, pressure is spatially uniform across this region at 422.089 kPa. |
| 80 us | Substantial flow has reached this region; the all-height maximum is about 405 m/s. |
| 110 us | Opposing near-injector velocities of about -43 to +50 m/s occur across the region, during the prominent pressure interaction. |

At 40 us the two lower-ring pressure peaks are at x=69.807 and 205.417 mm.
Eight millimetres ahead of them, gas velocities are only +0.270 and -0.093 m/s,
respectively, with temperatures about 298 K and progress about 0.000163.
At the peaks themselves gas velocities are about +269 and -233 m/s: flow is
being driven locally by the disturbances, not throughout the intervening gas.
The near-injector reaction maximum is already only 10.8 /s at this time.

This does not support early compression of the entire intervening gas column as
the cause of the 40 us reaction loss. It **does not exclude every indirect route**:
local fresh/product interactions, axial expansion, injector coupling and later
wave encounters remain relevant. The sample region was selected to lie between
the early fronts and include their subsequent far-side interaction, not to span
all unburned gas or substitute for a characteristic-path analysis.

Koch et al.'s [primary paper](https://arxiv.org/html/1908.03116v3), Section V.1,
explicitly discusses interaction mediated by the injector response and the
replenished medium. Its model treats co-rotating-wave dynamics qualitatively;
it is not validation of our hot-patch start or a quantitative counterflow model.
That is a reason to retain indirect coupling as a hypothesis, not to claim the
current central-region check rules it out globally.

## What the new end-on GIF means

Each circular plot has the real inner/outer radius but no resolved radial
structure; the scalar is constant across the displayed radial gap. The left
panel shows lower-ring pressure, the middle lower-ring reaction rate. The right
panel uses

`H(theta) = sum_z(rho * q * reaction_rate * dz)` in W/m².

This is chemical power per cross-sectional area. It includes off-front burning
and excludes any optical radiation model. Hot, already burned gas can emit light
while its instantaneous chemical heat release is zero, so the initial and later
optical images cannot be predicted from H alone. A bright, nearly complete ring
in H does not mean a detonation front is completing a circuit.

The gif has 96 frames and 15.5 s display duration, no looping, and includes every
saved timestamp. The initial 14 s are proportional to physical time; the final
frame is held for 1.5 s. Scale limits do not change frame by frame.

## Checks and reproduction

- All 96 source-frame hashes and input/summary/history provenance match the
  previously published flow-structure GIF manifest.
- The axial projection integrates back to the full volumetric chemical power:
  maximum relative discrepancy 5.06e-16 across all saved frames.
- Encoded frame count, per-frame durations and absence of looping were checked.
- Raw-array checks independently verified the central-region velocities and the
  samples ahead of each early pressure peak. Arrow plots use actual gas components,
  equal spatial aspect ratio, a fixed scale and full-range velocity axes.
- Initial review found a clipped velocity curve in the draft; the common axis
  range was widened before publication. Representative early, interaction and
  final frames and the source photographs were visually checked.
- The five-source-snapshot GIF has explicit time jumps and retains the original
  image pixels without contrast adjustment or interpolated motion. Its extraction
  rectangles, times and PDF checksum are in its manifest.

No production solver change, new CFD campaign or new full-suite result is claimed.
The scripts and generated manifests make this a reproducible saved-data review.

From the repository root:

```sh
.venv/bin/python docs/verification/end_on_comparison.py \
  --run rde_sim_starter/runs/radial_active --out reports/new_end_on
# Requires pypdf and Pillow (available in the bundled PDF Python runtime):
python docs/verification/mundt_snapshot_flipbook.py \
  --pdf Mundt2023.pdf --out reports/new_mundt_snapshots
```
