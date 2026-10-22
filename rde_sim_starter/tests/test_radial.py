"""Independent radial quadrature, coupled ODE, budgets and persistence tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.integrate import quad, solve_ivp
from radial import pressure_ratios, annular_rhs, resolve_radial, wall_pressures
from solver import Solver, NG, PERIODIC, WALL
from physics import wall_drag_rhs
import run
from contracts import iter_fields
from workflow import collect_workflow
from test_run import toy_case


def spec(centrifugal=True, cf=.005, analogy=1., temperature=300.):
    return dict(centrifugal=centrifugal,inner=dict(cf=cf,temperature_K=temperature),
        outer=dict(cf=cf,temperature_K=temperature),analogy_factor=analogy,recovery_factor=.9)


def params(**kwargs):
    return np.array(resolve_radial(dict(walls='annular_closure',radial=spec(**kwargs)),.0331,.0381))


def box(par, dt=None, end=20e-6, gas=(1.4,0.,287.,0.,0.), temperature=800.):
    s=Solver(4,2,1.,1.,gas,(PERIODIC,PERIODIC,WALL,WALL),radial=par)
    s.set_prim(1.,600.,0.,gas[2]*temperature,.2)
    initial=s.conserved_totals()
    if dt:
        while s.t<end:s.step(min(dt,end-s.t))
    return s,initial


class RadialTests(unittest.TestCase):
    def test_radial_equilibrium_volume_mean_and_gradient_independent_quadrature(self):
        ri,ro=.0331,.0381
        for beta in [0.,1e-8,.2,2.,20.,200.]:
            fi,fo=pressure_ratios(beta,ri,ro)
            # Construct from the outer endpoint, independently integrate r dr.
            p=lambda r:fo*(r/ro)**beta
            mean=quad(lambda r:2*r*p(r)/(ro*ro-ri*ri),ri,ro,epsabs=1e-12)[0]
            self.assertAlmostEqual(mean,1.,delta=2e-13)
            self.assertAlmostEqual(p(ri),fi,delta=2e-13)
            rm=(ri+ro)/2; h=1e-7
            self.assertAlmostEqual((p(rm+h)-p(rm-h))/(2*h),beta*p(rm)/rm,delta=1e-6)
        self.assertEqual(pressure_ratios(0.,ri,ro),(1.,1.))
        fi,fo=pressure_ratios(2.,1.,1.00001)
        self.assertAlmostEqual(fo-fi,2*1e-5/1.000005,delta=1e-14)
        with self.assertRaises(ValueError):pressure_ratios(1e6,ri,ro)

    def test_disabled_losses_leave_centifugal_observer_bitwise_inert(self):
        off,_=box(params(cf=0,centrifugal=False),1e-6)
        on,_=box(params(cf=0,centrifugal=True),1e-6)
        baseline=Solver(4,2,1.,1.,(1.4,0.,287.,0.,0.),(PERIODIC,PERIODIC,WALL,WALL))
        baseline.set_prim(1.,600.,0.,287*800.,.2)
        while baseline.t<20e-6:baseline.step(min(1e-6,20e-6-baseline.t))
        np.testing.assert_array_equal(off.U,on.U)
        np.testing.assert_array_equal(on.U,baseline.U)
        self.assertTrue(np.all(on.cumulative_source==0))
        pi,po=wall_pressures(on.prim(),on.radial)
        self.assertTrue(np.all(pi<on.prim()[3]));self.assertTrue(np.all(po>on.prim()[3]))

    def test_uniform_pressure_two_wall_drag_reduces_to_existing_closure(self):
        s,_=box(params(centrifugal=False,analogy=0))
        s.prim(); a=np.zeros_like(s.U); b=np.zeros_like(a)
        integ,_=annular_rhs(s.W,a,s.radial,s.g,s.R,NG,1.)
        old=wall_drag_rhs(s.W,b,.005/.005,NG,1.)
        np.testing.assert_allclose(a,b,atol=1e-10,rtol=2e-15)
        np.testing.assert_allclose(integ.sum(axis=0),[old[0],old[1],0],atol=1e-8,rtol=2e-15)
        self.assertAlmostEqual(integ[1,0]/integ[0,0],.0381/.0331)

    def test_coupled_drag_cooling_reaction_matches_independent_ode_and_second_order(self):
        # Independent quadrature normalization, full energy ODE, Arrhenius reaction.
        gas=(1.4,2e5,287.,2e4,2e6);g,q,R,k,Ea=gas;par=params(cf=.08)
        ri,ro=par[:2];areas=2*np.array([ri,ro])/(ro*ro-ri*ri)
        u0,T0,xi0=600.,800.,.2
        E0=R*T0/(g-1)+u0*u0/2+q*(1-xi0);cp=g*R/(g-1)
        def ode(t,y):
            u,E,xi=y;T=(g-1)/R*(E-u*u/2-q*(1-xi));beta=u*u/(R*T)
            norm=quad(lambda radius:2*radius*(radius/ro)**beta/(ro*ro-ri*ri),ri,ro)[0]
            ratios=np.array([(ri/ro)**beta,1.])/norm
            rate=np.sum(areas*ratios*.5*.08*abs(u))
            return [-rate*u,-rate*cp*(T+.9*u*u/(2*cp)-300.),(1-xi)*k*np.exp(-Ea/(R*T))]
        end=200e-6
        ref=solve_ivp(ode,(0,end),[u0,E0,xi0],method='DOP853',rtol=2e-12,atol=2e-12)
        self.assertTrue(ref.success)
        errors=[]
        for dt in [.5e-6,.25e-6,.125e-6]:
            s,initial=box(par,dt,end,gas)
            y=s.U[[1,3,4],NG,NG]
            errors.append(np.linalg.norm((y-ref.y[:,-1])/[u0,E0,1]))
            np.testing.assert_allclose(s.conserved_totals()-initial,s.cumulative_source,atol=2e-8,rtol=1e-11)
            np.testing.assert_allclose(s.cumulative_source[1:4],s.cumulative_wall_sources.sum(axis=0),atol=1e-8,rtol=2e-14)
            self.assertLess(s.cumulative_source[3],0.)
            self.assertEqual(s.invalid_state_count,0)
        self.assertLess(errors[-1],2e-7)
        self.assertGreater(errors[0]/errors[1],3.7);self.assertGreater(errors[1]/errors[2],3.7)

    def test_heat_sign_reversal_adiabatic_energy_and_stiff_cooling_cap(self):
        for temp,sign in [(300.,-1),(2000.,1)]:
            s,_=box(params(temperature=temp),1e-6)
            self.assertGreater(sign*s.cumulative_source[3],0)
        s,initial=box(params(analogy=0),1e-6)
        self.assertEqual(s.cumulative_source[3],0)
        self.assertEqual(s.conserved_totals()[3],initial[3])
        s,_=box(params(cf=100.,analogy=100.))
        dt=s.step(1e-3)
        self.assertLess(dt,1e-9);self.assertGreater(s.prim()[3].min(),0.)
        s.set_prim(1.,0.,0.,287*800.,.2);s.step(1e-6)
        self.assertTrue(np.all(s.last_step_budget['source']==0))

    def test_validation_rejects_ignored_options_and_missing_coefficients(self):
        config,cal=toy_case()
        for edit in [dict(walls='inviscid',radial=spec()),dict(walls='annular_closure'),
                     dict(walls='annular_closure',wall_cf=.01,radial=spec())]:
            c=copy.deepcopy(config);c['model'].update(edit)
            with self.assertRaises(ValueError):run.resolve_case(c,cal)
        for key,value in [('centrifugal',1),('recovery_factor',2),('analogy_factor',True),('unknown',1)]:
            bad=spec();bad[key]=value
            with self.assertRaises(ValueError):resolve_radial(dict(walls='annular_closure',radial=bad),.0331,.0381)

    def test_restart_per_wall_budget_fields_reports_and_corruption(self):
        config,cal=toy_case();config['model'].update(walls='annular_closure',radial=spec())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run';run.start_run(config,cal,path);run.resume_run(path)
            s,r,_,_=run._load_checkpoint(path)
            rows=[json.loads(line) for line in (path/'history.jsonl').read_text().splitlines()]
            replay=run.build_solver(r,cal)
            for row in rows[1:]:replay.step(row['dt'])
            np.testing.assert_array_equal(s.U,replay.U)
            np.testing.assert_array_equal(s.cumulative_wall_sources,replay.cumulative_wall_sources)
            np.testing.assert_allclose(s.cumulative_wall_sources*r['gap'],np.sum([a['radial_wall_integral'] for a in rows[1:]],axis=0),atol=1e-17)
            report=collect_workflow(path,.055e-6,.45e-6)['report']
            self.assertTrue(report['budgets']['closure_within_tolerance'])
            self.assertTrue(report['radial_physics']['centrifugal_pressure_split'])
            self.assertTrue(report['radial_physics']['heat_loss'])
            self.assertTrue(report['radial_wall_exchange']['available'])
            self.assertLess(abs(report['engine_torque']['traction_minus_balance_Nm']),1e-10)
            inputs=json.loads((path/'inputs.json').read_text())
            frames=list(iter_fields(path,inputs,s.steps))
            self.assertIn('inner_pressure',frames[-1])
            self.assertTrue(np.all(frames[-1]['outer_pressure']>=frames[-1]['inner_pressure']))
            file=sorted((path/'fields').glob('*.npz'))[-1]
            with np.load(file) as z:arrays={k:z[k] for k in z.files}
            arrays['inner_pressure'][0,0]=-1.;np.savez(file,**arrays)
            with self.assertRaises(ValueError):list(iter_fields(path,inputs,s.steps))

    def test_asymmetric_walls_and_actual_lever_arms(self):
        par=params(centrifugal=False);par[3]=.003;par[5]=.009;par[4]=1400.;par[6]=300.
        s,_=box(par);s.prim();out=np.zeros_like(s.U)
        integrals,_=annular_rhs(s.W,out,par,s.g,s.R,NG,1.)
        ri,ro=par[:2];volume=8.;cp=s.g*s.R/(s.g-1)
        for wall,(radius,cf,Tw) in enumerate([(ri,.003,1400.),(ro,.009,300.)]):
            a=2*radius/(ro*ro-ri*ri)
            self.assertAlmostEqual(integrals[wall,0],-a*.5*cf*600**2*volume,delta=1e-8)
            expected=-a*.5*cf*600*cp*(800+.9*600**2/(2*cp)-Tw)*volume
            self.assertAlmostEqual(integrals[wall,2],expected,delta=1e-5)
        self.assertGreater(integrals[0,2],0);self.assertLess(integrals[1,2],0)
        gap=ro-ri
        actual=-gap*np.dot([ri,ro],integrals[:,0])
        # Actual cylinder areas for a 4 m circumference at mean radius and 2 m length.
        rm=(ri+ro)/2
        expected=sum(radius*(radius/rm*8)*.5*cf*600**2 for radius,cf in [(ri,.003),(ro,.009)])
        self.assertAlmostEqual(actual,expected,delta=1e-8)
