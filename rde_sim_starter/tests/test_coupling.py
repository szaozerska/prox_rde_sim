"""Known traveling signals and dimensional source integrals, not engine validation."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import yaml
from coupling import periodic_peaks, track_candidates, thermal_metrics, inspect_run, config_differences
from plot import plot_coupling
from run import start_run
from solver import Solver
from tests.test_run import toy_case


class CouplingTests(unittest.TestCase):
    def test_periodic_peak_is_detected_once_at_the_seam(self):
        n=100; x=np.arange(n)/n
        distance=(x+.5)%1-.5
        values=1+3*np.exp(-distance**2/.0008)
        np.testing.assert_array_equal(periodic_peaks(values,2.,.5),[0])
        self.assertEqual(periodic_peaks(np.ones(n),.5,.1).size,0)
        values[45:48]=5.
        np.testing.assert_array_equal(periodic_peaks(values,2.,.5),[0,46])
        twins=np.ones(n); twins[[0,98]]=4.
        np.testing.assert_array_equal(periodic_peaks(twins,2.,.5,minimum_cells=4),[0])

    def test_tracks_preserve_direction_and_unwrap_a_known_speed(self):
        for direction in [-1,1]:
            positions=[np.array([(.94+direction*.08*i)%1]) for i in range(4)]
            result=track_candidates([0,.01,.02,.03],positions,1.,10.,.001)
            self.assertEqual(len(result['tracks']),1)
            track=result['tracks'][0]
            self.assertAlmostEqual(track['fit_speed_mps'],direction*8.)
            np.testing.assert_allclose([s['unwrapped_x_m'] for s in track['samples']],.94+direction*.08*np.arange(4))

    def test_ambiguous_collision_and_missing_frame_break_tracks(self):
        result=track_candidates([0,.01],[[.2,.4],[.3]],1.,20.,.001)
        self.assertEqual(len(result['tracks']),3)
        self.assertTrue(all(len(track['samples'])==1 for track in result['tracks']))
        result=track_candidates([0,.01,.02],[[.2],[],[.21]],1.,10.,.001)
        self.assertEqual(len(result['tracks']),2)

    def test_cadence_and_speed_gates_prevent_unsupported_links(self):
        result=track_candidates([0,1.],[[.2],[.21]],1.,.6,.001)
        self.assertEqual(len(result['tracks']),2)
        self.assertEqual(result['cadence_ambiguous_intervals'],1)
        result=track_candidates([0,.01],[[.2],[.4]],1.,10.,.001)
        self.assertEqual(len(result['tracks']),2)

    def test_thermal_conversion_and_height_quantiles_have_known_units(self):
        p=np.full((2,3),10.); rho=np.full_like(p,2.); rate=np.full_like(p,4.)
        result,field=thermal_metrics(p,rho,rate,3.,.1,.2,.5,5.,.4)
        np.testing.assert_array_equal(field,24.)
        self.assertAlmostEqual(result['thermal_conversion_W'],1.44)
        self.assertEqual(result['conversion_fraction_p_above_threshold'],1.)
        self.assertAlmostEqual(result['conversion_fraction_below_initial_fill'],2/3)
        np.testing.assert_allclose(result['conversion_height_quantiles_m'],[.06,.3,.54])
        empty,_=thermal_metrics(p,rho,rate*0,3.,.1,.2,.5,5.,None)
        self.assertEqual(empty['thermal_conversion_W'],0.)
        self.assertEqual(empty['conversion_height_quantiles_m'],[None]*3)
        self.assertIsNone(empty['conversion_fraction_p_above_threshold'])

    def test_invalid_signals_are_rejected(self):
        for values in [[1,2],[1,np.nan,2]]:
            with self.assertRaises(ValueError):
                periodic_peaks(values,1.,.1)
        for times,positions in [([0,0],[[0],[0]]),([0,1],[[0],[1.]])]:
            with self.assertRaises(ValueError):
                track_candidates(times,positions,1.,1.,.01)
        with self.assertRaises(ValueError):
            thermal_metrics([[1.]],[[1.]],[[-1.]],1.,1.,1.,1.,1.,None)

    def test_saved_comparison_is_read_only_and_missing_rate_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); first=root/'first'; second=root/'second'
            config,calibration=toy_case()
            start_run(config,calibration,first)
            other=copy.deepcopy(config); other['initialization']['u_theta']=20.
            start_run(other,calibration,second)
            def hashes():
                return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [first,second]
                        for p in folder.rglob('*') if p.is_file()}
            before=hashes()
            with patch.object(Solver,'step',side_effect=AssertionError('diagnostic advanced CFD')):
                result=plot_coupling(first,root/'plots',second,heights_mm=[1.,3.])
            self.assertEqual(hashes(),before)
            self.assertEqual(result['config_differences'],[dict(path='initialization.u_theta',left=10.,right=20.)])
            self.assertTrue(result['identical_calibration'])
            self.assertTrue(result['identical_numerical_implementation'])
            self.assertGreater((root/'plots/comparison.png').stat().st_size,0)
            for name in ['baseline','variant']:
                saved=json.loads((root/'plots'/name/'coupling.json').read_text())
                self.assertIsNone(saved['confirmed_detonation_passages'])
                self.assertEqual(saved['native_chemical_conversion_J'],0.)
                self.assertEqual(saved['snapshot_trapezoid_conversion_J'],0.)
                self.assertTrue(all(not ring['tracks'] for ring in saved['rings']))
                for figure in ['reaction_fields.png','axial_evolution.png','ring_tracks.png']:
                    self.assertGreater((root/'plots'/name/figure).stat().st_size,0)
            path=next((first/'fields').glob('*.npz'))
            with np.load(path,allow_pickle=False) as saved:
                fields={key:saved[key].copy() for key in saved.files if key!='reaction_rate'}
            np.savez_compressed(path,**fields)
            with self.assertRaisesRegex(ValueError,'missing data are not zero reaction'):
                inspect_run(first,heights_mm=[1.])

    def test_startup_case_changes_only_the_declared_parameter(self):
        root=Path(__file__).resolve().parents[1]
        baseline=yaml.safe_load((root/'config.yaml').read_text())
        variant=yaml.safe_load((root/'cases/run937_fill_7p6mm.yaml').read_text())
        self.assertEqual(config_differences(baseline,variant),
                         [dict(path='initialization.fill_height_mm',left=3.8,right=7.6)])
