import copy
import json
from pathlib import Path
import unittest
import numpy as np
import yaml
from calibrate import calibrate, znd_profile
from physics import prim_to_cons_cell, cons_to_prim, reaction_rate, injector_flux, total_energy
from solver import Solver, PERIODIC, WALL


class PhysicsTests(unittest.TestCase):
    def test_chemical_energy_round_trip(self):
        U=np.zeros((5,5,5)); W=np.full_like(U,np.nan)
        prim_to_cons_cell(2.,4.,-3.,1e5,.2,1.4,3e6,U[:,2,2])
        self.assertAlmostEqual(U[3,2,2],1e5/.4+25.+2.*3e6*.8)
        cons_to_prim(U,W,1.4,3e6)
        np.testing.assert_allclose(W[:,2,2],[2,4,-3,1e5,.2],rtol=1e-13)
        self.assertTrue(np.isnan(W[:,0,0]).all())

    def test_one_step_source_limits(self):
        self.assertEqual(reaction_rate(1.,1000.,300.,2e6,2e6),0.)
        self.assertEqual(reaction_rate(0.,1000.,300.,0.,2e6),0.)
        self.assertAlmostEqual(reaction_rate(.25,1000.,300.,4.,0.),3.)

    def test_closed_reactor_timing_and_energy(self):
        # Ea=0 has the independent exact solution xi=1-exp(-k*t).
        s=Solver(4,1,1.,1.,(1.4,10.,1.,5.,0.),(PERIODIC,PERIODIC,WALL,WALL))
        s.set_prim(1.,0.,0.,100.,0.)
        initial_energy=s.U[3,2:-2,2:-2].copy()
        end=.1
        while s.t < end:
            s.step(dt_max=min(.002,end-s.t))
        W=s.prim()
        exact=1.-np.exp(-5.*end)
        np.testing.assert_allclose(W[4],exact,rtol=0,atol=6e-6)
        np.testing.assert_allclose(s.U[3,2:-2,2:-2],initial_energy,rtol=0,atol=1e-12)
        np.testing.assert_allclose(W[3],100.+.4*10.*W[4],rtol=1e-13)
        self.assertEqual(s.floor_hits,0)
        self.assertEqual(s.invalid_state_count,0)

    def test_injector_blocked_choked_and_unchoked(self):
        p0,T0,R,g,q,sigma,cd=1e6,300.,300.,1.4,5e6,.1,.8
        def flux(p):
            F=np.empty(5)
            injector_flux(p,p0,T0,R,g,q,sigma,cd,F)
            return F
        np.testing.assert_array_equal(flux(1.1*p0),[0,0,1.1*p0,0,0])
        critical=p0*(2/(g+1))**(g/(g-1))
        a,b=flux(.2*p0),flux(.4*p0)
        self.assertEqual(a[0],b[0])
        expected=sigma*cd*p0*np.sqrt(g/(R*T0))*(2/(g+1))**((g+1)/(2*(g-1)))
        self.assertAlmostEqual(a[0],expected)
        self.assertLess(flux(.9*p0)[0],a[0])
        self.assertGreater(flux(.9*p0)[0],0)
        self.assertAlmostEqual(flux(critical*(1-1e-8))[0],flux(critical*(1+1e-8))[0],places=10)
        self.assertAlmostEqual(a[3]/a[0],g*R/(g-1)*T0+q)

    def test_calibration_matches_inherited_reference_without_mutating_config(self):
        root=Path(__file__).resolve().parents[1]
        config=yaml.safe_load((root/'config.yaml').read_text())
        before=copy.deepcopy(config)
        reference=json.loads((root/'calib.json').read_text())
        actual=calibrate(config)
        for key in ['gamma','R','q','k','Ea','p1','L_half']:
            with self.subTest(key=key):
                np.testing.assert_allclose(actual[key],reference[key],rtol=2e-10)
        self.assertEqual(config,before)
        profile=znd_profile(actual,samples=8)
        self.assertTrue(np.all(np.diff(profile['distance']) > 0))
        self.assertEqual(profile['distance'][0],0)
