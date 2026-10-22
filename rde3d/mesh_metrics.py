"""Independent geometry reductions from native ASCII OpenFOAM mesh faces."""
import argparse
import json
import math
from pathlib import Path
import re

from .native import run_command


def _body(path):
    text = Path(path).read_text()
    if not re.search(r'\bformat\s+ascii\s*;', text):
        raise ValueError('native mesh metrics require ASCII')
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    text = re.sub(r'FoamFile\s*\{.*?\}', '', text, flags=re.S).strip()
    match = re.fullmatch(r'(\d+)\s*\((.*)\)\s*', text, re.S)
    if not match:
        raise ValueError(f'malformed list in {path}')
    return int(match[1]), match[2]


def patch_measures(case):
    root = Path(case)/'constant/polyMesh'
    npoints, body = _body(root/'points')
    points = [tuple(map(float, row.split())) for row in re.findall(r'\(([^()]+)\)', body)]
    if len(points) != npoints or any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError('invalid mesh points')
    nfaces, body = _body(root/'faces')
    faces = []
    for count, row in re.findall(r'(\d+)\s*\(([^()]*)\)', body):
        face = tuple(map(int, row.split()))
        if len(face) != int(count) or len(face) < 3 or any(i < 0 or i >= npoints for i in face):
            raise ValueError('invalid mesh face')
        faces.append(face)
    if len(faces) != nfaces:
        raise ValueError('truncated mesh faces')
    npatches, body = _body(root/'boundary')
    patches = re.findall(r'(\w+)\s*\{([^{}]*)\}', body)
    if len(patches) != npatches:
        raise ValueError('invalid boundary file')
    report = {}
    closure = [0., 0., 0.]
    total_area = 0.
    for name, data in patches:
        count = re.search(r'\bnFaces\s+(\d+)\s*;', data)
        start = re.search(r'\bstartFace\s+(\d+)\s*;', data)
        if not count or not start or int(start[1])+int(count[1]) > nfaces:
            raise ValueError('invalid patch range')
        area = 0.
        for face in faces[int(start[1]):int(start[1])+int(count[1])]:
            vec = [0., 0., 0.]
            for a, b in zip(face, face[1:]+face[:1]):
                p, q = points[a], points[b]
                vec[0] += .5*(p[1]*q[2]-p[2]*q[1])
                vec[1] += .5*(p[2]*q[0]-p[0]*q[2])
                vec[2] += .5*(p[0]*q[1]-p[1]*q[0])
            area += math.sqrt(sum(x*x for x in vec))
            closure = [a+b for a, b in zip(closure, vec)]
        report[name+'_m2'] = area
        total_area += area
    report['boundary_closure_relative'] = math.sqrt(sum(x*x for x in closure))/total_area
    return report

def mesh_check(case):
    case = Path(case)
    manifest = json.loads((case/'manifest.json').read_text())
    run_command(case, ['blockMesh'])
    run_command(case, ['checkMesh', '-allTopology', '-allGeometry'])
    return inspect_mesh(case)


def inspect_mesh(case):
    case = Path(case)
    manifest = json.loads((case/'manifest.json').read_text())
    text = (case/'log.checkMesh').read_text()
    checks = {
        'mesh_ok': 'Mesh OK.' in text,
        'three_geometry_directions': '3 geometric (non-empty/wedge) directions' in text,
        'three_solution_directions': '3 solution (non-empty) directions' in text,
    }
    cells = re.search(r'\bcells:\s+(\d+)', text)
    volume = re.search(r'Total volume\s*=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)', text)
    nonorth = re.search(r'Mesh non-orthogonality Max:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)', text)
    skew = re.search(r'Max skewness\s*=\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)', text)
    checks['cell_count'] = bool(cells) and int(cells[1]) == manifest['cell_count']
    error = abs(float(volume[1])/manifest['analytical']['volume_m3']-1) if volume else None
    checks['volume'] = error is not None and error < .01
    checks['nonorthogonality'] = bool(nonorth) and float(nonorth[1]) < 70
    checks['skewness'] = bool(skew) and float(skew[1]) < 4
    measures = patch_measures(case)
    area_errors = {name: abs(measures.get(name, 0.)/target-1)
                   for name, target in manifest['analytical'].items() if name.endswith('_m2') and target > 0}
    checks['patch_areas'] = all(error < .01 for error in area_errors.values())
    checks['boundary_closure'] = measures['boundary_closure_relative'] < 1e-12
    result = dict(status='passed' if all(checks.values()) else 'failed', checks=checks,
                  volume_relative_error=error, native_patch_measures=measures, patch_relative_errors=area_errors,
                  max_nonorthogonality_deg=float(nonorth[1]) if nonorth else None,
                  max_skewness=float(skew[1]) if skew else None)
    (case/'mesh_verification.json').write_text(json.dumps(result, indent=2)+'\n')
    if not all(checks.values()):
        raise ValueError(f'mesh checks failed: {checks}')
    return result



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    parser.add_argument('--saved', action='store_true', help='analyze existing logs/mesh without rerunning')
    args = parser.parse_args()
    result = inspect_mesh(args.case) if args.saved else mesh_check(args.case)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
