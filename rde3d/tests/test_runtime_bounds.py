import sys, unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/pelec'))
from runtime_bounds import bounded_runtime_seconds

class RuntimeBoundsTests(unittest.TestCase):
    def test_queue_delay_reduces_worker_budget(self):
        cutoff = '2026-10-27T20:00:00-07:00'
        before_queue = datetime(2026,10,28,0,0,tzinfo=timezone.utc)
        after_queue = datetime(2026,10,28,2,0,tzinfo=timezone.utc)
        self.assertEqual(bounded_runtime_seconds(14400,cutoff,before_queue),10800)
        self.assertEqual(bounded_runtime_seconds(14400,cutoff,after_queue),3600)

    def test_rejects_expired_or_imminent_cutoff(self):
        for hour,minute in ((2,58),(3,0),(4,0)):
            with self.assertRaisesRegex(ValueError,'cutoff'):
                bounded_runtime_seconds(14400,'2026-10-28T03:00:00+00:00',datetime(2026,10,28,hour,minute,tzinfo=timezone.utc))

    def test_requires_timezone_and_retains_shorter_segment_limit(self):
        with self.assertRaisesRegex(ValueError,'timezone'):
            bounded_runtime_seconds(600,'2026-10-28T03:00:00')
        self.assertEqual(bounded_runtime_seconds(600,'2026-10-28T03:00:00+00:00',datetime(2026,10,28,0,0,tzinfo=timezone.utc)),600)
        self.assertEqual(bounded_runtime_seconds(600),600)
