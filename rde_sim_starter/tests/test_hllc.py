"""Independent flux identities and contact preservation with chemical energy."""
import unittest
import numpy as np
from physics import total_energy
from solver import Solver, riemann, hll, PERIODIC, WALL, TRANSMIT


class HllcTests(unittest.TestCase):
    def test_contact_and_shear_flux_in_both_directions(self):
        for axis in [0, 1]:
            for normal in [-100., 0., 100.]:
                states=[]
                for rho,xi,tangent in [(4.,0.,20.),(.4,1.,-30.)]:
                    states.append([rho,normal if axis else tangent,
                                   tangent if axis else normal,5e5,xi])
                f=np.empty(5)
                riemann(*states[0],*states[1],axis,1.24,5.5e6,f,1)
                rho,u,v,p,xi=states[0 if normal>=0 else 1]
                expected=np.array([rho*normal,rho*u*normal,rho*v*normal,
                    (total_energy(rho,u,v,p,xi,1.24,5.5e6)+p)*normal,rho*xi*normal])
                expected[1 if axis else 2]+=p
                np.testing.assert_allclose(f,expected,rtol=3e-14,atol=2e-6)

    def test_supersonic_and_default_flux(self):
        for speed in [-4000.,4000.]:
            args=(4.,speed,20.,5e5,.1,1.,speed,-10.,1e5,.8,1,1.24,5.5e6)
            a=np.empty(5);b=np.empty(5);c=np.empty(5)
            hll(*args,a);riemann(*args,b,0);riemann(*args,c,1)
            np.testing.assert_array_equal(a,b)
            np.testing.assert_allclose(a,c,rtol=1e-15)

    def test_stationary_hot_cold_contact_no_artificial_mixing(self):
        s=Solver(2,32,.000125,.000125,(1.24,5.5e6,319.,0.,1.9e6),
                 (PERIODIC,PERIODIC,WALL,WALL),flux='hllc')
        temp=np.where(np.arange(32)<16,300.,3000.)[None,:]
        xi=np.where(np.arange(32)<16,0.,1.)[None,:]
        s.set_prim(5e5/(319*temp),0,0,5e5,xi)
        initial=s.U.copy()
        for _ in range(100):s.step(dt_max=1e-8)
        np.testing.assert_allclose(s.U,initial,rtol=5e-14,atol=1e-8)
        self.assertEqual(s.invalid_state_count,0)

    def test_unknown_flux_rejected(self):
        with self.assertRaisesRegex(ValueError,'flux'):
            Solver(2,2,1.,1.,(1.4,0.,1.,0.,0.),(0,0,0,0),flux='typo')

    def test_sod_exact_star_state_and_shock(self):
        n=400
        s=Solver(n,1,1/n,1/n,(1.4,0.,1.,0.,0.),
                 (TRANSMIT,TRANSMIT,WALL,WALL),flux='hllc')
        s.p_min=1e-9;x=(np.arange(n)+.5)/n
        s.set_prim(np.where(x<.5,1.,.125)[:,None],0,0,
                   np.where(x<.5,1.,.1)[:,None],0)
        while s.t<.2:s.step(dt_max=.2-s.t)
        w=s.prim();i=int(.75*n)
        self.assertAlmostEqual(w[3,i,0],.30313017805064685,delta=.003)
        self.assertAlmostEqual(w[1,i,0],.9274526200489499,delta=.005)
        self.assertAlmostEqual(x[np.flatnonzero(w[0,:,0]>.2)[-1]],.850431146406,delta=3/n)
        self.assertEqual(s.invalid_state_count,0)
