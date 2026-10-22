"""Analytical, corrupt-evidence and read-only integration checks for F1."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from window_report import reduce_window, report_saved_window, main, render_markdown


def analytical_case(times=(0.,1.,3.,4.), forces=(10.,20.,40.)):
    """Uniform exit: rho=2,u=3,A=.4; variable p chosen for each force.

    Inlet axial momentum flux exceeds outlet by exactly 6 N, energy by 10 W.
    This produces nonzero storage even though inlet/outlet mass flows agree.
    """
    inputs=dict(resolved=dict(width=2.,gap=.2,r_mean=.3,p_back=100.,pressure_stations=[.01]),calibration=dict(q=10.))
    initial=np.array([100.,0.,0.,1000.,20.]);rows=[];inventory=initial.copy()
    rows.append(dict(step=0,t=times[0],dt=0.,inventory=inventory.copy()))
    for i,(t0,t1,force) in enumerate(zip(times[:-1],times[1:],forces),1):
        dt=t1-t0
        boundary=np.zeros((4,5))
        boundary[2]=np.array([2.4,0,force+40+6,100,0])*dt
        boundary[3]=np.array([2.4,0,force+40,90,0])*dt
        source=np.array([0,0,0,0,.25])*dt
        # Independently specified analytical storage, not summed from the flux arrays.
        inventory=initial+np.array([0,0,6,10,.25])*t1
        rows.append(dict(step=i,t=t1,dt=dt,inventory=inventory.copy(),boundary_integral=boundary,
            source_integral=source,exit_cell_force_estimate_N=force+1,pressure_stations=[force*10]))
    summary=dict(status='completed_limit',run_mode='engine_intervals',invalid_state_count=0,t=times[-1],steps=len(rows)-1)
    return inputs,summary,rows


class WindowReductionTests(unittest.TestCase):
    def test_constant_known_flow_force_storage_and_effective_isp(self):
        data=analytical_case(forces=(15.2,15.2,15.2))
        r=reduce_window(*data,.5,3.5)
        # Direct continuum exit calculation: (rho*u^2 + p - p_ambient)*A.
        expected=(2*3**2+120-100)*.4
        self.assertAlmostEqual(r['exit_numerical_force']['mean_N'],expected)
        self.assertAlmostEqual(r['exit_force_from_control_volume']['mean_N'],expected)
        self.assertAlmostEqual(r['annulus_exit_effective_isp']['value_s'],expected/(2.4*9.80665))
        np.testing.assert_allclose(r['budgets']['storage'],[0,0,18,30,.75],atol=1e-12)
        np.testing.assert_allclose(r['budgets']['residual'],0,atol=1e-12)
        self.assertTrue(r['budgets']['closure_within_tolerance'])
        self.assertEqual(r['budgets']['source_integral'][3],0)
        self.assertAlmostEqual(r['chemical_conversion']['chemical_to_thermal_J'],7.5)
        self.assertFalse(r['engine_torque']['available'])
        self.assertEqual(r['window']['partially_included_steps'],2)

    def test_uneven_steps_and_partial_window_use_duration_not_sample_count(self):
        r=reduce_window(*analytical_case(),.5,3.5)
        self.assertAlmostEqual(r['exit_numerical_force']['mean_N'],65/3)
        self.assertAlmostEqual(r['exit_cell_force_estimate']['mean_N'],65/3+1)
        self.assertAlmostEqual(r['pressure_stations']['mean_Pa'][0],650/3)
        self.assertNotAlmostEqual(r['exit_numerical_force']['mean_N'],70/3)
        aligned=reduce_window(*analytical_case(),1.,3.)
        self.assertEqual(aligned['window']['partially_included_steps'],0)
        self.assertEqual(aligned['window']['contributing_steps'],1)
        self.assertAlmostEqual(aligned['exit_numerical_force']['mean_N'],20.)

    def test_repartitioning_constant_flux_intervals_preserves_report(self):
        original=reduce_window(*analytical_case(),.5,3.5)
        split=analytical_case((0.,.5,1.,2.,3.,3.5,4.),(10.,10.,20.,20.,40.,40.))
        result=reduce_window(*split,.5,3.5)
        for key in ('storage','net_influx_and_source','boundary_integral','source_integral'):
            np.testing.assert_allclose(original['budgets'][key],result['budgets'][key],rtol=1e-13,atol=1e-12)
        self.assertAlmostEqual(original['exit_numerical_force']['mean_N'],result['exit_numerical_force']['mean_N'])

    def test_zero_negative_force_and_no_propellant_do_not_become_fake_performance(self):
        for force in (0.,-4.):
            r=reduce_window(*analytical_case(forces=(force,)*3),0.,4.)
            self.assertAlmostEqual(r['exit_numerical_force']['mean_N'],force)
        for mass_rate in (0.,-1.):
            data=analytical_case()
            for row in data[2][1:]:row['boundary_integral'][2,0]=mass_rate*row['dt']
            result=reduce_window(*data,0,4)
            self.assertFalse(result['annulus_exit_effective_isp']['available'])
            self.assertFalse(result['budgets']['closure_within_tolerance'])

    def test_missing_data_is_unavailable_while_available_fields_still_report(self):
        for field in ('source_integral','boundary_integral','inventory'):
            data=analytical_case();del data[2][1][field]
            r=reduce_window(*data,.5,3.5)
            self.assertFalse(r['budgets']['available'])
            self.assertFalse(r['exit_force_from_control_volume']['available'])
            self.assertTrue(r['pressure_stations']['available'])
            self.assertEqual(r['exit_numerical_force']['available'],field!='boundary_integral')
            self.assertIn('Unavailable',render_markdown(r))

    def test_corrupt_budget_reports_failure_instead_of_closing_by_construction(self):
        data=analytical_case();data[2][2]['source_integral'][3]=12.
        r=reduce_window(*data,0,4)
        self.assertEqual(r['budgets']['residual'][3],-12.)
        self.assertFalse(r['budgets']['closure_within_tolerance'])
        self.assertIn('**False**',render_markdown(r))

    def test_zero_net_momentum_uses_a_dimensional_inventory_scale(self):
        data=analytical_case();data[2][-1]['inventory'][1]=1e-14
        r=reduce_window(*data,0,4)
        self.assertTrue(r['budgets']['closure_within_tolerance'])
        self.assertEqual(r['budgets']['residual'][1],1e-14)
        data[2][-1]['inventory'][1]=.1
        self.assertFalse(reduce_window(*data,0,4)['budgets']['closure_within_tolerance'])

    def test_corrupt_timing_shapes_and_nonfinite_values_are_rejected(self):
        mutations=[lambda h:h[2].update(dt=1.9),lambda h:h[2].update(t=1.),
            lambda h:h[1].update(step=True),lambda h:h[2].update(step=5),
            lambda h:h[1].update(boundary_integral=np.zeros((5,4))),
            lambda h:h[1].update(source_integral=[0,0,0,np.nan,0]),
            lambda h:h[1].update(inventory=[100,0,0,np.inf,20]),
            lambda h:h[2].update(pressure_stations=[np.nan])]
        for mutate in mutations:
            data=analytical_case();mutate(data[2])
            with self.assertRaises(ValueError):reduce_window(*data,.5,3.5)
        for a,b in [(-1,2),(1,5),(2,2),(3,1),(np.nan,2),(1,np.inf)]:
            with self.assertRaises(ValueError):reduce_window(*analytical_case(),a,b)

    def test_angular_storage_and_negative_force_sign_are_preserved(self):
        data=analytical_case()
        for row in data[2]:
            row['inventory'][1]=2*row['t']
            if row['step']:row['boundary_integral'][2,1]=2*row['dt']
        r=reduce_window(*data,.5,3.5)
        self.assertAlmostEqual(r['budgets']['angular_storage_kg_m2_s'],1.8)
        self.assertAlmostEqual(r['budgets']['angular_residual_kg_m2_s'],0.)
        self.assertFalse(r['engine_torque']['available'])


class SavedWindowTests(unittest.TestCase):
    def setUp(self):
        from run import start_run
        from tests.test_run import toy_case
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.case=self.root/'case'
        c,k=toy_case();start_run(c,k,self.case)

    def test_reader_ignores_uncommitted_tail_loads_only_metadata_and_never_runs_cfd(self):
        from solver import Solver
        path=self.case/'history.jsonl'
        with path.open('ab') as f:f.write(b'{"partial":')
        def hashes():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.case.rglob('*') if p.is_file()}
        before=hashes();real_load=np.load;checkpoint_path=self.case/'checkpoint.npz'
        class MetadataOnly:
            def __enter__(self):
                self.archive=real_load(checkpoint_path,allow_pickle=False);return self
            def __getitem__(self,key):
                if key!='state_json':raise AssertionError('loaded a checkpoint field')
                return self.archive[key]
            def __exit__(self,*args):self.archive.close()
        def load(path,**kwargs):
            self.assertEqual(Path(path).name,'checkpoint.npz');return MetadataOnly()
        with patch.object(Solver,'step',side_effect=AssertionError('report ran CFD')),patch('window_report.np.load',side_effect=load):
            r=report_saved_window(self.case,.015e-6,.255e-6)
        self.assertEqual(before,hashes())
        self.assertTrue(r['budgets']['closure_within_tolerance'])
        self.assertGreater(r['window']['partially_included_steps'],0)
        self.assertEqual(r['provenance']['committed_history_bytes'],path.stat().st_size-len(b'{"partial":'))

    def test_changed_inputs_or_incomplete_committed_history_are_rejected(self):
        p=self.case/'inputs.json';original=p.read_bytes();p.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError,'do not agree'):report_saved_window(self.case,0,1e-7)
        p.write_bytes(original)
        history=self.case/'history.jsonl';history.write_bytes(history.read_bytes().splitlines(keepends=True)[0])
        with self.assertRaisesRegex(ValueError,'committed history'):report_saved_window(self.case,0,1e-7)

    def test_cli_outputs_new_json_and_markdown_and_rejects_overwrite_or_in_run_output(self):
        destination=self.root/'report'
        args=['--run',str(self.case),'--start-us','.015','--end-us','.255','--out',str(destination)]
        main(args)
        report=json.loads((destination/'report.json').read_text())
        self.assertTrue(report['budgets']['closure_within_tolerance'])
        self.assertIn('not whole-engine thrust',(destination/'report.md').read_text())
        original=(destination/'report.json').read_bytes()
        with self.assertRaises(SystemExit):main(args)
        self.assertEqual(original,(destination/'report.json').read_bytes())
        with self.assertRaises(SystemExit):main(args[:-1]+[str(self.case/'report')])
        self.assertFalse((self.case/'report').exists())
