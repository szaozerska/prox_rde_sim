import copy
import json
import math
from pathlib import Path
import unittest
from quick_estimate.compare_mundt import interpolate, make_inputs, pressure_kpa, run

MANIFEST=json.loads((Path(__file__).resolve().parents[1]/"validation/mundt_cases.json").read_text())

class MundtComparisonTests(unittest.TestCase):
    def test_pressure_fit_known_reference(self):
        self.assertAlmostEqual(pressure_kpa(240.21,1.176),377.917,places=3)

    def test_interpolation_and_extrapolation_rejection(self):
        self.assertEqual(interpolate(2,[1,3],[10,30]),20)
        with self.assertRaises(ValueError): interpolate(4,[1,3],[10,30])

    def test_wave_labels_cannot_leak_into_estimate(self):
        a=MANIFEST["cases"][0]
        b=dict(a,primary_waves=99,counter_waves=50,observed_mode="changed label")
        self.assertEqual(make_inputs(a,MANIFEST["reference_grid"]),make_inputs(b,MANIFEST["reference_grid"]))

    def test_all_six_geometries_and_real_negative_present(self):
        self.assertEqual(len({c["configuration"] for c in MANIFEST["cases"]}),6)
        self.assertEqual(len(MANIFEST["cases"]),7)
        negative=MANIFEST["cases"][-1]
        self.assertEqual(negative["primary_waves"],0)
        self.assertGreater(negative["mass_flux"],0)
        self.assertIn("deflagration",negative["observed_mode"])

    def test_coreless_is_not_false_zero_or_accuracy_denominator(self):
        result=run(MANIFEST)
        core=[r for r in result["cases"] if r["case"]["configuration"]=="25-FI-12.7"][0]
        self.assertEqual(core["status"],"unsupported_coreless")
        self.assertIsNone(core["result"])
        self.assertEqual(result["summary"]["supported_positive_cases"],5)
        self.assertEqual(result["summary"]["supported_negative_cases"],1)

    def test_geometric_mass_balance_and_cell_independent_conflict(self):
        for case in MANIFEST["cases"]:
            inputs,diag=make_inputs(case,MANIFEST["reference_grid"])
            if "mass_flow_g_s" not in case:
                self.assertAlmostEqual(inputs["m_dot_g_s"]*.001,
                                       case["mass_flux"]*diag["exact_exit_area_m2"])
            circumference=math.pi*inputs["d_c_mm"]*.001
            self.assertAlmostEqual(diag["minimum_K_compatible_with_refill"],
                                   circumference/diag["one_wave_refill_depth_m"])
            # Even half-CJ speed and exact-area refill leave required K above 9.
            self.assertGreater(.5*diag["minimum_K_using_exact_area_refill"],9)

if __name__=="__main__":unittest.main()
