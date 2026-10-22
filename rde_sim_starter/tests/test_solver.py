import json
import os
from pathlib import Path
import unittest
import numpy as np
from solver import Solver, InvalidStateError, fill_ghosts, hll, NG, PERIODIC, REFLECT, TRANSMIT, WALL


def uniform_solver(**kwargs):
    s=Solver(8,1,.1,.1,(1.4,10.,1.,0.,0.),(PERIODIC,PERIODIC,WALL,WALL),**kwargs)
    s.set_prim(1.,0.,0.,100.,.25)
    return s


def sod_case(n=400):
    s=Solver(n,1,1./n,1./n,(1.4,0.,1.,0.,0.),(TRANSMIT,TRANSMIT,WALL,WALL))
    s.p_min=1e-9
    x=(np.arange(n)+.5)/n
    rho=np.where(x<.5,1.,.125)[:,None]
    p=np.where(x<.5,1.,.1)[:,None]
    s.set_prim(rho,0.,0.,p,0.)
    while s.t < .2:
        s.step(dt_max=.2-s.t)
    return s,x,s.prim().copy()


class SolverTests(unittest.TestCase):
    def test_uniform_state_and_zero_ghost_storage(self):
        s=uniform_solver()
        expected=s.prim().copy()
        self.assertTrue(np.all(s.U[:,:NG,:] == 0))
        s.U[:,:NG,:]=np.nan  # unused conservative ghost storage must not be converted
        s.step(dt_max=1e-5)
        np.testing.assert_allclose(s.prim(),expected,rtol=1e-14)
        self.assertTrue(np.isfinite(s.W).all())

    def test_invalid_conserved_states_rejected_before_division(self):
        for component,value in [(0,0.),(0,-1.),(0,np.nan),(1,np.inf),(2,-np.inf),(3,np.nan),(4,np.inf),(3,-10.),(4,-.1),(4,1.1)]:
            with self.subTest(component=component,value=value):
                s=uniform_solver()
                s.U[component,NG,NG]=value
                with self.assertRaises(InvalidStateError):
                    s.step()
                self.assertEqual(s.t,0)
                self.assertEqual(s.invalid_state_count,1)
                self.assertEqual(s.last_failure['stage'],'step input')
                self.assertEqual(s.floor_hits,0)

    def test_invalid_initial_primitives_leave_state_intact(self):
        s=uniform_solver(); original=s.U.copy()
        for r,p,xi in [(0,100,0),(-1,100,0),(1,-1,0),(1,100,1.1),(1,100,np.nan)]:
            with self.subTest(r=r,p=p,xi=xi),self.assertRaises(InvalidStateError):
                s.set_prim(r,0.,0.,p,xi)
            np.testing.assert_array_equal(s.U,original)

    def test_rejected_reaction_stage_is_atomic(self):
        s=uniform_solver()
        s.k=1e8
        original=s.U.copy()
        with self.assertRaises(InvalidStateError) as caught:
            s.step(dt_max=1e-4)
        self.assertEqual(caught.exception.stage,'RK stage 1')
        np.testing.assert_array_equal(s.U,original)
        self.assertEqual(s.t,0.)
        s.k=0
        s.step(dt_max=1e-5)
        self.assertEqual(s.t,1e-5)

    def test_bounded_time_step(self):
        s=uniform_solver()
        self.assertEqual(s.step(dt_max=3e-8),3e-8)
        self.assertEqual(s.t,3e-8)
        for bad in [0,-1,np.inf,np.nan]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                s.step(dt_max=bad)

    def test_unpaired_periodic_boundaries_rejected(self):
        for boundaries in [(PERIODIC,TRANSMIT,WALL,WALL),(TRANSMIT,PERIODIC,WALL,WALL)]:
            with self.assertRaisesRegex(ValueError,'paired'):
                Solver(8,1,.1,.1,(1.4,0.,1.,0.,0.),boundaries)

    def test_ghost_boundary_values(self):
        for left,right in [(PERIODIC,PERIODIC),(TRANSMIT,REFLECT),(REFLECT,TRANSMIT)]:
            W=np.zeros((5,8,5))
            for i in range(4):
                W[:,NG+i,NG]=[i+1.,i+.5,0.,100+i,.25]
            fill_ghosts(W,left,right,WALL,WALL,100.,1.4)
            self.assertTrue(np.all(W[0] > 0))  # includes the single-row wall/corner ghosts
            for layer in range(NG):
                li=NG+3-layer if left==PERIODIC else NG+layer if left==REFLECT else NG
                ri=NG+layer if right==PERIODIC else NG+3-layer if right==REFLECT else NG+3
                for ghost,src,reflect in [(NG-1-layer,li,left==REFLECT),(NG+4+layer,ri,right==REFLECT)]:
                    expected=W[:,src,NG].copy()
                    if reflect:
                        expected[1]*=-1
                    np.testing.assert_array_equal(W[:,ghost,NG],expected)

    def test_hll_uniform_flux_and_normal_direction(self):
        for direction in [0,1]:
            F=np.empty(5)
            hll(2.,3.,4.,100.,.25,2.,3.,4.,100.,.25,direction,1.4,10.,F)
            normal=3. if direction==1 else 4.
            energy=100./.4+.5*2.*25.+2.*10.*.75
            expected=np.array([2.*normal,6.*normal,8.*normal,(energy+100.)*normal,.5*normal])
            expected[1 if direction==1 else 2]+=100.
            np.testing.assert_allclose(F,expected,rtol=1e-14)

    def test_periodic_nonreacting_conservation(self):
        n=32
        s=Solver(n,1,1./n,.1,(1.4,10.,1.,0.,0.),(PERIODIC,PERIODIC,WALL,WALL))
        x=(np.arange(n)+.5)/n
        rho=(1.+.1*np.sin(2*np.pi*x))[:,None]
        xi=(.3+.1*np.cos(2*np.pi*x))[:,None]
        s.set_prim(rho,.3,0.,100.,xi)
        before=s.U[:,NG:-NG,NG:-NG].sum(axis=(1,2))
        for _ in range(20):
            s.step(dt_max=1e-4)
        after=s.U[:,NG:-NG,NG:-NG].sum(axis=(1,2))
        np.testing.assert_allclose(after,before,rtol=5e-14,atol=1e-12)
        self.assertEqual(s.invalid_state_count,0)

    def test_sod_against_exact_star_state_and_shock_location(self):
        s,x,W=sod_case()
        i=int(.75*x.size)
        # Independent exact Riemann solution for the standard nondimensional Sod data.
        self.assertAlmostEqual(W[3,i,0],.30313017805064685,delta=3e-3)
        self.assertAlmostEqual(W[1,i,0],.9274526200489499,delta=5e-3)
        shock=x[np.where(W[0,:,0]>.2)[0].max()]
        self.assertAlmostEqual(shock,.850431146406,delta=3./x.size)
        self.assertEqual(s.t,.2)
        self.assertEqual(s.invalid_state_count,0)
        self.assertEqual(s.floor_hits,0)

    @unittest.skipUnless(os.environ.get('RDE_RUN_REACTIVE_BASELINE')=='1','95 us inherited detonation check is opt-in; not part of the fast suite')
    def test_inherited_detonation_baseline(self):
        c=json.loads((Path(__file__).resolve().parents[1]/'calib.json').read_text())
        g,q,R,k,Ea=(c[name] for name in ['gamma','q','R','k','Ea'])
        dx=.25e-3; n=1000
        s=Solver(n,1,dx,dx,(g,q,R,k,Ea),(REFLECT,TRANSMIT,WALL,WALL))
        x=(np.arange(n)+.5)*dx
        p=np.full((n,1),c['p1']); r=np.full((n,1),c['p1']/(R*c['T1'])); xi=np.zeros((n,1))
        hot=x<.01
        p[hot]=2*c['CJ']['p']; r[hot]=p[hot]/(R*c['CJ']['T']); xi[hot]=1.
        s.set_prim(r,0.,0.,p,xi)
        ts,xs=[],[]
        while s.t<95e-6:
            s.step(dt_max=95e-6-s.t)
            indices=np.flatnonzero(s.prim()[3,:,0]>2*c['p1'])
            if s.t>40e-6 and indices.size:
                ts.append(s.t); xs.append(x[indices[-1]])
        self.assertGreater(len(ts),20)
        speed=np.polyfit(ts,xs,1)[0]
        self.assertLess(abs(speed/c['D_CJ']-1),.03)
        self.assertEqual(s.invalid_state_count,0)
