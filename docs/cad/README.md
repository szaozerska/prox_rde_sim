# CAD extraction: Mundt first, reusable geometry next

This branch adds a STEP reader, reviewed feature mapping, SI measurement manifest,
and an adapter for the existing constant-annulus solver. It does not change the
solver, its chemistry, or the active Run 937 configuration. The generated paper
case preserves the nominal geometry; the separately labeled CAD case measures
the archived reconstruction. Neither demonstrates sustained detonation.

Start with the [measured audit](mundt_review_audit/report.md),
[physics priorities](physics_priorities.md), and
[verification record](verification.md). The [manifest](mundt_review_audit/manifest.json)
retains individual bore axes, source faces, transforms, hashes and assumptions.
The [preview](mundt_review_audit/preview.png) shows the reduced annulus and bore-axis
intersections. It is a geometric audit, not a meshed assembly.

## Inputs found in Drive

The [RDE folder](https://drive.google.com/drive/folders/1Av0SBd6qW10HFhnVbyGoqt84qhbAnJ5O)
contains CAD in `output/machining/`:
[Mundt-76mm-budget-RFQ.zip](https://drive.google.com/file/d/1PiaV5FJ-eQU_Gb608xQXWwWx9fEbi9pL/view).
Its seven STEP files represent 205 post-weld assembly, 206 front plate, 207 sleeve,
208 core, 211 process-stage injector, 212 finished injector, and an instrumentation
standoff. The archive includes source drawings and reconstruction notes. Part 211
is a process reference, not an additional finished injector.

The newer `MundtCAD_MicahCAD/CNC_TRUTH/{stl,3mf}` folders and the inspected drawing
and print-export directories were empty when checked on 2026-10-22. This is not
evidence that all RDE CAD is absent. A later correction record in `output/cad-fix`
postdates this ZIP; this extraction is explicitly an audit of the archived
review reconstruction, not certification of the current Onshape model.

Source files are cached locally under `.cad-inputs/rde-mundt-rfq/`, with the ZIP
alongside them. They are ignored by Git and retained unchanged. This is a local
download, not a live Drive filesystem mount. A fresh checkout requires downloading
and extracting the linked archive; the mapping checks the three selected STEP
hashes before reading geometry. Seven STEP files were inventoried during discovery;
the reproducible extraction uses core, sleeve and finished injector.

## Run

From the repository root, with Python 3.12:

```sh
python3 -m venv .cad-venv
.cad-venv/bin/python -m pip install -r requirements.txt -r requirements-cad.txt
.cad-venv/bin/python -m cad_extract inspect \
  .cad-inputs/rde-mundt-rfq/parts/76-208-r01-Core__REVIEW.step \
  --out /tmp/new-core-inventory.json
.cad-venv/bin/python -m cad_extract extract \
  --mapping examples/cad/mundt_review_mapping.json \
  --source-dir .cad-inputs/rde-mundt-rfq/parts \
  --base-case rde_sim_starter/config.yaml \
  --acknowledge-reduction --out /tmp/new-mundt-audit
```

Use fresh output paths; the CLI refuses to overwrite evidence. Without
`--acknowledge-reduction`, extraction writes an audit only. The acknowledgement
records the user's choice of a scalar reduction with stated omissions; it is not
validation of the fluid domain. STEP import runs with one Gmsh thread and does not
mesh or advance CFD. Gmsh is optional and isolated from the solver dependencies.

The paper-only case needs the ordinary Python requirements but no Gmsh:

```sh
.venv/bin/python -m cad_extract reference \
  --base-case rde_sim_starter/config.yaml \
  --acknowledge-reduction --out /tmp/new-mundt-paper.yaml
.venv/bin/python rde_sim_starter/run.py --preflight \
  --case /tmp/new-mundt-audit/case.paper.yaml
.venv/bin/python rde_sim_starter/run.py --preflight \
  --case /tmp/new-mundt-audit/case.cad.yaml
```

Preflight checks compatibility and initialization without time integration.
Operating conditions, chemistry, calibration assumptions and startup remain those
of the supplied base case. Changing geometry alone does not produce a new validated
operating point or calibrated discharge coefficient.

## Data boundaries and current limitations

1. `step.py` imports native STEP solids using OpenCASCADE's embedded-unit conversion
   to metres. Analytic cylinders and planes supply radii, axes and datums. Material
   volumes are labeled as such. Bounding boxes never determine the chamber gap.
2. A reviewed JSON mapping names part files, exact hashes, rigid placements,
   coordinate conventions, semantic faces, selection windows and omissions. Face
   tags are valid only for that source hash and Gmsh version. Radius/angle windows
   select bore families; expected paper counts do not force the answer.
3. `geometry.py` and `pipeline.py` validate planar datums, concentric cylindrical
   walls and injector alignment; derive SI measurements; and merge cylinder patches
   with the same axis/radius. The 288 oxygen patches reduce to 72 bore axes. Axis
   deduplication does not prove passage connectivity: spatially separated coaxial
   passages require additional semantic separation in a later reader.
4. `export_case` writes only the four geometry keys supported by the current solver.
   `cad_provenance` carries the full source/mapping evidence in the case. The solver
   retains that input, while its existing geometry contract still describes a scalar
   `manual_dimensions` interface and correctly advertises no native CAD capability.

The measured mean radius, circumference, annular area, volume, wall areas and
hydraulic diameter are properties of the **selected reduction**. They are not
integrals of a validated assembled gas cavity. The sleeve registration is inferred
and the selected bore surface starts after an enlarged seat. Its continuation to
the inlet is explicitly approximate. The finite axial support intervals describe
underlying trimmed cylinder bounds, not unobstructed flow paths or effective hole
lengths. Likewise, bore-axis intersections extrapolate geometric jet centerlines;
they do not predict mixing, recovery or jet penetration.

Paper values are maintained separately in `cad_extract/mundt_76_fi_5.json`, with
the thesis hash and page references. The archived inch-based drawing dimensions
and rounded paper SI values differ slightly. The nominal area ratio stays 0.110
in the paper case rather than being recomputed from rounded hole diameters.

## Development stages and acceptance gates

**Stage 1, implemented:** source-locked Mundt STEP extraction, analytic features,
reviewable mapping, source/datum/units checks, CAD-vs-paper comparison, lossless
source retention, explicit reduced cases and compatibility tests. Alternative
concentric annuli with changed dimensions can use a newly reviewed mapping. This
is not automatic feature recognition for arbitrary engines. STL/3MF are rejected
with a clear explanation at this stage.

**Stage 2, assembly and related designs:** retain assembly hierarchy and independent
part placements; identify complete bore passages and hydraulic lengths; verify
fuel/oxygen connectivity; derive connected gas cavities and classify all inlet,
outlet, wall, port and interface faces. Add point/section previews for every
selected role, drawing tolerances separately from numeric matching tolerances, and
explicit ambiguity handling. Accept only after unit/scale checks, interference and
leak checks, volume/area closure, source-drawing comparisons, and independent
checks on at least one changed RDE design. Import B-rep formats through their own
readers; STL needs declared units, and 3MF needs unit/transform handling. Mesh
repairs must retain original and repaired geometry plus a repair log.

**Stage 3, backend adapters:** export the same geometry manifest to a reduced model,
a variable-section model, or a 3D mesher through separate adapters. Add supported
capabilities explicitly. The 3D path consumes the actual cavity and boundary groups,
not four scalar dimensions; retain mesh quality, convergence and boundary mapping
checks. Unsupported radial changes, taper, blocked passages or missing datums must
fail validation or remain clearly labeled review evidence. Never quietly substitute
the Mundt dimensions or a bounding-box annulus.

The next priority is verified assembly and injector/plenum semantics, followed by
downstream-domain support. These support the simulation work without coupling CAD
import to chemistry models or a particular solver implementation.

Reader API reference: [Gmsh official documentation](https://gmsh.info/doc/texinfo/gmsh.html),
especially `Geometry.OCCTargetUnit`, `getEntityProperties`, and OpenCASCADE mass
properties. Source mappings are pinned to Gmsh 4.15.2.
