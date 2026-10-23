# Watch or rerun the current 3D-branch wave control

Work only in `/Users/sgfx/Desktop/Projects/prox_rde_sim_3d`, branch
`3d-modelling`. The original checkout is the other session's 2D workspace.

The available movie is a **planar initialized detonation control on a thin 3D
mesh**, evolved by native PeleC on an H100. It is not the annular engine case.
The propagation check currently fails: the fine-grid wave is about 18% faster
than the independent CJ reference, and its reaction structure is incorrect.
Motion alone does not establish sustained detonation. See the
[G2b investigation](../../docs/verification/pelec_g2b/README.md).

## Watch the saved result now — no cloud compute

Open the [wave propagation GIF](../../docs/verification/pelec_g2b/animations/wave_propagation.gif)
and [reaction-zone GIF](../../docs/verification/pelec_g2b/animations/reaction_structure.gif).
They loop automatically in a browser or GIF-capable viewer.

The first movie shows pressure and temperature moving right. The dashed line
moves at the independently calculated CJ speed. Strip height is only a display
choice: these are transverse means of a uniform planar control, not an annulus.
The second movie follows the measured pressure front and compares native pressure,
temperature and formation-enthalpy heat fraction with the independent ZND profile.
The wave starts already formed; there is no continuing ignition source.

Both movies use all 21 native snapshots over **0–0.2 microseconds**, with fixed
axes/colour scales and no interpolated frames. Playback is slowed for inspection;
physical time is printed on each frame. Numerical cells are displayed without
smoothing. The [manifest](../../docs/verification/pelec_g2b/animations/manifest.json)
records source checksums, snapshot times and the failed validation status.

To regenerate locally from the existing saved data (roughly tens of seconds;
choose a new output name each time):

```sh
cd /Users/sgfx/Desktop/Projects/prox_rde_sim_3d
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$PWD/.tooling/matplotlib" \
  .tooling/analysis-venv/bin/python tools/pelec/animate_wave.py \
  runs3d/formed_wave_fine01/wave runs3d/formed_wave_reference_03 \
  runs3d/wave_movie_replay_01
```

It creates two GIFs, two final-frame PNGs and a manifest. It refuses to overwrite
an existing output directory. Substitute `runs3d/formed_wave_coarse01/wave` to
view the saved 8-micrometre control instead.

## Launch a fresh native GPU control

**Modal is already installed and authenticated on this machine:** profile and
workspace `prox`, environment `main`. No new plugin, account connection or local
GPU is required. These commands use the existing isolated environments and
prepared reference files. No import or help command starts a simulation.

The command below requests **one H100, 8 CPU cores and 16 GiB host RAM**. Keep the
terminal open until it reports that the artifacts were saved. In the existing
measurements, native solver time was 5.5 minutes for the 8-micrometre control,
7.6 minutes with its timestep halved, and 9.0 minutes for the 4-micrometre control
shown in the GIFs. Queueing, any image rebuild, download and local analysis add
time. These are measurements of the short control, not an engine-runtime estimate.

From the same checkout, run the fine control shown in the movies:

```sh
cd /Users/sgfx/Desktop/Projects/prox_rde_sim_3d
wave_run="runs3d/wave_$(date +%Y%m%d_%H%M%S)"
PYTHONDONTWRITEBYTECODE=1 .tooling/modal-venv/bin/modal run \
  --profile prox --env main tools/pelec/modal_wave.py \
  --case-file runs3d/formed_wave_reference_03/case_n512.json \
  --profile-file runs3d/formed_wave_reference_03/profile_n512.dat \
  --output "${wave_run}.json" \
  --stop-time 2e-7 --dt 1e-10 --reconstruction-order 1
```

The job is capped at one GPU container with no retries; the native solver has a
15-minute timeout. This launches a finite job, not a permanent deployment. The
local runner saves a function-call ID alongside the result for recovery. Do not
increase the physical time or substitute engine geometry: the current control
has unresolved propagation/boundary checks.

After the result is saved, use the **same terminal** (which retains `wave_run`):

```sh
PYTHONDONTWRITEBYTECODE=1 .tooling/modal-venv/bin/python \
  tools/pelec/collect_result.py "${wave_run}.json" "$wave_run"
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$PWD/.tooling/matplotlib" \
  .tooling/analysis-venv/bin/python tools/pelec/analyze_wave.py \
  "$wave_run/wave" runs3d/formed_wave_reference_03
```

Collection checks the artifact checksum. Analysis checks native fields and
writes `wave_checks.json` and `wave_profiles.npz`. For the current fine control,
analysis returns a nonzero status because a conservative boundary-margin check
fails; the speed and reaction-distance checks also fail in the report. Inspect
that report; a solver completion message is not a physical pass. A nonzero
analysis status is not by itself a Modal installation failure.

If analysis produced both files, render the failed result for diagnosis:

```sh
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$PWD/.tooling/matplotlib" \
  .tooling/analysis-venv/bin/python tools/pelec/animate_wave.py \
  "$wave_run/wave" runs3d/formed_wave_reference_03 "$wave_run/movies"
```

No new simulation is needed to watch the committed GIFs. The large native raw
runs, prepared references and virtual environments are local/ignored; a fresh
clone on another computer needs the setup and reference preparation described in
[the native workflow](README.md) and [G2b evidence](../../docs/verification/pelec_g2b/README.md).
