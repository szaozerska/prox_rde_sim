"""Read-only STEP feature inventory using OpenCASCADE through Gmsh.

All measurements use analytic B-rep properties, never padded bounding boxes.
Entity tags are valid only for the recorded source hash and reader version.
This module does not infer that a solid or its complement is a fluid domain.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path

import numpy as np


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@contextmanager
def kernel():
    try:
        import gmsh
    except ImportError as exc:
        raise RuntimeError('STEP import needs optional requirements-cad.txt') from exc
    if gmsh.isInitialized():
        raise RuntimeError('CAD reader requires its own Gmsh session; use a separate process')
    gmsh.initialize([], readConfigFiles=False)
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('General.NumThreads', 1)
        # Explicitly convert embedded STEP units, including inch exports, into SI.
        gmsh.option.setString('Geometry.OCCTargetUnit', 'M')
        yield gmsh
    finally:
        gmsh.finalize()


def inspect_step(path, expected_sha256=None):
    path = Path(path)
    if path.suffix.lower() not in {'.step', '.stp'}:
        raise ValueError('stage 1 accepts STEP/STP; STL/3MF need separate unit and mesh validation')
    digest = sha256(path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(f'{path.name}: source hash changed; reinspect and review the feature mapping')
    declarations = path.read_text(encoding='ascii', errors='replace').upper()
    if 'LENGTH_UNIT' not in declarations or 'GLOBAL_UNIT_ASSIGNED_CONTEXT' not in declarations:
        raise ValueError('STEP must declare length units; implicit importer defaults are not accepted')
    with kernel() as gmsh:
        gmsh.model.occ.importShapes(str(path.resolve()))
        gmsh.model.occ.synchronize()
        solids = [dict(tag=int(t), volume_m3=gmsh.model.occ.getMass(d, t),
                       center_of_mass_m=list(gmsh.model.occ.getCenterOfMass(d, t)))
                  for d, t in gmsh.model.getEntities(3)]
        if not solids:
            raise ValueError(f'{path.name}: no solid B-rep found')
        if not all(np.isfinite(s['volume_m3']) and s['volume_m3'] > 0 for s in solids):
            raise ValueError('invalid material solid volumes')
        faces = []
        for dim, tag in gmsh.model.getEntities(2):
            kind = gmsh.model.getType(dim, tag)
            _, props = gmsh.model.getEntityProperties(dim, tag)
            face = dict(tag=int(tag), kind=kind, area_m2=gmsh.model.occ.getMass(dim, tag),
                        properties=props.tolist())
            if kind == 'Cylinder':
                if len(props) != 7 or props[6] <= 0:
                    raise ValueError('unsupported cylinder property layout')
                axis = props[3:6] / np.linalg.norm(props[3:6])
                low, high = gmsh.model.getParametrizationBounds(dim, tag)
                uv = [[u, v] for u in np.linspace(low[0], high[0], 5)
                      for v in [low[1], high[1]]]
                points = np.asarray(gmsh.model.getValue(dim, tag, np.ravel(uv))).reshape(-1, 3)
                along = (points - props[:3]) @ axis
                face.update(radius_m=float(props[6]), axis=axis.tolist(),
                            axis_point_m=props[:3].tolist(),
                            support_interval_m=[float(along.min()), float(along.max())])
            faces.append(face)
        if not faces or not all(np.isfinite(f['area_m2']) and f['area_m2'] > 0 for f in faces):
            raise ValueError('invalid surface areas')
        return dict(schema_version=1, source=dict(name=path.name, sha256=digest,
                    size_bytes=path.stat().st_size, format='STEP',
                    unit_policy='embedded STEP units converted by OCCTargetUnit=M'),
                    reader=dict(name='gmsh/OpenCASCADE', version=gmsh.__version__),
                    units='SI', solids=solids, faces=faces,
                    fluid_domain_verified=False,
                    notes=['Solid volume is material volume, not combustor gas volume.',
                           'Cylinder support intervals bound the underlying trimmed surface; they are not passage connectivity.',
                           'Face tags are scoped to source SHA256 and reader version.'])
