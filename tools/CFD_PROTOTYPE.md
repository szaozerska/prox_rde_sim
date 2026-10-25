# Run or replay the 3D CFD prototype

Read the [results and limitations](../docs/verification/3d_prototype_20261024/README.md)
first. These commands reproduce diagnostic cases that **fail physical acceptance**.
Do not use their output for engine design or label their motion sustained detonation.

Use this branch's existing isolated `.tooling/analysis-venv` (Cantera 3.2, NumPy,
SciPy, yt, Matplotlib/Pillow) and `.tooling/modal-venv` (Python 3.12, Modal 1.6.2).
Dependencies/source setup is in [PeleC](pelec/README.md), [OpenFOAM](openfoam/README.md)
and [Modal](modal/README.md). The pinned local upstream source trees are required
by the preparation/generation tools. Do not install into the original 2D environment.

PeleC uses one H100, eight host CPU cores and 32 GiB host RAM. The host CPUs manage
launches/I/O; this is not a second CPU CFD solve. detonationFoam runs separately
on up to 16 CPU cores. CPU image builds request 16 cores; no multi-GPU job is used.
Every remote solve has an explicit wall-time cap and zero automatic retries.
Use `--detach` so a local disconnect does not terminate the remote calculation.
Call IDs are saved next to result files; the artifacts include hashes and logs.

## Replay saved fields, no cloud cost

```sh
.tooling/analysis-venv/bin/python tools/pelec/animate_prototype.py \
  docs/verification/3d_prototype_20261024/pelec_annulus_10us runs3d/replay_gpu
.tooling/analysis-venv/bin/python tools/pelec/animate_prototype.py \
  docs/verification/3d_prototype_20261024/foam_annulus_1us runs3d/replay_cpu
```

The renderer works on stored native-field samples. It does not solve equations,
interpolate in time or move a prescribed front. CPU axial coordinates are graded;
plots retain their actual coordinates. Physical time is printed on every frame.
The native full-field archives remain in ignored `runs3d/*.json`; compact fields,
checks and execution manifests are committed with the report.

## Bounded native GPU diagnostic

```sh
.tooling/analysis-venv/bin/python tools/pelec/prepare_prototype.py \
  runs3d/new_gpu_case.json --mode annulus --n 128 --stop 1e-5 --dt 2e-8 --clean-species
.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/pelec/modal_prototype.py --case-file runs3d/new_gpu_case.json \
  --output runs3d/new_gpu.json --limit 900
.tooling/analysis-venv/bin/python tools/pelec/animate_prototype.py \
  runs3d/new_gpu_summary runs3d/new_gpu_visual
```

To repeat the homogeneous control, prepare `--mode reactor --stop 5e-7 --dt 5e-9`,
run the same launcher, unpack with `tools/cfd_artifacts.py RESULT NEW_DIRECTORY`,
and run `tools/pelec/analyze_prototype.py NEW_DIRECTORY/case` locally. The compact
mechanism's generated C++ is already committed. `tools/pelec/modal_generate.py`
regenerates it with pinned upstream CEPTR; no manually implemented reaction laws.

## Bounded native CPU diagnostic

```sh
.tooling/analysis-venv/bin/python tools/openfoam/prepare_compact.py runs3d/new_foam_base
.tooling/analysis-venv/bin/python tools/openfoam/prepare_annulus.py \
  runs3d/new_foam_base runs3d/new_foam_annulus --ntheta 576 --stop 1e-6 --dt 2e-8
.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/openfoam/modal_solver.py --case-dir runs3d/new_foam_annulus \
  --output runs3d/new_foam.json --limit 900 --ranks 16
.tooling/analysis-venv/bin/python tools/pelec/animate_prototype.py \
  runs3d/new_foam_summary runs3d/new_foam_visual
```

The base case itself is the 8-cell homogeneous control: launch it with `--ranks 1`,
unpack, then run `tools/openfoam/analyze_reactor.py NEW_DIRECTORY/case`.
Native coded inlet boundaries compile as an unprivileged container user.
The only upstream solver modification measures clipping before the existing
update; it does not normalize, repair or otherwise change that update.

The independent compact planar reference is prepared with
`tools/pelec/prepare_wave.py OUTPUT --mechanism rde3d/mechanisms/FFCMy12/mechanism.yaml
--length .004096 --shock .001024`; it requires the existing pinned SDToolbox setup.
`tools/openfoam/prepare_wave.py BASE REFERENCE OUTPUT` maps those conserved cell
averages into the CPU solver. The checked reference and both failed propagation
reports are committed. Do not treat the short-window speed as a converged mean.

Inputs and result destinations refuse overwrite. Review `checks.json` as well as
process completion. The upstream species cleanup/clipping is not a validation
method. The GPU and CPU meshes, integration methods and boundary implementations
differ, so comparing their raw times is not a hardware benchmark.
