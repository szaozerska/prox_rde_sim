"""Small nonreactive plumbing checks, not a Run 937 propagation experiment."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import yaml
import run
from solver import Solver, InvalidStateError, NG

HERE = Path(__file__).resolve().parents[1]


def toy_case():
    config = yaml.safe_load((HERE / 'config.yaml').read_text())
    config['geometry'].update(r_outer_mm=6., r_inner_mm=4., length_mm=4.)
    config['model']['chemistry'] = 'disabled'
    config['operating_point']['f_paper_kHz'] = 10000.  # artificial time budget for a tiny I/O check
    config['numerics'].update(dx_mm=2., average_start_us=.055, snapshot_every_us=.04,
                              checkpoint_every_us=.1, max_step_ns=30., probe_y_mm=1.)
    config['initialization'] = dict(kind='uniform', progress=.2, u_theta=10., u_z=5.)
    config['diagnostics']['pressure_stations_mm'] = [0., 2., 4.]
    return config, json.loads((HERE / 'calib.json').read_text())


def records(directory):
    return [json.loads(line) for line in (directory / 'history.jsonl').read_text().splitlines()]


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / 'run'
        self.config, self.calibration = toy_case()

    def start(self):
        return run.start_run(self.config, self.calibration, self.output)

    def test_three_interval_cap_early_output_and_explicit_empty_average(self):
        self.config['numerics']['average_start_us'] = 1.
        result = self.start()
        self.assertEqual(result['t'], 3e-7)
        self.assertEqual(result['status'], 'completed_limit')
        self.assertFalse(result['average']['available'])
        self.assertIsNone(result['average']['pressure_profile_Pa'])
        self.assertIsNone(result['observed_passages'])
        self.assertIsNone(result['engine_torque_Nm'])
        times = []
        for path in sorted((self.output / 'fields').glob('*.npz')):
            with np.load(path, allow_pickle=False) as saved:
                times.append(float(saved['t']))
                self.assertTrue(np.isfinite(saved['pressure']).all())
                self.assertEqual(saved['pressure'].shape, (16, 2))
        self.assertEqual(times[0], 0.)
        self.assertLess(times[1], 1e-7)
        self.assertEqual(times[-1], 3e-7)
        rows = records(self.output)
        np.testing.assert_array_equal([r['step'] for r in rows], np.arange(len(rows)))
        self.assertTrue(np.all(np.diff([r['t'] for r in rows]) > 0))
        budget = result['budgets']
        scale = np.maximum(np.abs(rows[0]['inventory']), 1e-12)
        self.assertLess(np.max(np.abs(budget['residual']) / scale), 1e-13)

    def test_restart_extends_same_run_and_preserves_averages_and_fluxes(self):
        first = self.start()
        prefix = (self.output / 'history.jsonl').read_bytes()
        inputs = (self.output / 'inputs.json').read_bytes()
        self.config['geometry']['r_outer_mm'] = 900.  # caller changes do not mutate saved inputs
        result = run.resume_run(self.output)
        self.assertEqual(result['t'], 5e-7)
        self.assertTrue((self.output / 'history.jsonl').read_bytes().startswith(prefix))
        self.assertEqual((self.output / 'inputs.json').read_bytes(), inputs)
        self.assertGreater(result['steps'], first['steps'])
        rows = records(self.output)
        self.assertEqual([r['step'] for r in rows], list(range(result['steps']+1)))
        durations = np.array([max(0., r['t'] - max(r['t']-r['dt'], .055e-6)) for r in rows[1:]])
        profile = np.array([r['pressure_stations'][::2] for r in rows[1:]])
        np.testing.assert_allclose(result['average']['pressure_profile_Pa'],
                                   np.sum(profile*durations[:, None], axis=0)/durations.sum(), rtol=2e-15)
        self.assertAlmostEqual(result['average']['duration_s'], 5e-7 - .055e-6, delta=1e-21)
        # Independent uninterrupted replay of the recorded steps must recover the
        # same float64 state, with no skipped/repeated interval or budget on restart.
        config, calibration = toy_case()
        resolved = run.resolve_case(config, calibration)
        uninterrupted = run.build_solver(resolved, calibration)
        for row in rows[1:]:
            uninterrupted.step(dt_max=row['dt'])
        saved, _, _, _ = run._load_checkpoint(self.output)
        np.testing.assert_array_equal(saved.U, uninterrupted.U)
        np.testing.assert_array_equal(saved.cumulative_boundary, uninterrupted.cumulative_boundary)
        np.testing.assert_array_equal(saved.cumulative_source, uninterrupted.cumulative_source)
        with self.assertRaisesRegex(ValueError, 'later'):
            run.resume_run(self.output)

    def test_incompatible_inputs_and_existing_output_are_rejected(self):
        for mutate in [lambda c: c['model'].update(walls='friction'),
                       lambda c: c['operating_point'].update(phi=1.3),
                       lambda c: c['operating_point'].update(mass_flux=230.),
                       lambda c: c['geometry'].update(r_inner_mm=0.)]:
            config = copy.deepcopy(self.config)
            mutate(config)
            with self.assertRaises(ValueError):
                run.start_run(config, self.calibration, self.output)
            self.assertFalse(self.output.exists())
        with self.assertRaises(ValueError):
            run.start_run(self.config, self.calibration, self.output, test_passages=5)
        self.start()
        checkpoint = (self.output / 'checkpoint.npz').read_bytes()
        with self.assertRaises(FileExistsError):
            self.start()
        self.assertEqual(checkpoint, (self.output / 'checkpoint.npz').read_bytes())
        with patch.object(run, '_fingerprint', return_value={}):
            with self.assertRaisesRegex(ValueError, 'same format'):
                run.resume_run(self.output)
        manifest = json.loads((self.output / 'inputs.json').read_text())
        manifest['config']['numerics']['cfl'] = .2
        (self.output / 'inputs.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'match saved inputs'):
            run.resume_run(self.output)

    def test_rejected_rk_state_saves_only_accepted_state_and_failure_details(self):
        check = Solver._check_state
        def reject(solver, U, stage):
            if stage == 'RK stage 1' and solver.t >= 4e-8:
                U[4, NG, NG] = 2 * U[0, NG, NG]
            check(solver, U, stage)
        with patch.object(Solver, '_check_state', reject):
            with self.assertRaises(InvalidStateError):
                self.start()
        summary = json.loads((self.output / 'summary.json').read_text())
        self.assertEqual(summary['status'], 'failed')
        self.assertEqual(summary['last_failure']['stage'], 'RK stage 1')
        self.assertEqual(summary['invalid_state_count'], 1)
        saved, _, _, _ = run._load_checkpoint(self.output)
        self.assertEqual(saved.t, records(self.output)[-1]['t'])
        self.assertGreater(saved.steps, 0)
        self.assertLessEqual(saved.prim()[4].max(), 1.)
        result = run.resume_run(self.output, test_passages=3)
        self.assertEqual(result['t'], 3e-7)
        self.assertEqual(result['invalid_state_count'], 1)

    def test_failure_during_bookkeeping_keeps_checkpoint_and_archives_partial_tail(self):
        history_row = run._history_row
        def fail(solver, resolved):
            if solver.steps == 4:
                raise OSError('injected output failure after an accepted step')
            return history_row(solver, resolved)
        with patch.object(run, '_history_row', fail):
            with self.assertRaises(OSError):
                self.start()
        saved, _, _, _ = run._load_checkpoint(self.output)
        self.assertEqual(saved.steps, 0)
        tail = (self.output / 'history.jsonl').read_bytes().splitlines(keepends=True)[1:]
        self.assertTrue(tail)
        result = run.resume_run(self.output, test_passages=3)
        self.assertEqual(result['t'], 3e-7)
        recovered = list((self.output / 'recovery').glob('*/history_after_checkpoint.jsonl'))
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0].read_bytes(), b''.join(tail))
        self.assertTrue(list((self.output / 'recovery').glob('*/step_*.npz')))
        rows = records(self.output)
        self.assertEqual([r['step'] for r in rows], list(range(result['steps']+1)))

    def test_atomic_failure_leaves_previous_checkpoint_bytes_intact(self):
        path = Path(self.tmp.name) / 'checkpoint.npz'
        path.write_bytes(b'previous complete checkpoint')
        def fail(stream):
            stream.write(b'partial replacement')
            raise OSError('injected interrupted write')
        with self.assertRaises(OSError):
            run._atomic_write(path, fail)
        self.assertEqual(path.read_bytes(), b'previous complete checkpoint')
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [path])

    def test_failed_checkpoint_write_can_resume_previous_checkpoint(self):
        write = run._write_npz
        initial_checkpoint = []
        def fail(path, **arrays):
            if Path(path).name == 'checkpoint.npz':
                if initial_checkpoint:
                    raise OSError('injected unavailable checkpoint storage')
                write(path, **arrays)
                initial_checkpoint.append(Path(path).read_bytes())
            else:
                write(path, **arrays)
        with patch.object(run, '_write_npz', fail):
            with self.assertRaises(OSError):
                self.start()
        self.assertEqual((self.output / 'checkpoint.npz').read_bytes(), initial_checkpoint[0])
        self.assertEqual(json.loads((self.output / 'summary.json').read_text())['t'], 0.)
        self.assertEqual(run.resume_run(self.output, test_passages=3)['t'], 3e-7)

    def test_active_run_lock_prevents_second_writer(self):
        self.output.mkdir()
        with run._run_lock(self.output):
            with self.assertRaisesRegex(RuntimeError, 'another process'):
                with run._run_lock(self.output):
                    self.fail('lock admitted a second writer')

    def test_periodic_ignition_wraps_at_seam(self):
        x = np.array([.01, .05, .5, .95, .99])
        np.testing.assert_array_equal(run.periodic_band(x, .9, .2, 1.), [True, True, False, True, True])
        np.testing.assert_array_equal(run.periodic_band(x, -.1, .2, 1.), [True, True, False, True, True])

    def test_cli_new_run_then_resume_and_reject_mixed_inputs(self):
        case = Path(self.tmp.name) / 'case.yaml'
        case.write_text(yaml.safe_dump(self.config))
        command = [sys.executable, str(HERE / 'run.py')]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', NUMBA_NUM_THREADS='2')
        new = subprocess.run(command + ['--case', str(case), '--calibration', str(HERE / 'calib.json'),
                                        '--out', str(self.output)], env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(new.returncode, 0, new.stdout + new.stderr)
        manifest = json.loads((self.output / 'inputs.json').read_text())
        self.assertEqual(manifest['source_text']['case_yaml'], case.read_text())
        resume = subprocess.run(command + ['--resume', str(self.output)], env=env,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(resume.returncode, 0, resume.stdout + resume.stderr)
        self.assertEqual(records(self.output)[-1]['t'], 5e-7)
        invalid = subprocess.run(command + ['--resume', str(self.output), '--case', str(case)],
                                 env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(invalid.returncode, 2)
