import json
from pathlib import Path
import tempfile
import unittest

from rde3d.mesh_metrics import inspect_mesh, patch_measures


class NativeMeshMetricsTests(unittest.TestCase):
    def test_unit_cube_areas_closure_and_punctuated_log(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp)
            mesh = case/'constant/polyMesh'
            mesh.mkdir(parents=True)
            header = 'FoamFile { version 2.0; format ascii; class dictionary; object test; }\n'
            (mesh/'points').write_text(header+'8\n(\n(0 0 0) (1 0 0) (1 1 0) (0 1 0)\n(0 0 1) (1 0 1) (1 1 1) (0 1 1)\n)\n')
            (mesh/'faces').write_text(header+'6\n(\n4(0 3 2 1) 4(4 5 6 7) 4(0 1 5 4)\n4(1 2 6 5) 4(2 3 7 6) 4(3 0 4 7)\n)\n')
            (mesh/'boundary').write_text(header+'1\n( walls { type wall; nFaces 6; startFace 0; } )\n')
            result = patch_measures(case)
            self.assertEqual(result['walls_m2'], 6.)
            self.assertEqual(result['boundary_closure_relative'], 0.)
            (case/'manifest.json').write_text(json.dumps(dict(cell_count=1, analytical=dict(volume_m3=1., walls_m2=6.))))
            text = ('cells: 1\nMesh has 3 geometric (non-empty/wedge) directions (1 1 1)\n'
                    'Mesh has 3 solution (non-empty) directions (1 1 1)\nTotal volume = 1.0.\n'
                    'Mesh non-orthogonality Max: 0 average: 0\nMax skewness = 0 OK.\nMesh OK.\n')
            (case/'log.checkMesh').write_text(text)
            self.assertEqual(inspect_mesh(case)['status'], 'passed')
            # OpenFOAM can return exit code zero while reporting a failed check.
            (case/'log.checkMesh').write_text(text.replace('Mesh OK.', 'Failed 1 mesh checks.'))
            with self.assertRaises(ValueError):
                inspect_mesh(case)
