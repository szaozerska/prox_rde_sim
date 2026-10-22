"""Saved-reference feasibility checks; no engine or thermochemical integration."""
import copy
import json
from pathlib import Path
import unittest
import numpy as np
from model_audit import reaction_scale_audit


class ModelAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=json.loads((Path(__file__).resolve().parents[2]/'docs/verification/d3_metrics.json').read_text())

    def test_rate_scaling_and_held_out_distance(self):
        c=self.evidence['reference_inputs']['calibration'];reference=self.evidence['reference']
        before=copy.deepcopy(c);report=reaction_scale_audit(c,reference)
        self.assertEqual(c,before)
        old=np.array(report['current_length_m']);physical=np.array(report['physical_length_m'])
        self.assertAlmostEqual(old[0],c['L_half'],places=12)
        for match,index in [('rate_only_match_half',0),('rate_only_match_95',2)]:
            item=report[match];pred=np.array(item['predicted_length_m'])
            self.assertAlmostEqual(pred[index],physical[index],places=12)
            np.testing.assert_allclose(pred*item['k_multiplier'],old,rtol=1e-12)
        fit=report['two_distance_candidate_not_adopted']
        np.testing.assert_allclose(np.array(fit['predicted_length_m'])[[0,2]],physical[[0,2]],rtol=1e-8)
        # Independent holdout: matching two distances must not be reported as all-profile validation.
        self.assertGreater(fit['held_out_90_relative_error'],.05)
        self.assertLess(fit['held_out_90_relative_error'],.08)
        self.assertGreater(fit['steps_for_three_reference_intervals_lower_bound'],9e7)
        self.assertEqual(report['thermodynamics_unchanged']['CJ_speed_mps'],c['D_CJ'])

    def test_rejects_nonphysical_reference_distances(self):
        reference=copy.deepcopy(self.evidence['reference'])
        reference['znd']['heat_fraction_lengths_m']['0.95']=0.
        with self.assertRaises(ValueError):reaction_scale_audit(self.evidence['reference_inputs']['calibration'],reference)
