import unittest
import numpy as np
from analyze import directional_spectrum, exit_contribution, weighted_mean, window_weights


class AnalysisTests(unittest.TestCase):
    def test_partial_step_averaging_window(self):
        weights=window_weights([.1,.3,.4],[.1,.2,.1],.15,.35)
        np.testing.assert_allclose(weights,[0,.15,.05],atol=1e-16)
        self.assertAlmostEqual(float(weighted_mean([100,20,40],weights)),25.)
        with self.assertRaises(ValueError):
            weighted_mean([1,2,3],window_weights([.1,.3,.4],[.1,.2,.1],.5,.7))

    def test_empty_or_invalid_means_are_not_zero_results(self):
        for values,weights in [([],[]),([1],[0]),([1],[-1]),([np.nan],[1]),([1],[np.nan])]:
            with self.subTest(values=values,weights=weights),self.assertRaises(ValueError):
                weighted_mean(values,weights)

    def test_known_uniform_exit_contribution(self):
        expected=(2.*3.**2+120.-100.)*.4
        self.assertAlmostEqual(exit_contribution([2,2],[3,3],[120,120],[.1,.3],100),expected)
        self.assertEqual(exit_contribution(1,0,100,1,100),0.)
        self.assertEqual(exit_contribution(1,0,90,1,100),-10.)

    def test_known_traveling_signal_direction_and_frequency(self):
        t=np.arange(128)/128.
        theta=2*np.pi*np.arange(32)/32
        for direction in [-1,1]:
            p=10.+np.cos(3*theta[None,:]-direction*2*np.pi*8*t[:,None])
            result=directional_spectrum(p,t)
            positive=np.flatnonzero(result['frequency']>0)
            fi,ki=np.unravel_index(np.argmax(result['power'][positive]),(positive.size,32))
            self.assertAlmostEqual(result['frequency'][positive[fi]],8.)
            self.assertEqual(result['wave_number'][ki],-direction*3)

    def test_spectrum_rejects_insufficient_or_nonmonotone_record(self):
        for times in [[0,1,2],[0,1,1,2],[0,1,np.nan,3]]:
            with self.assertRaises(ValueError):
                directional_spectrum(np.ones((len(times),4)),times)


class SavedSignalTests(unittest.TestCase):
    def test_pressure_arrivals_need_hysteresis_and_do_not_count_initial_high(self):
        from analyze import pressure_arrivals
        p=[3.,2.,1.,1.5,2.5,2.1,2.6,1.,3.]
        got=pressure_arrivals(np.arange(len(p),dtype=float),p,2.,1.2)
        np.testing.assert_allclose(got,[3.5,7.5])
        self.assertEqual(pressure_arrivals([0,1,2],[1,1,1],2.,1.2).size,0)
        with self.assertRaises(ValueError):
            pressure_arrivals([0,1,1],[1,2,1],2.,1.)
