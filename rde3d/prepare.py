"""Prepare mesh-only native cases. Deliberately cannot launch reactive flow."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import yaml

from .geometry import Annulus, block_mesh_dict, build_mesh, cell_count


def prepare(case_path, out, *, outlet_z=.152, ntheta=64, nr=4, nz=24, nz_downstream=24, nr_core=8):
    case_path, out = Path(case_path), Path(out)
    raw = case_path.read_bytes()
    source = yaml.safe_load(raw)
    if source.get('model', {}).get('geometry') != 'constant_annulus':
        raise ValueError('only the explicitly identified constant-annulus source is supported')
    g = source['geometry']
    geometry = Annulus(g['r_outer_mm']*.001, g['r_inner_mm']*.001, g['length_mm']*.001, outlet_z)
    mesh = build_mesh(geometry, ntheta, nr, nz, nz_downstream, nr_core)
    controls = dict(ntheta=ntheta, nr=nr, nz=nz, nz_downstream=nz_downstream, nr_core=nr_core)
    manifest = dict(schema_version=1, purpose='mesh_only', backend='OpenFOAM-8',
                    source_case_sha256=hashlib.sha256(raw).hexdigest(),
                    geometry_m=asdict(geometry), analytical=geometry.measures(),
                    mesh_controls=controls, cell_count=cell_count(mesh),
                    coordinates='Cartesian x,y,z; axis +z; azimuth atan2(y,x)',
                    boundaries=list(mesh['boundary']),
                    expansion_reference='Mundt printed pp. 29-30, 37; outer core 152 mm',
                    omissions=['injector passages/plenums', 'predetonator', 'facility duct/tank'],
                    validated_reactive_model=False)
    # Validate everything above before creating a new destination; never overwrite.
    out.mkdir(parents=True, exist_ok=False)
    (out/'system').mkdir()
    (out/'constant').mkdir()
    (out/'source_case.yaml').write_bytes(raw)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    (out/'system/blockMeshDict').write_text(block_mesh_dict(mesh))
    (out/'system/controlDict').write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n'
        'application blockMesh; startFrom startTime; startTime 0; stopAt endTime;\n'
        'endTime 1; deltaT 1; writeControl timeStep; writeInterval 1;\n'
        'writeFormat ascii; writePrecision 12; runTimeModifiable false;\n')
    for name in ('fvSchemes', 'fvSolution'):
        (out/'system'/name).write_text(
            'FoamFile { version 2.0; format ascii; class dictionary; object '+name+'; }\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, default=Path('rde_sim_starter/config.yaml'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--outlet-z', type=float, default=.152, help='metres; core length gives annulus-only control')
    for name, default in [('ntheta', 64), ('nr', 4), ('nz', 24), ('nz-downstream', 24), ('nr-core', 8)]:
        parser.add_argument('--'+name, type=int, default=default)
    args = vars(parser.parse_args())
    result = prepare(args.pop('case'), args.pop('out'), **args)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
