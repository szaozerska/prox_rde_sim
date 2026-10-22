from pathlib import Path
import tempfile
import unittest

from rde3d.native import inspect_completion, read_field


class CompletionTests(unittest.TestCase):
    def test_early_success_missing_fields_and_invalid_states_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp)
            (case/'0').mkdir()
            with self.assertRaises(ValueError):
                inspect_completion(case, 1e-6, 2)
            final = case/'1e-6'
            final.mkdir()
            with self.assertRaises(FileNotFoundError):
                inspect_completion(case, 1e-6, 2)
            for name, value in [('p', '101325'), ('T', '300'), ('U', '(0 0 0)')]:
                (final/name).write_text(f'FoamFile {{format ascii;}}\ninternalField uniform {value};\n')
            t, fields = inspect_completion(case, 1e-6, 2)
            self.assertEqual(t, 1e-6)
            self.assertEqual(fields['U'], [(0, 0, 0)]*2)
            (final/'T').write_text('FoamFile {format ascii;} internalField uniform -1;')
            with self.assertRaisesRegex(ValueError, 'nonpositive'):
                inspect_completion(case, 1e-6, 2)

    def test_nonuniform_fields_reject_truncation_nonfinite_and_wrong_count(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'p'
            path.write_text('FoamFile {format ascii;} internalField nonuniform List<scalar> 2 (1e5 2e5);')
            self.assertEqual(read_field(path, 2), [(1e5,), (2e5,)])
            for body in ['List<scalar> 2 (1e5);', 'List<scalar> 2 (1e5 nan);', 'List<scalar> 3 (1 2 3);',
                         'List<vector> 2 ((0 0 0) (1 2));']:
                path.write_text('FoamFile {format ascii;} internalField nonuniform '+body)
                with self.assertRaises(ValueError):
                    read_field(path, 2)
