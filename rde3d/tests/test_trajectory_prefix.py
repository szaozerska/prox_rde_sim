import sys, unittest, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/pelec'))
from assemble_startup import audit_window, assemble

class TrajectoryPrefixTests(unittest.TestCase):
    def test_abandoned_failure_is_excluded_only_outside_selected_interval(self):
        log = ('TIME = 0.00005 sumYminus1 MIN = -1e-16 MAX = 2e-16\n'
               'TIME = 0.000056 sumYminus1 MIN = -0.03 MAX = 0.06\n')
        self.assertFalse(audit_window(log, 0, 0.00005)['emergency_stop_required'])
        self.assertTrue(audit_window(log, 0, 0.000056)['emergency_stop_required'])
        self.assertEqual(audit_window(log, 0, 0.00005)['every_step_species_sum']['samples'], 1)

    def test_nonfinite_time_cannot_be_hidden_by_window(self):
        self.assertTrue(audit_window('TIME = nan pressure MIN = 1 MAX = 2\n', 0, 1)['emergency_stop_required'])

    def test_rejects_disconnected_checkpoint_even_with_matching_times(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'manifest.json'
            p.write_text(json.dumps({'segments': [{'run_id':'parent'}, {'run_id':'child', 'restart_checkpoint':'unrelated/chk00001', 'restart_time_s':1}]}))
            with self.assertRaisesRegex(ValueError, 'ancestry'):
                assemble(p, Path(d) / 'output')
