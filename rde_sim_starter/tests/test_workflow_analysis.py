import copy
import unittest
import numpy as np
import yaml
from test_run import HERE
from workflow_analysis import pressure_spectrum, pressure_spectrogram, run937_reference, roll_response


class WorkflowAnalysisTests(unittest.TestCase):
    def test_known_frequency_and_independent_power_normalization(self):
        t = np.linspace(0., 1., 2049)
        p = 1e5 + 2*np.sin(2*np.pi*40*t) + 3*t
        s = pressure_spectrum(t,p,0,1)
        self.assertTrue(s['available'])
        self.assertAlmostEqual(s['peak_pressure_frequency_Hz'],40,delta=s['frequency_bin_Hz'])
        self.assertAlmostEqual(np.sum(s['density_Pa2_per_Hz'])*s['frequency_bin_Hz'],2.,delta=.002)
        self.assertIn('pressure oscillation only',s['qualification'])

    def test_uneven_sampling_uses_largest_gap_and_no_hidden_window_clamp(self):
        t=np.sort(np.r_[np.linspace(0,.4,301),np.linspace(.41,1,401)])
        p=1e5+np.sin(2*np.pi*20*t)
        s=pressure_spectrum(t,p,.05,.95)
        self.assertLessEqual(s['sampling_nyquist_Hz'],50.+1e-10)
        self.assertAlmostEqual(s['peak_pressure_frequency_Hz'],20,delta=s['frequency_bin_Hz'])
        with self.assertRaises(ValueError): pressure_spectrum(t,p,-.01,.9)
        with self.assertRaises(ValueError): pressure_spectrum(t[::-1],p,0,1)
        p[5]=np.nan
        with self.assertRaises(ValueError): pressure_spectrum(t,p,0,1)

    def test_short_constant_and_low_cycle_signals_are_qualified(self):
        t=np.linspace(0,1,10)
        self.assertFalse(pressure_spectrum(t,t,0,1)['available'])
        t=np.linspace(0,1,500)
        self.assertFalse(pressure_spectrum(t,np.full_like(t,1e5),0,1)['available'])
        s=pressure_spectrum(t,1e5+np.sin(2*np.pi*t),0,1)
        self.assertIn('poorly constrained',s['qualification'])

    def test_spectrogram_detects_changing_frequency_without_mode_label(self):
        t=np.linspace(0,2,4097)
        p=1e5+np.where(t<1,np.sin(2*np.pi*30*t),np.sin(2*np.pi*70*t))
        result=pressure_spectrogram(t,p,0,2,.5)
        s=result['segments']
        self.assertEqual(len(s),7)
        self.assertAlmostEqual(s[0]['peak_pressure_frequency_Hz'],30,delta=2.1)
        self.assertAlmostEqual(s[-1]['peak_pressure_frequency_Hz'],70,delta=2.1)
        self.assertNotIn('wave_count',result)
        with self.assertRaises(ValueError): pressure_spectrogram(t,p,0,2,3)

    def test_reference_identity_and_saved_data_guard(self):
        config=yaml.safe_load((HERE/'config.yaml').read_text())
        ref=config['experimental_reference']
        report=dict(run_mode='engine_intervals',pressure_stations=dict(available=True,
            stations_m=np.array(ref['pressure_stations_mm'])*.001,
            mean_Pa=np.array(ref['mean_pressures_kPa'])*1000*1.1))
        result=run937_reference(config,{},report)
        self.assertTrue(result['available'])
        np.testing.assert_allclose(result['discrepancy_percent'],10.,atol=1e-12)
        self.assertFalse(result['measured_thrust']['available'])
        for section,key,val in [('geometry','r_inner_mm',32),('operating_point','phi',1.2)]:
            c=copy.deepcopy(config);c[section][key]=val
            self.assertFalse(run937_reference(c,{},report)['available'])
        changed=copy.deepcopy(config)
        changed['experimental_reference']['mean_pressures_kPa'][0]+=1
        self.assertFalse(run937_reference(changed,{},report)['available'])
        report['run_mode']='development_benchmark'
        self.assertFalse(run937_reference(config,{},report)['available'])

    def test_constant_torque_roll_matches_closed_form_and_reverses(self):
        t=np.array([0.,.1,.4,1.])
        result=roll_response(t,2*np.diff(t),4.,omega0=3.)
        np.testing.assert_allclose(result['angular_velocity_rad_s'],3.+.5*t)
        np.testing.assert_allclose(result['angle_rad'],3*t+.25*t*t)
        positive=roll_response(t,2*np.diff(t),4.)
        negative=roll_response(t,-2*np.diff(t),4.)
        np.testing.assert_array_equal(positive['angle_rad'],-negative['angle_rad'])
        for inertia in [0,-1,float('nan')]:
            with self.assertRaises(ValueError): roll_response(t,np.diff(t),inertia)
