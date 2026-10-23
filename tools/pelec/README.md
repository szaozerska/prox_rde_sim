# Pinned PeleC trial

For viewing the saved wave GIFs and exact launch/replay commands on this machine,
start with the [quickstart](QUICKSTART.md).

One native GPU candidate, same-source CPU verification controls, installed
OpenFOAM/detonationFoam fallback. Use upstream numerical kernels; the experimental GRI inverse-bound overlay is explicitly recorded and is limited to numerical controls. `source_lock.json`
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


G1 shock convergence and CPU/GPU equivalence passed. **G1a closed-reactor numerical controls now pass for the pinned generated LiDryer model.**
See [the failure investigation](../../docs/verification/pelec_g1/README.md).
The controls runner rejects solver-error logs independently of native exit/final
time, since the pinned CPU per-cell CVODE path can ignore an integration failure.

```sh
.tooling/modal-venv/bin/modal run --profile prox --write-result /private/tmp/prox_rde_3d_controls.json tools/pelec/modal_controls.py --suite shock
.tooling/modal-venv/bin/python tools/pelec/collect_result.py /private/tmp/prox_rde_3d_controls.json runs3d/new_controls
MPLCONFIGDIR="$PWD/.tooling/matplotlib" .tooling/analysis-venv/bin/python tools/pelec/analyze_shock_controls.py runs3d/new_controls/controls
```

Chemistry controls require explicit `--suite chem`; `--rtol`, `--atol`,
`--backend-filter`, `--chem-dt`, `--chem-order` and the CPU-only `--linear-solver` permit discriminating small
tests. Defaults are the verified order-5, rtol=1e-11/atol=1e-22 reactor controls; they are not automatically accepted engine tolerances.
Every subprocess has a 90-second cap; the batch stops at first completion/error
failure. These are not production engine cases. The shared control allocation
reserves one H100 even for a CPU case filter.

`compare_reactor_history.py RUN MECHANISM --output REPORT` is the cheap all-step
temperature comparison. `analyze_reactor.py RUN MECHANISM` additionally checks
native fields, species/element budgets and independent energy. The optional
`--native-constants` mode is a separately labelled LiDryer diagnostic derived from
the generated header; it does not replace or overwrite nominal YAML comparisons.
`modal_rates.py` evaluates the actual compiled native thermodynamics and source
rates across public fresh/reacting mixtures on two CPUs.

`PELEC_STRICT_EOS=1` selects a separate cached A/B build using the upstream
`CONVERGENCE` macro. It changes EOS inversion tolerance to 1e-12 K and its iteration cap to 5000, records new
binary hashes and does not change rate constants or numerical source. This option
failed to cure the reactor step-limit error and is retained only as a rejected diagnostic. The default cached build remains
available; full reacting throughput and the one-to-two-hour engine target remain
unmeasured.


Methane preflight and its unresolved model limits are in
[the G2 evidence](../../docs/verification/pelec_g2/README.md).
`methane_preflight.py NEW_OUTPUT --znd` reuses the inherited physical references.
`modal_thermo_audit.py` probes compiled operators; its explicit
`--gri-inverse-bound 5000` option does not extend thermodynamic fit validity.
`native_generated_reference.py` preserves the LiDryer diagnostic and adds only
the pinned GRI mechanism after a direct source-rate audit; nominal comparisons
remain separate. `modal_methane.py` uses a capped native reactor and explicit
state metadata, never an engine run. No imports launch jobs.
