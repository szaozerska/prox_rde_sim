# CAD extraction verification

Verified on 2026-10-22 with Python 3.12, Gmsh 4.15.2 / OpenCASCADE and the
repository's existing NumPy/PyYAML/Matplotlib stack. CAD dependencies were installed
in an isolated temporary environment; the shared solver environment was unchanged.
The final reader and tests ran against the locally downloaded, hash-checked archive.

## Results

- **11 CAD tests passed**, including the actual archived core/sleeve/injector
  regression, STEP imports with embedded millimetre/metre/inch units, transformed
  axes, split-face deduplication, changed annulus dimensions and counts, rejection
  of stale hashes/reader versions, eccentric geometry, noncylindrical walls,
  unaligned injector faces, undeclared units, and unsupported formats. Export
  checks preserve the base operating/chemistry model and reject diagnostics beyond
  the reduced domain. See [test log](cad_tests.log).
- **4 existing contract tests passed**, including saved-input/field compatibility
  and invalid-geometry rejection. The existing runner fixture advances a tiny
  nonreactive toy case. See [contract log](contract_tests.log).
- **Both generated cases passed native solver preflight**, including initialization:
  [paper contract](mundt_review_audit/preflight.paper.json),
  [CAD contract](mundt_review_audit/preflight.cad.json). No Run 937 time integration
  or sustained-detonation study was performed for this change.
- The paper-only CLI successfully exported a case using the normal solver Python
  environment, which has no optional Gmsh dependency.
- The generated geometric preview and thesis Tables 2-1, 2-2 and 3-2, Figure 2.4,
  injector-design text and relevant source drawings were visually checked. The
  drawing/reconstruction uncertainty remains explicitly recorded in the manifest.

## Repeat the checks

From the repository root, after the optional CAD environment and archive are ready:

```sh
RDE_CAD_SOURCE_DIR=.cad-inputs/rde-mundt-rfq/parts \
  .cad-venv/bin/python -m unittest discover -s tests/cad -v
NUMBA_NUM_THREADS=2 .venv/bin/python rde_sim_starter/run.py --preflight \
  --case docs/cad/mundt_review_audit/case.paper.yaml
NUMBA_NUM_THREADS=2 .venv/bin/python rde_sim_starter/run.py --preflight \
  --case docs/cad/mundt_review_audit/case.cad.yaml
cd rde_sim_starter
NUMBA_NUM_THREADS=2 ../.venv/bin/python -m unittest discover -s tests -p test_contracts.py -v
```

Without the archive environment variable, the archive regression is explicitly
skipped. Without Gmsh, the synthetic STEP unit test is also explicitly skipped;
the remaining nine geometry/adapter tests do not import Gmsh. The recorded full CAD
run had **no skips**. Preflight contracts describe the current scalar solver
interface, while the source hashes, mappings and geometry warnings remain in each
case's `cad_provenance` and the extraction manifest.

These tests establish geometry arithmetic and software integration. They do not
certify the reconstructed parts, assembled fluid volume, effective injector
behavior, or reproduction of the experiment. Assembly and model acceptance gates
are listed in the [development stages](README.md#development-stages-and-acceptance-gates).
