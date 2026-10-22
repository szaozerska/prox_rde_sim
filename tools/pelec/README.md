# Pinned PeleC trial

One native GPU candidate, same-source CPU verification controls, installed
OpenFOAM/detonationFoam fallback. No fork of numerical physics. `source_lock.json`
pins the upstream source, recursive submodules and amd64 CUDA image digest.
The build records actual compiler/package versions and binary hash. Later
rebuilding apt packages may differ; reuse the cached successful image for runs.

First installation smoke, from the isolated 3D checkout:

```sh
.tooling/modal-venv/bin/modal run --profile prox --write-result /private/tmp/prox_rde_3d_pelec_smoke.json tools/pelec/modal_smoke.py
.tooling/modal-venv/bin/python tools/pelec/collect_result.py /private/tmp/prox_rde_3d_pelec_smoke.json runs3d/pelec_smoke_01
```

The first command builds on CPUs (16 cores, 64 GiB, one-hour build cap), then runs
one upstream nonreacting Sod test on one H100 (five-minute subprocess cap,
ten-minute function cap, zero retries). Image construction is a one-time
engineering step, not the routine two-hour CFD benchmark. Source automount is
disabled; only the explicit function and public upstream source are used.
No project engine geometry or private 2D work is uploaded.

The output includes checksummed native plotfiles, logs, final-time/exit checks and
build manifest. Collection preserves failures too; its successful exit means
artifact transport passed, not solver validation. Inspect `result.json` and
independent field checks before declaring the installation smoke passed.

PeleC has no native 1D build; physical 1D controls use transversely uniform thin
2D/3D grids, with transverse-invariance checks. The Sod build uses GammaLaw/Null
chemistry **only for nonreacting verification**. Engine chemistry uses a separate
finite-rate ideal-mixture build after source/thermo/propagation verification.


G0 passed on October 22: native CUDA execution and independent fields/budgets.
Evidence: [result](../../docs/verification/pelec_g0/result.json) and
[field checks](../../docs/verification/pelec_g0/field_checks.json). Upstream
`--describe` fails before runtime initialization; the regular run initializes
CUDA correctly and writes job_info. Use the saved build manifest and job_info.
This workaround does not modify numerical source. Inactive AMR inputs are removed
for the uniform-grid control; strict unused-input validation remains enabled.

Native analysis uses a separate `.tooling/analysis-venv` with
`analysis-requirements.txt`. Set `MPLCONFIGDIR` to an isolated writable cache:

```sh
MPLCONFIGDIR="$PWD/.tooling/matplotlib" .tooling/analysis-venv/bin/python tools/pelec/analyze_sod.py runs3d/pelec_smoke_02/run --time .002
```

The LiDryer upstream reactor has a tiny thermodynamic fit discontinuity at 1000 K.
The strict independent reference uses 1001 K, explicitly, without changing the
mechanism or energy tolerance. See the preserved investigation in the G0 evidence
folder; methane validation is separate.
