"""Observed GRI inversion failure must not be confused with fit validity."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/pelec'))
from analyze_thermo_audit import analyze


class ThermoAuditTests(unittest.TestCase):
    def evidence(self,label):
        return json.loads((ROOT/f'docs/verification/pelec_g2/thermo_{label}_evidence.json').read_text())

    def test_original_hot_inverse_failure_is_detected(self):
        case=next(c for c in analyze(self.evidence('original'))['cases'] if c['mechanism']=='grimech30')
        self.assertFalse(case['numerical_consistency_passed'])
        self.assertFalse(case['checks']['temperature_round_trip'])
        self.assertFalse(case['checks']['enthalpy_round_trip'])

    def test_numerical_fix_does_not_pass_physical_fit_gate(self):
        case=next(c for c in analyze(self.evidence('diagnostic'))['cases'] if c['mechanism']=='grimech30')
        self.assertTrue(case['numerical_consistency_passed'])
        self.assertFalse(case['checks']['inside_thermo_fits'])
        self.assertFalse(case['operator_preflight_passed'])

    def test_incomplete_or_nonfinite_operator_output_is_rejected(self):
        evidence=self.evidence('diagnostic')
        missing=copy.deepcopy(evidence);missing['cases'][0]['values_cgs'].pop()
        with self.assertRaises(ValueError):analyze(missing)
        evidence['cases'][0]['values_cgs'][0][0]=float('nan')
        with self.assertRaises(ValueError):analyze(evidence)


if __name__=='__main__':unittest.main()
