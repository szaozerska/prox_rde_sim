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


class FormedProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from controlled import formed_profile
        cls.profile=formed_profile(C)

    def test_jump_invariants_and_finite_tail(self):
        p=self.profile;v=p['verification']
        self.assertLess(max(v['jump_max_relative_error']),1e-8)
        self.assertAlmostEqual(v['length_m']['0.5'],C['L_half'],places=11)
        self.assertLess(max(abs(e) for e in v['table_length_relative_error'].values()),1e-4)
        self.assertLess(v['tail_pressure_relative_jump'],.002)
        self.assertTrue(np.all(np.diff(p['distance'])>0))
        r=p['U'][0];u=p['U'][1]/r
        self.assertGreater(u.min(),100.)
        self.assertGreater(np.max(abs(r/p['fresh'][0]-1)),1.)

    def test_conservative_cell_integrals_and_profile_refinement(self):
        from scipy.integrate import quad_vec
        from controlled import formed_strip,formed_profile,profile_integral,profile_cell_average
        from solver import NG
        p=self.profile;totals=[]
        for dx in (.5e-3,.25e-3,.125e-3):
            s,x=formed_strip(C,p,dx=dx,length=.1,shock=.04137)
            totals.append(s.conserved_totals()/(s.ny*s.dy))
            self.assertGreater(s.prim()[3].min(),0)
        np.testing.assert_allclose(totals,np.broadcast_to(totals[0],(3,5)),rtol=2e-12,atol=1e-9)
        lo=-.00013;hi=.00143;points=p['distance'][(p['distance']>lo)&(p['distance']<hi)]
        def exact(x):
            if x<0:return p['fresh']
            return np.array([np.interp(x,p['distance'],a) for a in p['U']])
        reference=quad_vec(exact,lo,hi,points=np.r_[0,points],epsabs=1e-7)[0]
        integrated=profile_cell_average(p,np.array([lo]),np.array([hi]))[:,0]*(hi-lo)
        np.testing.assert_allclose(integrated,reference,rtol=1e-11,atol=1e-9)
        fine=formed_profile(C,4801);intervals=np.linspace(-.002,.03,81)
        a=profile_cell_average(p,intervals[:-1],intervals[1:]);b=profile_cell_average(fine,intervals[:-1],intervals[1:])
        scales=np.array([p['fresh'][0],p['fresh'][0]*C['D_CJ'],1,C['CJ']['p']/(C['gamma']-1)+p['fresh'][0]*C['q'],p['fresh'][0]])[:,None]
        self.assertLess(np.max(abs(a-b)/scales),1e-4)
        burned=profile_cell_average(p,np.array([.1]),np.array([.1005]))[:,0]
        self.assertEqual(burned[0],burned[4])
        with self.assertRaises(ValueError):profile_cell_average(p,np.array([1.]),np.array([0.]))

    def test_formed_multistep_budgets_and_causal_accounting(self):
        from controlled import run_formed
        with tempfile.TemporaryDirectory() as tmp:
            result=run_formed(C,Path(tmp)/'formed',end=.2e-6,profile=self.profile)
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['invalid_state_count'],0)
            self.assertLess(result['max_budget_scaled_residual'],1e-12)
            self.assertGreater(result['history'][-1]['converted_J_per_m_depth'],0)
            self.assertGreater(result['history'][-1]['left_causal_margin_m'],0)
            self.assertGreater(result['history'][-1]['right_causal_margin_m'],0)
            self.assertEqual(result['history'][-1]['transverse_max_scaled'],0)
            with patch.object(Solver,'step',side_effect=AssertionError('render ran CFD')):
                plot_controlled(Path(tmp)/'formed',Path(tmp)/'plots')
            self.assertGreater((Path(tmp)/'plots/formed_control.png').stat().st_size,1000)
            with self.assertRaises(ValueError):run_formed(C,Path(tmp)/'bad',end=1.)
