import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml
import run
import plot
from workflow import collect_workflow, compare_saved_runs, write_data
from test_run import toy_case, HERE


def hashes(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.config,self.cal=toy_case()
        self.config['model'].update(walls='constant_cf',wall_cf=.01)
        self.config['numerics']['max_step_ns']=5.

    def cli(self,script,args):
        result=subprocess.run([sys.executable,*script,*args],cwd=HERE,
            env=dict(os.environ,NUMBA_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True,text=True,timeout=120)
        return result

    def test_end_to_end_preflight_run_resume_viewer_and_readonly_rejection(self):
        case=self.root/'case.yaml';case.write_text(yaml.safe_dump(self.config))
        pre=self.cli(['run.py'],['--preflight','--case',str(case)])
        self.assertEqual(pre.returncode,0,pre.stderr)
        self.assertEqual(list(self.root.iterdir()),[case])
        native=self.root/'native'
        new=self.cli(['run.py'],['--case',str(case),'--out',str(native)])
        self.assertEqual(new.returncode,0,new.stderr)
        resumed=self.cli(['run.py'],['--resume',str(native)])
        self.assertEqual(resumed.returncode,0,resumed.stderr)
        before=hashes(native);out=self.root/'view'
        args=['--workflow',str(native),'--start-us','0.055','--end-us','0.45','--frames','3',
              '--inertia-kg-m2','0.01','--out',str(out)]
        command=['-c','import sys,plot; plot.main(sys.argv[1:]); assert "solver" not in sys.modules']
        result=self.cli(command,args)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(hashes(native),before)
        self.assertTrue((out/'COMPLETE').exists());self.assertFalse((out/'INCOMPLETE').exists())
        report=json.loads((out/'report.json').read_text())
        self.assertTrue(report['budgets']['closure_within_tolerance'])
        self.assertTrue(report['engine_torque']['available'])
        self.assertTrue(report['roll_response']['available'])
        self.assertFalse(report['experimental_comparison']['available'])
        self.assertFalse(report['radial_physics']['centrifugal_pressure_split'])
        self.assertEqual(len(report['preview']['rendered_frames']),3)
        for name in ['index.html','report.md','history.csv','wrapped.png','space_time.png','signals.png','loads.png','roll.png','animations/unwrapped.gif','animations/wrapped.gif']:
            self.assertGreater((out/name).stat().st_size,100)
        html=(out/'index.html').read_text()
        self.assertIn('RDE-001 remains unresolved',html)
        self.assertNotIn('https://',html)
        self.assertIn('animations/wrapped.gif', html)
        self.assertNotIn('centrifugal pressure split, curvature loss and heat loss are absent', html)
        again=self.cli(command,args)
        self.assertEqual(again.returncode,2)
        inside=self.cli(command,args[:-1]+[str(native/'view')])
        self.assertEqual(inside.returncode,2)
        self.assertFalse((native/'view').exists())
        self.assertEqual(hashes(native),before)

    def test_comparison_records_confounds_and_refuses_nonoverlap(self):
        paths=[]
        for i,cf in enumerate([.01,.02]):
            config=copy.deepcopy(self.config);config['model']['wall_cf']=cf
            path=self.root/f'run{i}';run.start_run(config,self.cal,path);paths.append(path)
        result=compare_saved_runs(paths,0.,.25e-6)
        self.assertEqual(set(result['rows'][1]['changed_settings']),{'model.wall_cf'})
        self.assertTrue(result['rows'][1]['one_setting_changed'])
        self.assertTrue(result['rows'][1]['recorded_implementation_matches_baseline'])
        export=self.root/'export';export.mkdir()
        write_data(collect_workflow(paths[0],0.,.25e-6),export,result)
        self.assertIn('model.wall_cf',(export/'comparison.csv').read_text())
        self.assertEqual(json.loads((export/'comparison.json').read_text())['rows'][1]['changed_settings']['model.wall_cf']['value'],.02)
        self.assertGreater(result['rows'][1]['wall_torque_Nm'],result['rows'][0]['wall_torque_Nm'])
        with self.assertRaises(ValueError):compare_saved_runs(paths,0.,1.)
        with self.assertRaises(ValueError):compare_saved_runs([paths[0],paths[0]],0.,.25e-6)
        with patch('solver.Solver.step',side_effect=AssertionError('analysis launched CFD')):
            data=collect_workflow(paths[0],.01e-6,.02e-6)
        self.assertEqual(data['report']['preview']['snapshot_count'],0)
        self.assertTrue(data['report']['budgets']['available'])
        with self.assertRaises(ValueError):collect_workflow(paths[0],0,.25e-6,segment_s=0)
        with self.assertRaises(ValueError):collect_workflow(paths[0],0,.25e-6,inertia=0)

    def test_radial_report_describes_enabled_physics(self):
        self.config['model'].pop('wall_cf')
        self.config['model'].update(walls='annular_closure', radial=dict(centrifugal=True,
            inner=dict(cf=.005, temperature_K=300.), outer=dict(cf=.005, temperature_K=300.),
            analogy_factor=1., recovery_factor=.9))
        native=self.root/'native';run.start_run(self.config,self.cal,native)
        data=collect_workflow(native,0.,.25e-6)
        out=self.root/'report';out.mkdir();write_data(data,out)
        report=(out/'report.md').read_text()
        self.assertIn('centrifugal_pressure_split=True',report)
        self.assertIn('heat_loss=True',report)
        self.assertNotIn('heat loss are not implemented',report)

    def test_failure_marks_incomplete_instead_of_success(self):
        native=self.root/'native';run.start_run(self.config,self.cal,native)
        out=self.root/'bad'
        with patch('workflow.write_data',side_effect=OSError('test storage failure')):
            with self.assertRaises(OSError):
                plot.plot_workflow(native,out,.01e-6,.02e-6,frames=1)
        self.assertTrue((out/'INCOMPLETE').exists())
        self.assertFalse((out/'COMPLETE').exists())


class WatchTests(unittest.TestCase):
    def test_refreshes_changed_checkpoints_and_stops_without_solver(self):
        summaries=[dict(steps=1,t=1e-6,status='running'),dict(steps=1,t=1e-6,status='running'),
                   dict(steps=2,t=2e-6,status='completed_limit')]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'view'
            def render(source,target,start,end,frames,gifs=False):
                Path(target).mkdir();(Path(target)/'index.html').write_text('verified report')
            with patch('window_report.load_native_prefix',side_effect=[({},s,[],{}) for s in summaries]), \
                 patch('plot.plot_workflow',side_effect=render) as renderer, patch('time.sleep'):
                result=plot.watch_workflow(Path(tmp)/'native',out,refresh_seconds=1)
            self.assertEqual(result['updates'],2)
            self.assertEqual(renderer.call_count,2)
            self.assertEqual(renderer.call_args_list[0].args[3],1e-6)
            self.assertEqual(renderer.call_args_list[1].args[3],2e-6)
            self.assertIn('update_0001_step_000000002/index.html',(out/'index.html').read_text())

    def test_corrupt_checkpoint_does_not_wait_forever(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('window_report.load_native_prefix',side_effect=ValueError('corrupt')) as reader, patch('time.sleep'):
                with self.assertRaisesRegex(ValueError,'three reads'):
                    plot.watch_workflow(Path(tmp)/'native',Path(tmp)/'out',refresh_seconds=1)
            self.assertEqual(reader.call_count,3)
