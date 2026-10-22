import copy
import math
from pathlib import Path
import tempfile
import unittest

from rde3d.geometry import Annulus, HEX_FACES, build_mesh, cell_count, validate_topology
from rde3d.prepare import prepare


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


class GeometryTests(unittest.TestCase):
    def test_paper_areas_volume_and_expansion(self):
        g = Annulus(.0381, .0331, .0762, .152)
        m = g.measures()
        self.assertAlmostEqual(m['injector_m2']*1e6, 1118.407, places=3)
        # Independent radius-average identity inherited from the 2D plan.
        self.assertAlmostEqual(m['injector_m2'], 2*math.pi*.0356*.005, places=15)
        self.assertAlmostEqual(m['volume_m3'], m['injector_m2']*.0762 + math.pi*.0381**2*.0758)
        self.assertAlmostEqual(m['outlet_m2']-m['injector_m2'], m['coreEnd_m2'])

    def test_invalid_geometry_and_resolution(self):
        for vals in [(1, 1, 1, 2), (1, 0, 1, 2), (1, .5, 2, 1), (1, .5, 0, 1), (math.nan, .5, 1, 2)]:
            with self.assertRaises(ValueError):
                Annulus(*vals)
        g = Annulus(.0381, .0331, .0762, .152)
        for kwargs in [dict(ntheta=7), dict(nr=0), dict(nz=1.5), dict(ntheta=True)]:
            with self.assertRaises(ValueError):
                build_mesh(g, **kwargs)

    def test_connected_faces_orientation_and_cell_counts(self):
        for end in (.0762, .152):
            mesh = build_mesh(Annulus(.0381, .0331, .0762, end), 64, 4, 24, 24, 8)
            expected = 64*4*24
            if end > .0762:
                expected += (64*4+64*8+16*16)*24
            self.assertEqual(cell_count(mesh), expected)
            vertices = mesh['vertices']
            self.assertEqual(len(vertices), len(set(vertices)))
            face_signs = {}
            for block in mesh['blocks']:
                v = [vertices[i] for i in block['vertices']]
                # Local radial/theta/axial mapping must have a positive Jacobian.
                self.assertGreater(dot(cross(sub(v[1], v[0]), sub(v[3], v[0])), sub(v[4], v[0])), 0)
                center = tuple(sum(p[i] for p in v)/8 for i in range(3))
                for face in HEX_FACES:
                    pts = [v[i] for i in face]
                    normal = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
                    fc = tuple(sum(p[i] for p in pts)/4 for i in range(3))
                    self.assertGreater(dot(normal, sub(fc, center)), 0)
                    key = tuple(sorted(block['vertices'][i] for i in face))
                    if key in face_signs:
                        self.assertLess(dot(normal, face_signs[key]), 0)
                    face_signs[key] = normal
            broken = copy.deepcopy(mesh)
            broken['boundary']['injector'].pop()
            with self.assertRaises(ValueError):
                validate_topology(broken)

    def test_immutable_case_reuses_2d_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source.yaml'
            source.write_text('model: {geometry: constant_annulus}\ngeometry: {r_outer_mm: 38.1, r_inner_mm: 33.1, length_mm: 76.2}\n')
            out = Path(temp)/'mesh'
            report = prepare(source, out)
            self.assertEqual(report['purpose'], 'mesh_only')
            self.assertFalse(report['validated_reactive_model'])
            self.assertEqual((out/'source_case.yaml').read_bytes(), source.read_bytes())
            with self.assertRaises(FileExistsError):
                prepare(source, out)
            self.assertIn('coreEnd', report['boundaries'])
