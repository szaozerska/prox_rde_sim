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


class LayerControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from controlled import formed_profile
        cls.profile=formed_profile(C)

    def test_layer_inventory_is_mesh_independent(self):
        from controlled import formed_layer
        totals=[];excess=[]
        for dx in (.5e-3,.25e-3,.125e-3):
            s,x,z,info=formed_layer(C,self.profile,.0038,dx=dx,length=.1,shock=.04137,buffer=.002)
            totals.append(s.conserved_totals());excess.append(info['initial_excess_over_unignited_layer'])
            self.assertAlmostEqual(info['initial_layer_volume_m2'],.0038*.1,places=15)
            self.assertEqual(info['interface_mixed_row_count'],1)
            self.assertGreater(s.prim()[3].min(),0.)
        for collection in [totals,excess]:np.testing.assert_allclose(collection,np.broadcast_to(collection[0],(3,5)),rtol=2e-11,atol=1e-8)
        for h in (0.,.031,np.nan):
            with self.assertRaises(ValueError):formed_layer(C,self.profile,h)

    def test_layer_row_metrics_distinguish_reaction_and_pressure(self):
        from controlled import formed_layer,row_front_metrics
        s,x,z,info=formed_layer(C,self.profile,.0038,length=.1,shock=.04137,buffer=.002)
        w=s.prim();row=row_front_metrics(w[:,:,0],x,C)
        self.assertIsNotNone(row['front_m']);self.assertGreater(row['rate_peak_per_s'],1e5)
        self.assertLess(row['front_rate_separation_m'],.004)
        hot=row_front_metrics(w[:,:,-1],x,C)
        self.assertIsNone(hot['front_m']);self.assertEqual(hot['near_front_heat_W_per_m2'],0.)
        self.assertAlmostEqual(hot['pressure_max_Pa'],C['p1'],places=7)

    def test_layer_driver_preserves_budgets_and_renders_saved_fields(self):
        from controlled import run_layer
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'layer';r=run_layer(C,out,.0038,end=.03e-6,profile=self.profile)
            self.assertEqual(r['status'],'completed')
            self.assertEqual(r['invalid_state_count'],0)
            self.assertLess(r['max_budget_scaled_residual'],1e-12)
            self.assertGreater(r['steps'],1)
            self.assertEqual(len(r['history'][-1]['rows']),3)
            with patch.object(Solver,'step',side_effect=AssertionError('render ran CFD')):
                plot_controlled(out,Path(tmp)/'plots')
            self.assertGreater((Path(tmp)/'plots/layer_control.png').stat().st_size,1000)
            with np.load(out/'fields.npz') as a:
                self.assertEqual(a['primitive'].ndim,4)
                self.assertEqual(a['primitive'].shape[0],len(r['history']))
            with self.assertRaises(ValueError):run_layer(C,Path(tmp)/'bad',.0038,end=1.)

    def test_aligned_interface_removes_initial_mixing_and_preserves_charge(self):
        from controlled import formed_layer,conserved_state
        c=self.profile;totals=[];excess=[]
        for dx in (.5e-3,.25e-3,.125e-3):
            s,x,z,info=formed_layer(C,c,.0038,dx=dx,length=.1,shock=.04137,buffer=.002,align_interface=True)
            self.assertEqual(info['interface_mixed_row_count'],0)
            self.assertTrue(info['interface_aligned'])
            self.assertAlmostEqual(info['initial_layer_volume_m2'],.0038*.1,places=15)
            w=s.prim();ahead=x>.06
            np.testing.assert_allclose(w[4,ahead,:][:,z<.0038],0,atol=1e-14)
            np.testing.assert_allclose(w[4,ahead,:][:,z>.0038],1,atol=1e-14)
            totals.append(s.conserved_totals());excess.append(info['initial_excess_over_unignited_layer'])
        for values in [totals,excess]:np.testing.assert_allclose(values,np.broadcast_to(values[0],(3,5)),rtol=2e-11,atol=1e-8)
        unaligned,_,_,info=formed_layer(C,c,.0038,length=.1,shock=.04137,buffer=.002)
        hot=conserved_state(C['p1']/(C['R']*1500),0.,C['p1'],1.,C)
        extra_height=s.ny*s.dy-info['height_m']
        np.testing.assert_allclose(totals[0]-unaligned.conserved_totals(),hot*.1*extra_height,rtol=1e-10,atol=1e-9)
        np.testing.assert_allclose(excess[0],info['initial_excess_over_unignited_layer'],rtol=1e-11,atol=1e-8)

    def test_blast_inventory_matches_independent_box_integrals(self):
        from controlled import blast_layer,conserved_state,formed_layer
        p=self.profile;totals=[]
        h=.015;length=.1
        hot=conserved_state(C['p1']/(C['R']*1500.),0.,C['p1'],1.,C)
        pressure=2*C['CJ']['p'];ignition=conserved_state(pressure/(C['R']*C['CJ']['T']),0.,pressure,1.,C)
        expected=h*(.01*(ignition-p['fresh'])+.02*(hot-p['fresh']))
        for dx in (.5e-3,.25e-3,.125e-3):
            s,x,z,info=blast_layer(C,p,h,dx=dx,length=length,shock=.04137,buffer=.002)
            np.testing.assert_allclose(info['initial_excess_over_unignited_layer'],expected,rtol=1e-11,atol=1e-8)
            self.assertEqual(s.conserved_totals()[1],0.)
            self.assertEqual(s.conserved_totals()[2],0.)
            self.assertEqual(info['start'],'blast')
            totals.append(s.conserved_totals())
        np.testing.assert_allclose(totals,np.broadcast_to(totals[0],(3,5)),rtol=1e-11,atol=1e-8)
        formed,_,_,info=formed_layer(C,p,h,length=length,shock=.04137,buffer=.002)
        self.assertGreater(formed.conserved_totals()[1],0.)
        self.assertGreater(abs(info['initial_excess_over_unignited_layer'][3]-expected[3]),100.)
        with self.assertRaises(ValueError):blast_layer(C,p,h,shock=.02)

    def test_blast_driver_short_step_preserves_native_budgets(self):
        from controlled import run_layer
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'blast';r=run_layer(C,out,.015,end=.03e-6,profile=self.profile,start='blast')
            self.assertEqual(r['status'],'completed')
            self.assertEqual(r['initialization']['start'],'blast')
            self.assertEqual(r['invalid_state_count'],0)
            self.assertLess(r['max_budget_scaled_residual'],1e-12)
            with patch.object(Solver,'step',side_effect=AssertionError('render ran CFD')):
                plot_controlled(out,Path(tmp)/'plots')
            self.assertGreater((Path(tmp)/'plots/layer_control.png').stat().st_size,1000)
            from plot import plot_layer_comparison
            import hashlib
            before=hashlib.sha256((out/'fields.npz').read_bytes()).hexdigest()
            reverse=Path(tmp)/'reverse';reverse.mkdir()
            for name in ('inputs.json','summary.json'):(reverse/name).write_bytes((out/name).read_bytes())
            with np.load(out/'fields.npz') as a:arrays={key:a[key].copy() for key in a.files}
            # Synthetic stronger left-going burning must not replace the
            # right-going wave's peak in the declared observation region.
            left=int(np.argmin(abs(arrays['x']-.15)))
            arrays['primitive'][:,0,left,:]=C['p1']/(C['R']*4000.)
            arrays['primitive'][:,3,left,:]=C['p1']
            arrays['primitive'][:,4,left,:]=.5
            np.savez_compressed(reverse/'fields.npz',**arrays)
            with patch.object(Solver,'step',side_effect=AssertionError('comparison ran CFD')):
                cases=plot_layer_comparison([out,reverse],Path(tmp)/'comparison')
            self.assertNotEqual(np.argmax(cases[0]['rate'][-1]),np.argmax(cases[1]['rate'][-1]))
            np.testing.assert_allclose(cases[0]['gap'],cases[1]['gap'],equal_nan=True)
            self.assertGreater((Path(tmp)/'comparison/layer_comparison.png').stat().st_size,1000)
            self.assertEqual(before,hashlib.sha256((out/'fields.npz').read_bytes()).hexdigest())
            with self.assertRaises(ValueError):plot_layer_comparison([out],Path(tmp)/'bad_plot')
            # Saved input mismatch must be rejected before creating an output.
            altered=Path(tmp)/'altered';altered.mkdir()
            inputs=json.loads((out/'inputs.json').read_text());inputs['calibration']['k']*=2
            (altered/'inputs.json').write_text(json.dumps(inputs))
            (altered/'summary.json').write_bytes((out/'summary.json').read_bytes())
            with self.assertRaises(ValueError):plot_layer_comparison([out,altered],Path(tmp)/'bad_compare')
            self.assertFalse((Path(tmp)/'bad_compare').exists())
            with self.assertRaises(ValueError):run_layer(C,Path(tmp)/'bad',.015,start='unknown')

    def test_layer_continuation_checks_legacy_roundtrip_and_preserves_history(self):
        from controlled import run_layer,restore_layer
        from solver import NG
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp)/'old';new=Path(tmp)/'continued'
            first=run_layer(C,old,.0038,end=.03e-6,profile=self.profile)
            exact,*_=restore_layer(old,C)
            with np.load(old/'state.npz') as a:expected=a['conserved'].copy()
            np.testing.assert_array_equal(exact.U[:,NG:-NG,NG:-NG],expected)
            # Old C3 cases contain float64 primitive snapshots but no conserved checkpoint.
            (old/'state.npz').unlink()
            legacy,*rest=restore_layer(old,C)
            self.assertLess(rest[-1]['max_relative_inventory_difference'],1e-12)
            np.testing.assert_allclose(legacy.U[:,NG:-NG,NG:-NG],expected,rtol=5e-15,atol=1e-8)
            self.assertEqual(legacy.steps,first['steps']);self.assertEqual(legacy.t,first['time_s'])
            exact.step(dt_max=5e-9);legacy.step(dt_max=5e-9)
            np.testing.assert_allclose(legacy.U,exact.U,rtol=1e-12,atol=1e-7)
            result=run_layer(C,new,.0038,end=.05e-6,resume=old,transverse_bound=3200.)
            self.assertEqual(result['status'],'completed');self.assertEqual(result['invalid_state_count'],0)
            self.assertLess(result['max_budget_scaled_residual'],1e-12)
            self.assertGreater(result['steps'],first['steps'])
            with np.load(old/'fields.npz') as a,np.load(new/'fields.npz') as b:
                np.testing.assert_array_equal(a['primitive'],b['primitive'][:len(a['times'])])
            self.assertIn('reconstructed',result['restart']['state_storage'])
            bad=copy.deepcopy(C);bad['q']+=1
            with self.assertRaises(ValueError):restore_layer(old,bad)
            with self.assertRaises(ValueError):run_layer(C,Path(tmp)/'bad',.0038,end=.05e-6,resume=old,transverse_bound=100.)
            with self.assertRaises(ValueError):run_layer(C,Path(tmp)/'bad2',.0038,resume=old,transverse_bound=10000.)
