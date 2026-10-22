import unittest
import numpy as np
from radial_study import ring_metrics


class RadialStudyTests(unittest.TestCase):
    def test_periodic_front_distance_and_absolute_signal_preserved(self):
        p=np.ones(8);p[-1]=3.;w=np.zeros(8);w[0]=1e-10
        # Largest two jumps tie; argmax locates face 6.5. Wrapped nearest cell is 0.
        a=ring_metrics(p,w,.001)
        self.assertAlmostEqual(a['front_to_half_peak_reaction_m'],.0015)
        self.assertEqual(a['reaction_rate_max_per_s'],1e-10)
        b=ring_metrics(np.roll(p,2),np.roll(w,2),.001)
        self.assertEqual(a['pressure_contrast'],b['pressure_contrast'])
        c=ring_metrics(np.ones(8),np.zeros(8),.001)
        self.assertIsNone(c['front_to_half_peak_reaction_m'])
        self.assertEqual(c['pressure_contrast'],0.)
        with self.assertRaises(ValueError):ring_metrics(p,-w,.001)
