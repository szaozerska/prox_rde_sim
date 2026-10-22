"""Rendering contracts and native fuel accounting; no wave classifier shortcuts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
import run
from animate import playback_durations, surface_blocks, render_gifs, fuel_accounting
from window_report import load_native_prefix
from test_run import toy_case
from test_workflow import hashes


class AnimationTests(unittest.TestCase):
    def test_timing_preserves_unequal_physical_intervals_and_endpoint_hold(self):
        self.assertEqual(playback_durations([0., 1., 3., 4.], seconds=4.), [1000, 2000, 1000, 1500])
        for bad in ([0.], [0., 0.], [2., 1.], [0., np.nan]):
            with self.assertRaises(ValueError): playback_durations(bad)
        with self.assertRaises(ValueError): playback_durations([0., 1e-10, 1.])

    def test_surface_cells_conserve_mean_and_close_periodic_seam(self):
        a = np.arange(35).reshape(7, 5)
        xe, ze, values = surface_blocks(a, 3, 2)
        self.assertEqual(xe.tolist(), [0, 2, 4, 7])
        self.assertEqual(ze.tolist(), [0, 2, 5])
        self.assertEqual(values[0, 0], np.mean(a[:2, :2]))
        self.assertEqual(values[-1, -1], np.mean(a[4:, 2:]))
        weights = np.diff(xe)[:, None]*np.diff(ze)[None, :]
        self.assertAlmostEqual(float(np.sum(values*weights)), float(a.sum()))
        angles = xe/7*2*np.pi
        np.testing.assert_allclose([np.cos(angles[0]), np.sin(angles[0])],
                                   [np.cos(angles[-1]), np.sin(angles[-1])], atol=1e-14)

    def test_native_end_to_end_gifs_readonly_zero_reaction_and_fuel_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); native=root/'native'; out=root/'gif'
            config, cal=toy_case()
            # Two saved endpoints exercise rendering without unnecessary frame cost.
            config['numerics']['snapshot_every_us']=1.
            run.start_run(config, cal, native)
            before=hashes(native)
            inputs, summary, rows, _=load_native_prefix(native)
            account=fuel_accounting(inputs, summary, rows, 0., summary['t'])
            self.assertEqual(account['converted_mixture_kg'], 0.)
            self.assertGreater(account['injected_unreacted_mixture_kg'], 0.)
            self.assertLess(abs(account['unreacted_balance_residual_kg']), 1e-17)
            self.assertAlmostEqual(account['initial_unreacted_mixture_kg'],
                rows[0]['inventory'][0]*.8, delta=1e-18)
            with patch('solver.Solver.step', side_effect=AssertionError('renderer launched CFD')):
                result=render_gifs(native, out, seconds=2.)
            self.assertEqual(hashes(native), before)
            self.assertTrue((out/'COMPLETE').exists())
            self.assertEqual(result['frames'][0]['time_s'], 0.)
            self.assertEqual(result['frames'][-1]['time_s'], summary['t'])
            for name in ('unwrapped.gif', 'wrapped.gif'):
                with Image.open(out/name) as gif:
                    self.assertEqual(gif.n_frames, 2)
                    self.assertNotIn('loop', gif.info)
                    self.assertEqual(gif.info['duration'], 2000)
                    gif.seek(1)
                    self.assertEqual(gif.info['duration'], 1500)
                    self.assertGreater(np.asarray(gif.convert('RGB')).std(), 20.)
            with self.assertRaises(FileExistsError): render_gifs(native, out)
            with self.assertRaises(ValueError): render_gifs(native, native/'gif')
            with self.assertRaises(ValueError): render_gifs(native, root/'empty', .01e-6, .02e-6)
            self.assertFalse((root/'empty').exists())

    def test_failed_encoder_cannot_leave_complete_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); config, cal=toy_case()
            config['numerics']['snapshot_every_us']=1.
            run.start_run(config, cal, root/'native')
            with patch('PIL.Image.Image.save', side_effect=OSError('disk full')):
                with self.assertRaises(OSError): render_gifs(root/'native', root/'out')
            self.assertTrue((root/'out'/'INCOMPLETE').exists())
            self.assertFalse((root/'out'/'COMPLETE').exists())
