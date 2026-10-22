"""Short tests for the causal controls; full propagation remains an explicit run."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from plot import plot_controlled
from solver import Solver
from controlled import blast_strip, canonical_fields, run_strip

C=json.loads((Path(__file__).resolve().parents[1]/'calib.json').read_text())


class ControlledTests(unittest.TestCase):
    def test_coordinate_mapping_preserves_reactive_state(self):
        sx,x=blast_strip(C,rows=4,length=.05)
        sz,z=blast_strip(C,rows=4,length=.05,direction='z')
        np.testing.assert_array_equal(x,z)
        np.testing.assert_array_equal(canonical_fields(sx,'x'),canonical_fields(sz,'z'))
        # Nonzero momentum is needed to make swapped-component mistakes observable.
        sx.set_prim(2.,123.,-45.,1e6,.3);sz.set_prim(2.,-45.,123.,1e6,.3)
        np.testing.assert_array_equal(canonical_fields(sx,'x'),canonical_fields(sz,'z'))
        for kwargs in [dict(rows=0),dict(direction='bad'),dict(dx=0),dict(direction='z',open_end=True)]:
            with self.assertRaises(ValueError):blast_strip(C,**kwargs)

    def test_multistep_reactive_control_is_symmetric_and_conservative(self):
        original=copy.deepcopy(C)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'strip'
            r=run_strip(C,out,rows=4,end=.2e-6,length=.05)
            self.assertTrue(r['control_passed'])
            self.assertGreater(r['steps'],10)
            self.assertLess(r['max_budget_scaled_residual'],1e-12)
            self.assertEqual(r['invalid_state_count'],[0,0,0,0])
            self.assertEqual(C,original)
            with np.load(out/'fields.npz') as a:
                self.assertGreater(np.max(np.abs(a['primitive'][-1]-a['primitive'][0])),0)
            with patch.object(Solver,'step',side_effect=AssertionError('render ran CFD')):
                plot_controlled(out,Path(tmp)/'plots')
            self.assertGreater((Path(tmp)/'plots/strip_control.png').stat().st_size,1000)
            with self.assertRaises(FileExistsError):run_strip(C,out,end=.2e-6)
            with self.assertRaises(ValueError):run_strip(C,Path(tmp)/'bad',end=1.)
