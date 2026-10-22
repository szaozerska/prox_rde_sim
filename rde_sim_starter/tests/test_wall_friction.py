"""Independent drag ODE, energy and angular-balance checks, not torque calibration."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from physics import wall_drag_rhs
from solver import Solver, PERIODIC, WALL, NG
import run
from window_report import report_saved_window, render_markdown
from test_run import toy_case


def box(cf=.01, velocity=100., gap=.01):
    s = Solver(4, 2, 1., 1., (1.4, 0., 287., 0., 0.),
               (PERIODIC, PERIODIC, WALL, WALL), wall_cf=cf, wall_gap=gap)
    s.set_prim(2., velocity, 0., 1e5, 0.)
    return s


def advance(s, dt, end=.002):
    while s.t < end:
        s.step(dt_max=min(dt, end-s.t))
    return s


class WallTests(unittest.TestCase):
    def test_uniform_drag_exact_solution_energy_and_second_order(self):
        errors = []
        for dt in [.0002, .0001, .00005]:
            s = box(); initial = s.conserved_totals()
            advance(s, dt)
            speed = 100/(1 + .01/.01 * 100 * .002)
            W = s.prim()
            errors.append(abs(W[1,0,0]-speed))
            self.assertLess(errors[-1], .004)
            expected_p = 1e5 + .4*.5*2*(100**2-W[1,0,0]**2)
            np.testing.assert_allclose(W[3], expected_p, rtol=2e-15)
            np.testing.assert_array_equal(s.U[3,NG:-NG,NG:-NG], np.full((4,2), initial[3]/8))
            self.assertEqual(s.cumulative_source[3], 0.)
            np.testing.assert_allclose(s.conserved_totals()-initial,
                s.cumulative_source, atol=2e-11, rtol=2e-14)
        self.assertGreater(errors[0]/errors[1], 3.8)
        self.assertGreater(errors[1]/errors[2], 3.8)

    def test_reversal_and_coefficient_sensitivity(self):
        plus, minus = advance(box(), .00005), advance(box(velocity=-100), .00005)
        np.testing.assert_allclose(plus.prim()[1], -minus.prim()[1], atol=0, rtol=0)
        np.testing.assert_allclose(plus.cumulative_source, -minus.cumulative_source, atol=0, rtol=0)
        faster = advance(box(cf=.02), .00005)
        exact = 100/(1 + 2*100*.002)
        self.assertAlmostEqual(faster.prim()[1,0,0], exact, delta=.002)
        self.assertLess(faster.prim()[1,0,0], plus.prim()[1,0,0])

    def test_two_component_drag_factor_and_zero_velocity(self):
        W = np.zeros((5, 6, 5)); out = np.zeros_like(W)
        W[0] = 2.; W[1] = 3.; W[2] = 4.
        theta, axial, rate = wall_drag_rhs(W, out, .01/.002, 2, .02)
        # Two active cells; S = -(Cf/g) rho speed vector, independently 3-4-5.
        self.assertEqual(theta, -6.)
        self.assertEqual(axial, -8.)
        self.assertEqual(rate, 25.)
        self.assertTrue(np.all(out[[0,3,4]] == 0))
        W[1:3] = 0; out[:] = 0
        self.assertEqual(wall_drag_rhs(W,out,5.,2,.02), (0.,0.,0.))

    def test_zero_cf_is_bitwise_baseline_and_invalid_parameters_rejected(self):
        explicit = box(cf=0)
        baseline = Solver(4,2,1.,1.,(1.4,0.,287.,0.,0.),(PERIODIC,PERIODIC,WALL,WALL))
        baseline.set_prim(2.,100.,0.,1e5,0.)
        advance(explicit,.0001); advance(baseline,.0001)
        np.testing.assert_array_equal(explicit.U, baseline.U)
        np.testing.assert_array_equal(explicit.cumulative_source, baseline.cumulative_source)
        for cf, gap in [(-1,.1),(float('nan'),.1),(.01,None),(.01,0)]:
            with self.assertRaises(ValueError): box(cf=cf,gap=gap)

    def test_decay_step_cap_prevents_unresolved_source(self):
        s = box(cf=100.)
        dt = s.step()
        self.assertAlmostEqual(dt, .1/(100/.01*100))
        self.assertGreater(s.prim()[1].min(), 0)
        self.assertLess(s.prim()[1].max(), 100)

    def test_saved_restart_and_independent_angular_balance(self):
        config, cal = toy_case()
        config['model'].update(walls='constant_cf', wall_cf=.02)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'run'
            run.start_run(config,cal,out)
            run.resume_run(out)
            report = report_saved_window(out, .055e-6, .45e-6)
            torque = report['engine_torque']
            self.assertTrue(torque['available'])
            self.assertGreater(torque['mean_Nm'], 0)
            self.assertAlmostEqual(torque['mean_Nm'],torque['balance_mean_Nm'],delta=1e-10)
            self.assertTrue(report['budgets']['closure_within_tolerance'])
            self.assertIn('constant-Cf', render_markdown(report))
            rows = [json.loads(x) for x in (out/'history.jsonl').read_text().splitlines()]
            r = run.resolve_case(config,cal); replay = run.build_solver(r,cal)
            for row in rows[1:]: replay.step(dt_max=row['dt'])
            saved,_,_,_ = run._load_checkpoint(out)
            np.testing.assert_array_equal(replay.U,saved.U)
            np.testing.assert_array_equal(replay.cumulative_source,saved.cumulative_source)
            result = json.loads((out/'summary.json').read_text())
            impulse = sum(row['wall_engine_angular_impulse_Nm_s'] for row in rows[1:])
            self.assertAlmostEqual(result['engine_torque_Nm'],impulse/result['t'],delta=1e-15)

    def test_no_implicit_friction_coefficient(self):
        config, cal = toy_case()
        for model in [dict(walls='constant_cf'), dict(walls='inviscid', wall_cf=.01)]:
            changed=copy.deepcopy(config); changed['model'].update(model)
            with self.assertRaises(ValueError): run.resolve_case(changed,cal)
