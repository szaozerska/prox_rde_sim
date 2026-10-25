# Reproduce the diagnostic campaign

Use the isolated Python/Modal environments described in [CFD_PROTOTYPE.md](../../../tools/CFD_PROTOTYPE.md). The existing prepared inputs are `runs3d/foam_compact_reactor_v6` and `runs3d/compact_wave_reference`; the planar input template is committed in `tools/pelec/planar_template.json`; they use the committed FFCMy12 mechanism and pinned upstream sources. New campaigns need a fresh destination. No command below changes the original 2D checkout.

If the prepared baseline directories are absent, create them first with `tools/openfoam/prepare_compact.py runs3d/foam_compact_reactor_v6` and `tools/pelec/prepare_wave.py runs3d/compact_wave_reference --mechanism rde3d/mechanisms/FFCMy12/mechanism.yaml --length .004096 --shock .001024`, using the analysis Python.

```sh
.tooling/analysis-venv/bin/python tools/prepare_failure_matrix.py runs3d/new_diagnostics
.tooling/analysis-venv/bin/python tools/pelec/extend_znd_reference.py \
  runs3d/compact_wave_reference runs3d/new_diagnostics/long_reference
.tooling/analysis-venv/bin/python tools/pelec/prepare_wave.py \
  runs3d/new_diagnostics/short_profiles --reference runs3d/compact_wave_reference \
  --mechanism rde3d/mechanisms/FFCMy12/mechanism.yaml \
  --length .004096 --shock .001024 --nx 256 512 1024 2048
.tooling/analysis-venv/bin/python tools/pelec/prepare_wave.py \
  runs3d/new_diagnostics/long_profiles --reference runs3d/new_diagnostics/long_reference \
  --mechanism rde3d/mechanisms/FFCMy12/mechanism.yaml \
  --length .032768 --shock .008192 --nx 2048 4096
.tooling/analysis-venv/bin/python tools/prepare_planar_matrix.py runs3d/new_diagnostics
.tooling/analysis-venv/bin/python tools/prepare_followup_controls.py runs3d/new_diagnostics
.tooling/analysis-venv/bin/python tools/prepare_tight_chem_control.py runs3d/new_diagnostics
```

Run each backend's batches **sequentially** to retain one H100 and one 16-core CPU worker. GPU and CPU backends may run alongside each other. Each case has a wall-time cap; no automatic retries or multi-GPU allocation. The CPU repair build uses eight CPUs before its run batch.

```sh
.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/pelec/modal_diagnostics.py::batch --manifest runs3d/new_diagnostics/gpu_manifest.json
.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/pelec/modal_diagnostics.py::batch --manifest runs3d/new_diagnostics/gpu_planar_manifest.json

.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/openfoam/modal_diagnostics.py::batch --manifest runs3d/new_diagnostics/cpu_manifest.json
.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/openfoam/modal_diagnostics.py::batch --manifest runs3d/new_diagnostics/cpu_planar_manifest.json
.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/openfoam/modal_flux_diagnostics.py::batch --manifest runs3d/new_diagnostics/cpu_flux_manifest.json
.tooling/modal-venv/bin/modal run --detach --profile prox --env main \
  tools/openfoam/modal_flux_diagnostics.py::batch --manifest runs3d/new_diagnostics/cpu_flux_tight_manifest.json
```

The last two launches use an explicitly patched executable; the other CPU batches retain upstream numerics. Patch/build hashes are saved in the artifact. It changes the species-convection constructor from `phi` to `rhoPhi`; it does not renormalize composition or add chemistry.

Annular analysis runs in each native container. Analyze the planar and material-contact outputs locally, then collect compact evidence:

```sh
.tooling/analysis-venv/bin/python tools/analyze_diagnostic_batch.py runs3d/new_diagnostics/gpu_planar_manifest.json gpu
.tooling/analysis-venv/bin/python tools/analyze_diagnostic_batch.py runs3d/new_diagnostics/cpu_planar_manifest.json cpu
.tooling/analysis-venv/bin/python tools/analyze_diagnostic_batch.py runs3d/new_diagnostics/cpu_flux_manifest.json cpu
.tooling/analysis-venv/bin/python tools/collect_diagnostic_evidence.py runs3d/new_diagnostics runs3d/new_diagnostic_evidence
```

`index.json` links each compact result to its local native archive and SHA-256. Solver logs are losslessly compressed. Large field archives remain in ignored `runs3d/`. A successful process exit is reported separately from field checks and physical validation. The first-order upwind control has additional numerical diffusion and is not an accuracy upgrade by itself.
