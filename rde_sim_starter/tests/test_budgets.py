import unittest
import numpy as np
from analyze import conservation_budget
from solver import Solver, InvalidStateError, NG, PERIODIC, TRANSMIT, WALL, INJECTOR, OUTFLOW


class BudgetTests(unittest.TestCase):
    def test_native_open_boundary_fluxes_close_all_conserved_budgets(self):
        s = Solver(9, 4, .02, .03, (1.4, 10., 1., 3., 0.),
                   (TRANSMIT, TRANSMIT, INJECTOR, OUTFLOW),
                   inj=(140., 100., .2, .7), p_back=80.)
        x, z = np.meshgrid(np.arange(9), np.arange(4), indexing='ij')
        s.set_prim(1. + .01*x, 2. + .03*z, 3. + .02*x, 100. + x + 2*z, .2 + .01*z)
        initial = s.conserved_totals()
        for _ in range(12):
            s.step(dt_max=1e-5)
        current = s.conserved_totals()
        budget = conservation_budget(current, initial, s.cumulative_boundary,
                                     s.cumulative_source, .005, .0356)
        scale = np.maximum(np.abs(initial) * .005, 1e-12)
        self.assertLess(np.max(np.abs(budget['residual']) / scale), 3e-14)
        self.assertGreater(np.max(np.abs(budget['storage'])), 0.)
        self.assertGreater(s.cumulative_source[4], 0.)
        np.testing.assert_array_equal(s.cumulative_source[:4], np.zeros(4))
        self.assertAlmostEqual(budget['angular_storage'], budget['storage'][1] * .0356)
        self.assertLess(abs(budget['angular_residual']), 1e-14)
        # A flux from the final RK stage alone does not match the accepted update.
        last_stage = s.boundary_faces.sum(axis=2)
        last_stage[:2] *= s.dy
        last_stage[2:] *= s.dx
        self.assertGreater(np.max(np.abs(last_stage*s.last_step_budget['dt'] -
                                        s.last_step_budget['boundary'])), 1e-10)

    def test_rejected_stage_does_not_commit_budget_or_state(self):
        s = Solver(4, 1, .1, .1, (1.4, 10., 1., 1e10, 0.),
                   (PERIODIC, PERIODIC, WALL, WALL), source_cfl=None)
        s.set_prim(1., 0., 0., 100., .2)
        initial = s.U.copy()
        with self.assertRaises(InvalidStateError):
            s.step(dt_max=1e-6)
        np.testing.assert_array_equal(s.U, initial)
        np.testing.assert_array_equal(s.cumulative_boundary, np.zeros((4, 5)))
        np.testing.assert_array_equal(s.cumulative_source, np.zeros(5))
        self.assertEqual(s.steps, 0)
        self.assertIsNone(s.last_step_budget)

    def test_uniform_depth_changes_integrals_not_the_local_state(self):
        current = np.array([2., 3., 4., 5., 1.])
        initial = current*.8
        boundary = np.arange(20.).reshape(4, 5)
        source = np.zeros(5)
        thin = conservation_budget(current, initial, boundary, source, .003, .0356)
        wide = conservation_budget(current, initial, boundary, source, .007, .0356)
        for name in thin:
            np.testing.assert_allclose(wide[name], np.asarray(thin[name])*7/3)
