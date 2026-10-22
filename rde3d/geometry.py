"""Full-annulus blockMesh geometry in SI units; no flow or plotting code."""
from collections import Counter
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Annulus:
    outer_radius: float
    inner_radius: float
    core_length: float
    outlet_z: float

    def __post_init__(self):
        values = (self.outer_radius, self.inner_radius, self.core_length, self.outlet_z)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('geometry must be finite')
        if not 0 < self.inner_radius < self.outer_radius:
            raise ValueError('require 0 < inner_radius < outer_radius')
        if not 0 < self.core_length <= self.outlet_z:
            raise ValueError('require 0 < core_length <= outlet_z')

    def measures(self):
        ri, ro, length, end = (self.inner_radius, self.outer_radius,
                               self.core_length, self.outlet_z)
        expanded = end > length
        inlet = math.pi * (ro**2 - ri**2)
        return {
            'volume_m3': inlet*length + math.pi*ro**2*(end-length),
            'injector_m2': inlet,
            'outlet_m2': math.pi*ro**2 if expanded else inlet,
            'innerWall_m2': 2*math.pi*ri*length,
            'outerWall_m2': 2*math.pi*ro*end,
            'coreEnd_m2': math.pi*ri**2 if expanded else 0.0,
        }


# Outward-oriented local faces of a positively oriented OpenFOAM hex.
HEX_FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


def build_mesh(geometry, ntheta=64, nr=4, nz=24, nz_downstream=24, nr_core=8):
    """Four quarter-annulus blocks per axial section; downstream square/O-grid.

    Curves are true block edges, but cell faces are chordal. ntheta is divisible
    by four; the central square has ntheta/4 cells per edge. No collapsed axes,
    periodic sectors, or duplicated seam vertices. Counts are topology controls,
    not a claim of reactive resolution.
    """
    counts = (ntheta, nr, nz, nz_downstream, nr_core)
    if any(type(n) is not int or n <= 0 for n in counts) or ntheta % 4:
        raise ValueError('positive integer counts; ntheta divisible by four')
    if ntheta < 8:
        raise ValueError('ntheta must be at least eight')
    vertices, vertex_map, arcs, blocks = [], {}, {}, []
    boundary = {name: [] for name in ('injector', 'innerWall', 'outerWall', 'outlet')}
    expanded = geometry.outlet_z > geometry.core_length
    if expanded:
        boundary['coreEnd'] = []

    def vertex(x, y, z):
        key = tuple(round(v, 14) for v in (x, y, z))
        if key not in vertex_map:
            vertex_map[key] = len(vertices)
            vertices.append(key)
        return vertex_map[key]

    def ring(radius, z, square=False):
        result = []
        for k in range(4):
            theta = math.pi/4 + k*math.pi/2
            result.append(vertex(radius*math.cos(theta), radius*math.sin(theta), z))
        if not square:
            for k in range(4):
                theta = math.pi/2 + k*math.pi/2
                pair = (result[k], result[(k+1) % 4])
                arcs[pair] = (radius*math.cos(theta), radius*math.sin(theta), z)
        return result

    def block(v, cells, faces):
        blocks.append({'vertices': tuple(v), 'cells': tuple(cells)})
        for face_index, name in faces.items():
            boundary[name].append(tuple(v[i] for i in HEX_FACES[face_index]))

    levels = [0.0, geometry.core_length]
    if expanded:
        levels.append(geometry.outlet_z)
    rings = {(j, side): ring(radius, z) for j, z in enumerate(levels)
             for side, radius in [('inner', geometry.inner_radius), ('outer', geometry.outer_radius)]}
    for j in range(len(levels)-1):
        for k in range(4):
            nxt = (k+1) % 4
            v = [rings[j, 'inner'][k], rings[j, 'outer'][k],
                 rings[j, 'outer'][nxt], rings[j, 'inner'][nxt],
                 rings[j+1, 'inner'][k], rings[j+1, 'outer'][k],
                 rings[j+1, 'outer'][nxt], rings[j+1, 'inner'][nxt]]
            faces = {3: 'outerWall'}
            if j == 0:
                faces.update({0: 'injector', 5: 'innerWall'})
            if j == len(levels)-2:
                faces[1] = 'outlet'
            block(v, (nr, ntheta//4, nz if j == 0 else nz_downstream), faces)

    if expanded:
        # The four square vertices lie at 0.5*ri; avoid a singular polar axis.
        squares = [ring(geometry.inner_radius*.5, z, square=True) for z in levels[1:]]
        for k in range(4):
            nxt = (k+1) % 4
            v = [squares[0][k], rings[1, 'inner'][k], rings[1, 'inner'][nxt], squares[0][nxt],
                 squares[1][k], rings[2, 'inner'][k], rings[2, 'inner'][nxt], squares[1][nxt]]
            block(v, (nr_core, ntheta//4, nz_downstream), {0: 'coreEnd', 1: 'outlet'})
        block(squares[0] + squares[1], (ntheta//4, ntheta//4, nz_downstream),
              {0: 'coreEnd', 1: 'outlet'})
    mesh = {'vertices': vertices, 'blocks': blocks, 'arcs': arcs, 'boundary': boundary}
    validate_topology(mesh)
    return mesh


def validate_topology(mesh):
    """Reject non-manifold blocks, missing/duplicated faces and unpaired seams."""
    faces = Counter(tuple(sorted(block['vertices'][i] for i in face))
                    for block in mesh['blocks'] for face in HEX_FACES)
    patches = Counter(tuple(sorted(face)) for patch in mesh['boundary'].values() for face in patch)
    if any(count not in (1, 2) for count in faces.values()):
        raise ValueError('non-manifold block face')
    external = Counter({face: 1 for face, count in faces.items() if count == 1})
    if patches != external:
        raise ValueError('boundary coverage does not match exterior block faces')


def cell_count(mesh):
    return sum(math.prod(block['cells']) for block in mesh['blocks'])


def block_mesh_dict(mesh):
    def vector(values):
        return '(' + ' '.join(f'{v:.14g}' for v in values) + ')'
    lines = ['FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }',
             'convertToMeters 1;', 'vertices', '(']
    lines += [vector(v) for v in mesh['vertices']]
    lines += [');', 'blocks', '(']
    lines += [f"hex {vector(b['vertices'])} {vector(b['cells'])} simpleGrading (1 1 1)" for b in mesh['blocks']]
    lines += [');', 'edges', '(']
    lines += [f'arc {a} {b} {vector(mid)}' for (a, b), mid in mesh['arcs'].items()]
    lines += [');', 'boundary', '(']
    for name, faces in mesh['boundary'].items():
        kind = 'patch' if name in ('injector', 'outlet') else 'wall'
        lines += [f'{name} {{ type {kind}; faces ('] + [vector(f) for f in faces] + ['); }']
    return '\n'.join(lines + [');', 'mergePatchPairs ();', ''])
