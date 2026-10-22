"""Fast initializer and benchmark checks; none asserts sustained detonation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from calibrate import calibrate
from controlled import formed_profile
from detwave_initialization import periodic_charge_average, initialize_engine
import run
from solver import NG, Solver
from tests.test_run import toy_case, records


def formed_case():
    config,_=toy_case()
    config['model']['chemistry']='one_step'
    config['chemistry']['L_half_mm']=.25
    config['initialization']=dict(kind='formed',fill_height_mm=3.8,
        charge_length_mm=20.,shock_fraction=.02,product_temperature_K=1500.)
    config['numerics'].update(snapshot_every_us=.02,checkpoint_every_us=.02)
    return config,calibrate(config)


class FormedEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config,cls.c=formed_case()
        cls.profile=formed_profile(cls.c)

    def build(self,config=None):
        r=run.resolve_case(config or self.config,self.c)
        s=run.build_solver(r,self.c,initialize=False)
        initialize_engine(s,r,self.c)
        return s,r

    def test_lab_momentum_and_energy_match_normal_shock_relations(self):
        c=self.c;g=c['gamma'];M2=c['D_CJ']**2/(g*c['R']*c['T1'])
        rho=c['p1']/(c['R']*c['T1'])*(g+1)*M2/((g-1)*M2+2)
        pressure=c['p1']*(2*g*M2-(g-1))/(g+1)
        u=c['D_CJ']*(1-c['p1']/(c['R']*c['T1'])/rho)
        expected=[rho,rho*u,0,pressure/(g-1)+.5*rho*u*u+rho*c['q'],0]
        np.testing.assert_allclose(self.profile['U'][:,0],expected,rtol=1e-10,atol=1e-10)  # allows the existing scalar root-solve tolerance

    def test_periodic_cell_integrals_against_independent_piecewise_quadrature(self):
        from scipy.integrate import quad_vec
        p=self.profile;circ=.031;charge=.02;shock=.00031
        edges=np.linspace(0,circ,24)
        actual=periodic_charge_average(p,edges,shock,charge,circ)
        # Direct interpolation in physical x, with explicit jumps/knots as quad points.
        def value(x):
            d=(shock-x)%circ
            if d>charge:return p['fresh']
            if d>p['distance'][-1]:return p['burned']
            return np.array([np.interp(d,p['distance'],a) for a in p['U']])
        knots=np.sort(np.mod(shock-np.r_[p['distance'],charge],circ))
        for i,(a,b) in enumerate(zip(edges[:-1],edges[1:])):
            expected=quad_vec(value,a,b,points=knots[(knots>a)&(knots<b)],epsabs=1e-8)[0]/(b-a)
            np.testing.assert_allclose(actual[:,i],expected,rtol=2e-11,atol=1e-8)

    def test_arbitrary_phase_and_mesh_preserve_all_five_inventories(self):
        totals=[]
        for spacing,phase in [(2.,.02),(1.,.87),(.5,0.)]:
            cfg=copy.deepcopy(self.config);cfg['numerics']['dx_mm']=spacing
            cfg['initialization']['shock_fraction']=phase
            s,r=self.build(cfg);totals.append(s.conserved_totals()*r['gap'])
            self.assertGreater(s.prim()[3].min(),0.)
            self.assertLess(r['formed_initialization']['inventory_max_scaled_error'],1e-12)
            self.assertGreater(r['initialization_energy_change_J'],0.)
            self.assertEqual(s.conserved_totals()[2],0.)
            # Thermal energy is reconstructed after removing kinetic and unspent chemical energy.
            w=s.prim();U=s.U[:,NG:-NG,NG:-NG]
            expected=U[3]-.5*(U[1]**2+U[2]**2)/U[0]-self.c['q']*(U[0]-U[4])
            np.testing.assert_allclose(w[3]/(self.c['gamma']-1),expected,rtol=1e-13)
        np.testing.assert_allclose(totals,np.broadcast_to(totals[0],(3,5)),rtol=1e-12,atol=1e-11)

    def test_seam_translation_commutes_with_initialization_and_flow_steps(self):
        a,r=self.build();cfg=copy.deepcopy(self.config)
        cfg['initialization']['shock_fraction']+=3/r['nx']
        b,_=self.build(cfg)
        for _ in range(3):
            np.testing.assert_allclose(np.roll(a.U[:,NG:-NG,NG:-NG],3,axis=1),
                                       b.U[:,NG:-NG,NG:-NG],rtol=1e-12,atol=1e-8)
            a.step(dt_max=1e-9);b.step(dt_max=1e-9)
        # A translated state samples a different flux at the seam. Its net periodic
        # contribution must vanish; integrated injector/outlet fluxes are invariant.
        for solver in (a,b):
            np.testing.assert_allclose(solver.cumulative_boundary[0],solver.cumulative_boundary[1],rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(a.cumulative_boundary[2:],b.cumulative_boundary[2:],rtol=1e-12,atol=1e-12)

