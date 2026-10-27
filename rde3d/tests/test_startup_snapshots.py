"""Reject misleading combinations of independent native CFD trajectories."""
import json, sys, tempfile, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/pelec'))
from combine_startup import combine

class SnapshotTests(unittest.TestCase):
    def segment(self, root, name, times, parent=None, value=1):
        path=root/name;path.mkdir()
        (path/'case.json').write_text(json.dumps({'startup':{'kernel_angle_deg':2},'species':['CH4'],'finest_dx_m':.0002}))
        (path/'fetch.json').write_text(json.dumps({'run_id':name}))
        (path/'allocation.json').write_text(json.dumps({'command': ['solver'] + ([f'amr.restart=/results/{parent}/chk00001'] if parent else [])}))
        np.savez(path/'preview.npz',time_s=times,theta_rad=[0,1],z_m=[0,1],pressure_Pa=np.full((len(times),2,2),value))
        (path/'checks.json').write_text(json.dumps({'rows':[{'time_s':t} for t in times], 'checks':{'species_sum':True}}))
        return path

    def test_preserves_native_times_and_deduplicates_restart(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=self.segment(p,'a',[0.,1e-6]);b=self.segment(p,'b',[1e-6,5e-6],'a')
            combine([a,b],p/'out')
            with np.load(p/'out/preview.npz') as data:np.testing.assert_array_equal(data['time_s'],[0.,1e-6,5e-6])

    def test_rejects_different_trajectory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=self.segment(p,'a',[0.,1e-6]);b=self.segment(p,'b',[2e-6,5e-6],'unrelated')
            with self.assertRaisesRegex(ValueError,'checkpoint'):combine([a,b],p/'out')

    def test_rejects_conflicting_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a=self.segment(p,'a',[0.,1e-6]);b=self.segment(p,'b',[1e-6,5e-6],'a',value=2)
            with self.assertRaisesRegex(ValueError,'Conflicting'):combine([a,b],p/'out')
