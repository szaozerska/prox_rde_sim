"""Contact controls check conservative initialization and isolate source activation."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from experiments import contact_exact, run_contact
from plot import plot_experiments
from solver import Solver
from test_1d import detonation_case

CALIBRATION=json.loads((Path(__file__).resolve().parents[1]/'calib.json').read_text())


class ExperimentTests(unittest.TestCase):
    def test_contact_average_is_mass_weighted_and_translates(self):
        # Half a hot cell (rho=1) and half a cold cell (rho=5): xi=1/6, not 1/2.
        x=np.array([-1.,0.,1.])
        rho,xi=contact_exact(x,1.,0.,0.,2.,1500.,300.,1500.,1.)
        np.testing.assert_allclose(rho,[1.,3.,5.])
        np.testing.assert_allclose(rho*xi,[1.,.5,0.])
        shifted=contact_exact(x+2.,1.,1.,0.,2.,1500.,300.,1500.,1.)
        np.testing.assert_allclose(shifted,(rho,xi))
        for bad in [np.array([np.nan]),np.zeros((2,2))]:
            with self.assertRaises(ValueError):
                contact_exact(bad,1.,0.,0.,0.,1500.,300.,1500.,1.)

    def test_frozen_contact_and_reactive_control_preserve_budgets_and_inputs(self):
        c=copy.deepcopy(CALIBRATION);original=copy.deepcopy(c)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            frozen=run_contact(c,root/'frozen',dx=1e-3,end=2e-6,reactive=False)
            active=run_contact(c,root/'active',dx=1e-3,end=2e-6,reactive=True)
            self.assertEqual(c,original)
            self.assertEqual(frozen['final']['conversion_J_m2'],0.)
            self.assertLess(frozen['final']['pressure_departure'],1e-12)
            self.assertGreater(active['final']['conversion_J_m2'],1.)
            for result in [frozen,active]:
                self.assertEqual(result['status'],'completed')
                self.assertEqual(result['invalid_state_count'],0)
                self.assertLess(result['max_budget_scaled_residual'],1e-12)
            inputs=[json.loads((root/name/'inputs.json').read_text()) for name in ['frozen','active']]
            self.assertEqual(inputs[0]['common_max_step_s'],inputs[1]['common_max_step_s'])
            self.assertEqual(inputs[0]['calibration'],inputs[1]['calibration'])
            with self.assertRaises(FileExistsError):
                run_contact(c,root/'frozen',dx=1e-3,end=2e-6,reactive=False)
            cases=[dict(directory=name,dx_m=1e-3,reactive=reactive,summary=result)
                   for name,reactive,result in [('frozen',False,frozen),('active',True,active)]]
            (root/'summary.json').write_text(json.dumps(dict(kind='contact',status='completed',cases=cases)))
            before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
            with patch.object(Solver,'step',side_effect=AssertionError('plot ran CFD')):
                plot_experiments(root,root/'plots')
            self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
            for name in ['contact_profiles.png','contact_refinement.png']:
                self.assertGreater((root/'plots'/name).stat().st_size,1000)

    def test_spatial_change_preserves_chemistry_and_physical_domain(self):
        for dx in [.5e-3,.25e-3,.125e-3]:
            solver,x=detonation_case(CALIBRATION,dx=dx)
            self.assertAlmostEqual(solver.nx*solver.dx,.25)
            self.assertEqual((solver.g,solver.q,solver.R,solver.k,solver.Ea),tuple(CALIBRATION[k] for k in ['gamma','q','R','k','Ea']))
            self.assertAlmostEqual(np.count_nonzero(x<.01)*solver.dx,.01)
        for dx in [0.,np.nan,-1.]:
            with self.assertRaises(ValueError):detonation_case(CALIBRATION,dx=dx)
