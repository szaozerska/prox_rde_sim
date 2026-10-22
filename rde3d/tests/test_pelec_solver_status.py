"""A nominally completed CFD step must not hide an incomplete chemistry solve."""
import unittest
from tools.pelec.validation import native_log_errors


class ChemistryFailureTests(unittest.TestCase):
    def test_completed_time_does_not_hide_cvode_failure(self):
        log = ('[ERROR][rank 0][CVode] At t = 5.03021e-06, '
               'mxstep steps taken before reaching tout.\n'
               'STEP = 100 TIME = 0.001 DT = 1e-05\n')
        self.assertIn('[ERROR]', native_log_errors(log))
        self.assertTrue(native_log_errors(log))

    def test_clean_cvode_run_is_not_rejected(self):
        self.assertEqual([], native_log_errors(
            'Initializing CVODE:\nSTEP = 100 TIME = 0.001 DT = 1e-05\n'))

    def test_timeout_and_abort_are_failures(self):
        for marker in ('SUBPROCESS TIMEOUT', 'amrex::Abort', 'SUNDIALS_ERROR'):
            with self.subTest(marker=marker):
                self.assertTrue(native_log_errors(marker))
