"""Independent source accuracy and boundary-plane checks; no engine campaign."""
import json
from pathlib import Path
import unittest
import numpy as np
from scipy.integrate import solve_ivp
from physics import PROGRESS_TOL, injector_state, injector_flux, reaction_rate, source_step_limit
from solver import Solver, InvalidStateError, PERIODIC, WALL, OUTFLOW, NG, fill_ghosts

CALIBRATION = json.loads((Path(__file__).resolve().parents[1]/'calib.json').read_text())


def reactor_case(T0, xi0, end, source_cfl):
    c=CALIBRATION
    g,q,R,k,Ea=(c[key] for key in ['gamma','q','R','k','Ea'])
    A=(g-1)*q/R
    # Independent scalar ODE: constant total energy implies T=T0+A*(xi-xi0).
    reference=solve_ivp(lambda t,y: [(1-y[0])*k*np.exp(-Ea/(R*(T0+A*(y[0]-xi0))))],
                        (0,end), [xi0], method='DOP853', rtol=2e-12, atol=2e-14, dense_output=True)
    if not reference.success:
        raise RuntimeError(reference.message)
    s=Solver(4,1,1.,1.,(g,q,R,k,Ea),(PERIODIC,PERIODIC,WALL,WALL),source_cfl=source_cfl)
    s.set_prim(1.,0.,0.,R*T0,xi0)
    initial=s.conserved_totals()
    history=[]
    while s.t<end:
        dt=s.step(dt_max=end-s.t)
        W=s.prim()
        progress=float(W[4,0,0])
        expected=float(reference.sol(s.t)[0])
        history.append([s.t,progress,expected,float(W[3,0,0]/R),dt])
    history=np.asarray(history)
    return s, history, initial


class ReactiveTests(unittest.TestCase):
    def test_arrhenius_reactor_accuracy_and_second_order_refinement(self):
        for T0,xi0,end in [(1000.,0.,30e-6),(2116.248966,.35,6e-6),(300.,0.,10e-6)]:
            errors=[]
            for fraction in [.1,.05,.025]:
                with self.subTest(T0=T0,xi0=xi0,source_cfl=fraction):
                    s,h,initial=reactor_case(T0,xi0,end,fraction)
                    error=float(np.max(np.abs(h[:,1]-h[:,2])))
                    errors.append(error)
                    self.assertLess(error,2e-4)
                    np.testing.assert_allclose(s.conserved_totals()[:4],initial[:4],rtol=2e-14,atol=1e-12)
                    self.assertEqual(s.invalid_state_count,0)
                    self.assertTrue(np.all(h[:,1]>=xi0-PROGRESS_TOL))
                    self.assertTrue(np.all(h[:,1]<=1+PROGRESS_TOL))
            if max(errors)>1e-10:
                self.assertGreater(errors[0]/errors[1],3.5)
                self.assertGreater(errors[1]/errors[2],3.5)

    def test_source_cap_is_independent_of_mesh_and_bounds_rate_slope(self):
        c=CALIBRATION
        g,q,R,k,Ea=(c[key] for key in ['gamma','q','R','k','Ea'])
        limit=source_step_limit(g,q,R,k,Ea,.05)
        T=np.geomspace(10.,30000.,200)
        for xi in [0.,.3,.99]:
            derivative=k*np.exp(-Ea/(R*T))*(-1+(1-xi)*Ea*(g-1)*q/(R*R*T*T))
            self.assertLessEqual(np.max(np.abs(derivative))*limit,.05)
        self.assertEqual(source_step_limit(g,q,R,0.,Ea,.05),np.inf)
        self.assertAlmostEqual(source_step_limit(g,q,R,5.,0.,.05),.01)
        for spacing in [1.,.1]:
            s=Solver(4,1,spacing,spacing,(g,q,R,k,Ea),(PERIODIC,PERIODIC,WALL,WALL))
            s.set_prim(1.,0.,0.,R*2000.,.2)
            self.assertEqual(s.step(),limit)

    def test_roundoff_is_tolerated_without_modifying_conserved_state(self):
        s=Solver(4,1,1.,1.,(1.4,10.,1.,0.,0.),(PERIODIC,PERIODIC,WALL,WALL))
        s.set_prim(1.,0.,0.,100.,1.)
        s.U[4,NG,NG]=np.nextafter(1.,2.)
        original=s.U.copy()
        W=s.prim()
        self.assertGreater(W[4,0,0],1.)
        np.testing.assert_array_equal(s.U,original)
        self.assertGreater(s.progress_roundoff_max,0.)
        self.assertEqual(reaction_rate(W[4,0,0],100.,1.,5.,0.),0.)
        s.U[4,NG,NG]=1.+1e-10
        with self.assertRaises(InvalidStateError):
            s.prim()

    def test_injector_plane_is_sonic_when_choked_and_accounts_for_face_pressure(self):
        p0,T0,R,g,q,sigma=1e6,300.,300.,1.4,5e6,.2
        pcr=p0*(2/(g+1))**(g/(g-1))
        for pw in [.2*p0,pcr,.9*p0]:
            pj,Tj,uj=injector_state(pw,p0,T0,R,g)
            mach=uj/np.sqrt(g*R*Tj)
            self.assertAlmostEqual(g*R/(g-1)*Tj+.5*uj**2,g*R/(g-1)*T0)
            if pw<=pcr:
                self.assertAlmostEqual(mach,1.)
                self.assertAlmostEqual(pj,pcr)
            else:
                self.assertLess(mach,1.)
                self.assertEqual(pj,pw)
            F=np.empty(5)
            injector_flux(pw,p0,T0,R,g,q,sigma,1.,F)
            rho=pj/(R*Tj)
            energy=pj/(g-1)+.5*rho*uj**2+rho*q
            expected=sigma*np.array([rho*uj,0,rho*uj**2+pj,(energy+pj)*uj,0.])
            expected[2]+=(1-sigma)*pw
            np.testing.assert_allclose(F,expected,rtol=3e-15)
        a=np.empty(5); b=np.empty(5)
        injector_flux(.2*p0,p0,T0,R,g,q,sigma,.76,a)
        injector_flux(.4*p0,p0,T0,R,g,q,sigma,.76,b)
        self.assertEqual(a[0],b[0])
        self.assertAlmostEqual(b[2]-a[2],(1-sigma)*.2*p0)

    def test_outlet_uses_axial_mach_even_with_large_swirl(self):
        for vz_over_a,swirl_over_a,expected in [(.5,10.,80.),(1.5,0.,100.),(-.5,10.,80.)]:
            W=np.zeros((5,8,7))
            a=np.sqrt(1.4*100.)
            W[0,NG:-NG,NG:-NG]=1.
            W[1,NG:-NG,NG:-NG]=swirl_over_a*a
            W[2,NG:-NG,NG:-NG]=vz_over_a*a
            W[3,NG:-NG,NG:-NG]=100.
            W[4,NG:-NG,NG:-NG]=.2
            fill_ghosts(W,PERIODIC,PERIODIC,WALL,OUTFLOW,80.,1.4)
            np.testing.assert_array_equal(W[3,NG:-NG,-NG:],expected)
            np.testing.assert_array_equal(W[2,NG:-NG,-NG:],vz_over_a*a)
