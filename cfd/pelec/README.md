# Native PeleC 2D backend — first integration gate

Selected stack: **PeleC + PelePhysics + SUNDIALS/CVODE**. See the
[comparison and staged plan](../../docs/plans/pelec_2d_transition.md).
This is a separate reacting-flow solver, not a rate function inserted into the
old constant-gamma code. No prescribed reaction length or rate multiplier.

## Current scope

Explicitly 2D native executable, double precision, pinned upstream sources and
53-species grimech30. Only initialization is adapted; no numerical, chemistry or
thermodynamic source patches. An 8x8 periodic homogeneous CH4/O2 control runs with
hydrodynamics on: reacting, half-step and frozen cases use the same executable.
Initial state: 1800 K, 377916.972 Pa, phi=1.176; duration: 0.2 us. Chemical activity
is measured through species change; early endothermic chemistry can lower T.
This is not an ignition-delay validation, propagating wave or annular engine.

The pinned GRI inverse-temperature code extrapolates above 3000 K. No diagnostic
bound patch from the independent 3D work is copied. P1 stays below 2500 K.
Shock/product-range mechanism and EOS validation remains a P2 gate.

P1 passed on 2026-10-25. [Saved evidence and limitations](../../docs/verification/pelec_2d/README.md).

## Install and run

From the repository root, with Python 3.12:

```sh
python3.12 -m venv .tooling/pelec-venv
.tooling/pelec-venv/bin/python -m pip install --only-binary=:all: -r cfd/pelec/requirements.txt
PYTHONDONTWRITEBYTECODE=1 .tooling/pelec-venv/bin/modal run \
  --profile prox --env main cfd/pelec/modal_run.py \
  --output runs_cfd/pelec_p1_new
MPLCONFIGDIR=/tmp/rde-pelec-mpl .tooling/pelec-venv/bin/python \
  cfd/pelec/analyze.py runs_cfd/pelec_p1_new \
  --output runs_cfd/pelec_p1_new/analysis
```

The cbor2 pin avoids a Rust build on Intel macOS. The old `.venv` is unchanged.
No local Docker is needed. Modal uses the user's existing profile; authenticate
separately if this machine lacks one. First use builds a cached Linux executable
(16 build CPUs, 32 GiB, 3600 s cap). Execution is one 2-CPU/4-GiB container, no
GPU, no retries, 900 s function cap and 240 s per native subprocess. No persistent
deployment. GPU execution and one-hour engine performance are not yet verified.

Every run requires a new output directory; native failures save evidence and
return nonzero. Failed image builds retain Modal logs. Imports/help do not launch
jobs. Results include a function-call ID, checksummed raw archive and execution
status. If already extracted, analyze with `--collected` and a new output path.

## Analysis contract

Check archive integrity, source pins, mechanism hashes, actual 2D dimensions,
species names/order, finite fields, native error logs and completed time.
Compare all saved species/T/p with independent Cantera using the bundled YAML;
check density/energy/element conservation, species sum/negativity, uniformity,
frozen behavior and step sensitivity. Explicit tolerances in `analyze.py` apply
to this P1 control only. Report discrepancies; do not silently retune constants.

Exports: `report.json`, `reactor_check.png`, and SI NPZ fields (time, T, p, density,
energy density, species mass fractions and names). Native cgs converts to SI as
p and energy density x0.1, density x1000, length x0.01. Raw fields are preserved.

The old progress-based `plot.py --workflow` format is not used for multispecies
outputs. No invented progress, torque or boundary budgets. The new engine input,
wrapped GIF and full reporting adapter remain P3 work.

## Original solver / rollback

No reset required: all existing solver files/cases are unchanged from `73d4516`.
Use their existing commands and separate output directories:

```sh
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python run.py --preflight --case config.yaml
```

The transition plan was pushed as `1868f8b`. Adapter tests, from repository root:

```sh
.venv/bin/python -m unittest discover -s tests/cfd -v
```

Deliberate false-pass tests supplement actual native controls, not replace them.
