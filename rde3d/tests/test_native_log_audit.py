"""Catch transient closure defects that saved snapshots can miss."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/pelec'))
from audit_native_log import audit_native_log

class NativeLogAuditTests(unittest.TestCase):
    def test_transient_failure_cannot_be_erased_by_later_good_step(self):
        log='TIME = 5.598e-05 sumYminus1 MIN = -0.034841601 MAX = 0.036065022\nTIME = 5.606e-05 sumYminus1 MIN = -6.66e-16 MAX = 0.061661052\nTIME = 5.614e-05 sumYminus1 MIN = -6.66e-16 MAX = 6.66e-16\n'
        a=audit_native_log(log)
        self.assertTrue(a['emergency_stop_required']);self.assertEqual(a['violation_count'],2)
        self.assertAlmostEqual(a['every_step_species_sum']['maximum_absolute_error'],.061661052)
        self.assertEqual(a['every_step_species_sum']['samples'],3)

    def test_known_small_negative_is_not_an_emergency_pass(self):
        a=audit_native_log('TIME = 1e-5 massfrac MIN = -0.001 MAX = 0.9\n')
        self.assertFalse(a['emergency_stop_required']);self.assertEqual(a['fields']['massfrac']['minimum'],-.001)

    def test_nonfinite_is_stopped_and_json_serializable(self):
        a=audit_native_log('TIME = 1e-5 pressure MIN = nan MAX = inf\n')
        self.assertTrue(a['emergency_stop_required']);json.dumps(a,allow_nan=False)
        a=audit_native_log('TIME = nan pressure MIN = 1 MAX = 2\n')
        self.assertTrue(a['emergency_stop_required']);json.dumps(a,allow_nan=False)

    def test_incomplete_line_does_not_create_false_failure(self):
        a=audit_native_log('TIME = 1e-5 sumYminus1 MIN = 0 MAX = 6')
        self.assertFalse(a['emergency_stop_required']);self.assertEqual(a['fields'],{})
