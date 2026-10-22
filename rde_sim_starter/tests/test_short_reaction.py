"""Fast checks for the declared C5 sensitivity; no layer campaign on import/test."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from controlled import formed_profile, run_formed, run_layer
from short_reaction import short_calibration, reactor_check, checked_verification, fingerprint, layer_pair

C=json.loads(Path(__file__).resolve().parents[1].joinpath('calib.json').read_text())

class ShortReactionTests(unittest.TestCase):
    def test_scaled_profile_preserves_jump_and_thermodynamics(self):
        before=copy.deepcopy(C);c=short_calibration(C)
        self.assertEqual(C,before)
        self.assertEqual({k:v for k,v in c.items() if k not in ('k','L_half')},
                         {k:v for k,v in C.items() if k not in ('k','L_half')})
        old=formed_profile(C);new=formed_profile(c)
        np.testing.assert_allclose(new['U'],old['U'],rtol=1e-13)
        np.testing.assert_allclose(new['distance']*4,old['distance'],rtol=2e-8,atol=1e-12)
        self.assertLess(max(new['verification']['jump_max_relative_error']),1e-8)
        self.assertAlmostEqual(new['verification']['length_m']['0.5'],.00025,places=12)
        with self.assertRaises(ValueError):short_calibration(c)

    def test_changed_rate_reactor_matches_independent_ode(self):
        c=short_calibration(C)
        a=reactor_check(c,2100.,.35,.3e-6,.05)
        b=reactor_check(c,2100.,.35,.3e-6,.025)
        self.assertLess(a['max_progress_error'],2e-4)
        self.assertGreater(a['max_progress_error']/b['max_progress_error'],3.5)
        self.assertLess(a['conserved_relative_error'],2e-14)
        self.assertEqual(a['invalid_state_count'],0)

    def test_compact_domain_and_continuation_are_explicit(self):
        c=short_calibration(C)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for runner,extra in ((run_formed,{}),(run_layer,{'layer_height':.0038})):
                with self.assertRaises(ValueError):runner(c,root/'bad',end=11e-6,domain_scale=.25,**extra)
            r=run_layer(c,root/'layer',.0038,dx=.5e-3,end=.008e-6,domain_scale=.25,transverse_bound=3200.)
            self.assertEqual(r['status'],'completed')
            inputs=json.loads((root/'layer/inputs.json').read_text())
            self.assertEqual(inputs['length_m'],.1125)
            self.assertEqual(inputs['shock_initial_m'],.04)
            self.assertEqual(inputs['reaction_roi_behind_front_m'],.0075)
            self.assertGreater(r['history'][-1]['top_causal_margin_m'],0)
            self.assertLess(r['max_budget_scaled_residual'],1e-12)
            with self.assertRaises(ValueError):run_layer(c,root/'bad',.0038,end=.01e-6,resume=root/'layer')
            continued=run_layer(c,root/'continued',.0038,end=.01e-6,resume=root/'layer',domain_scale=.25)
            self.assertEqual(continued['status'],'completed')

    def test_layer_gate_rejects_stale_failed_or_mismatched_verification(self):
        c=short_calibration(C)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'verification.json'
            report=dict(status='passed',calibration=c,fingerprint=fingerprint())
            path.write_text(json.dumps(report));checked_verification(c,root)
            for key,value in (('status','failed'),('calibration',C),('fingerprint',{})):
                bad=dict(report);bad[key]=value;path.write_text(json.dumps(bad))
                with patch('short_reaction.run_layer',side_effect=AssertionError('gate advanced CFD')):
                    with self.assertRaises(ValueError):layer_pair(c,root/'new',root)
                self.assertFalse((root/'new').exists())


    def test_contact_far_field_accounts_for_background_reaction(self):
        from experiments import run_contact
        from short_reaction import contact_boundary_check
        c=short_calibration(C)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'contact'
            r=run_contact(c,root,dx=.5e-3,end=.1e-6,reactive=True)
            self.assertGreater(r['max_boundary_state_relative_error'],1e-9)
            check=contact_boundary_check(c,root)
            self.assertLess(check['homogeneous_boundary_scaled_error'],1e-10)
            # A real boundary perturbation must not be excused as uniform burning.
            with np.load(root/'fields.npz') as a:data={k:a[k] for k in a.files}
            data['primitive'][-1,3,-1]*=1.001
            np.savez_compressed(root/'fields.npz',**data)
            self.assertGreater(contact_boundary_check(c,root)['homogeneous_boundary_scaled_error'],1e-4)


class VerificationGateTests(unittest.TestCase):
    def test_budget_gate_rejects_nonfinite_negative_and_corrupted_evidence(self):
        from short_reaction import require_run
        valid=dict(status='completed',invalid_state_count=0,max_budget_scaled_residual=1e-14)
        require_run(valid)
        for value in (np.nan,np.inf,-np.inf,-1.,1e-4):
            with self.subTest(value=value),self.assertRaises(RuntimeError):
                require_run(dict(valid,max_budget_scaled_residual=value))
        for change in (dict(status='failed'),dict(invalid_state_count=1)):
            with self.assertRaises(RuntimeError):require_run(dict(valid,**change))
