# Native engine preview workflow

PeleC + PelePhysics FFCM1_Red + CVODE, with a finite tangential formed-wave
initializer, periodic circumference, homogenized premixed feed and an approximate
pressure outlet. The original custom solver is unchanged. The wrapped cylinder
is a coordinate mapping of the 2D solution, not resolved radial/3D flow.

**Status:** the native adapter builds and its uniform/cold-feed controls pass
independent saved-field checks. The reacting engine launch is still failing;
there is no accepted 1 ms engine movie yet. See the
[measured engine evidence](../../../docs/verification/pelec_2d_engine/README.md)
and [open propagation qualification](../../../docs/verification/pelec_2d_propagation/README.md).

## Commands

Use the isolated `.tooling/pelec-venv` environment. `prepare.py` takes the
independent reference directory, exact pinned mechanism YAML, case ID and a new
output directory. It produces conservative CGS launch data and a JSON case.

```sh
python cfd/pelec/engine/prepare.py docs/verification/pelec_2d_propagation \
  path/to/pinned/mechanism.yaml run937_76fi5 runs_cfd/prepared_run937
modal run --profile prox --env main cfd/pelec/engine/run_modal.py \
  --case-file runs_cfd/prepared_run937/case.json \
  --profile-file runs_cfd/prepared_run937/profile.dat \
  --output runs_cfd/new_unique_run --stop .001 --wall-limit 12600
```

Runs retain full native plots, checkpoints and logs in Modal volume
`prox-rde-2d-engine/<run-id>`. A checksum-tagged compact archive is downloaded
locally even after a solver failure. Failed validity checks prohibit movie export.
A nonzero exit, invalid fields, missing frames or insufficient final time cannot
be reported as a completed simulation.

`visualize.py` takes the exported SI NPZ, output directory and display title;
see `--help`. It renders fixed-scale pressure, native heat release, numerical
schlieren and vorticity, velocity arrows and simulation times. It does not infer
or label a slip line merely from a gradient. Inspect the saved first/last PNGs
alongside both GIFs. Actual frame times are recorded in the movie manifest.

Input arrays: `time_s`, uniform cell centers `x_m`, `y_m`, and (time,x,y) arrays
`pressure_Pa`, `density_kg_m3`, `heat_release_W_m3`, `u_mps`, `v_mps`. Supply
actual native fields; do not manufacture a traveling wave or pad the time window.

`cases.json` contains Run 937 and controlled geometry variants, not invented
experimental operating points. The preview mesh is intentionally coarse and
cannot establish mesh-independent detonation sustainment.
