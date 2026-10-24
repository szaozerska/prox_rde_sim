import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from quick_estimate.model import estimate

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT/"examples/synthetic.json").read_text())

class EstimateTests(unittest.TestCase):
    def test_hand_calculated_two_head_case(self):
        r=estimate(BASE)
        self.assertAlmostEqual(r["continuous_refill_capacity"],2.4)
        self.assertEqual(r["nominal_candidate_wave_counts"],[2])
        self.assertEqual(r["expected_wave_count"],2)
        row=r["candidate_details"][1]
        self.assertAlmostEqual(row["K_nominal"],7)
        self.assertAlmostEqual(row["return_time_s"],56e-6)
        self.assertAlmostEqual(row["fresh_depth_m"],.0144)

    def test_mass_balance_independent_area_time(self):
        r=estimate(BASE)
        area=math.pi*BASE["d_c_mm"]*.001*BASE["annulus_mm"]*.001
        for row in r["candidate_details"]:
            mass=BASE["rho_kg_m3"]*area*row["fresh_depth_m"]
            self.assertAlmostEqual(mass,BASE["m_dot_g_s"]*.001*row["return_time_s"])

    def test_fable_equation_parity_and_source_hash(self):
        path=ROOT/"vendor/fable_chamber_sizing.py"
        spec=importlib.util.spec_from_file_location("legacy",path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        legacy=module.size(BASE)
        self.assertAlmostEqual(legacy["wave_number_w"],estimate(BASE)["continuous_refill_capacity"])
        manifest=json.loads((ROOT/"vendor/provenance.json").read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),manifest["sha256"])

    def test_law_table1_upper_agrees_lower_discrepancy_retained(self):
        # Paper table: w approximately 0.18--0.75 using joint sizing extremes.
        rho=1e5/(268.1*298)
        lower=.005/(rho*(17*.000465)*2500*(3.4*.000465))
        upper=.005/(rho*(7*.000465)*2500*(1.4*.000465))
        self.assertAlmostEqual(lower,.1278525309,places=9)
        self.assertGreater(abs(lower-.18),.02)  # Unresolved paper-table mismatch, not a validation pass.
        self.assertAlmostEqual(upper,.75,delta=.02)
        case=json.loads((ROOT/"examples/law2021_design.json").read_text())
        r=estimate(case)
        self.assertAlmostEqual(r["continuous_refill_capacity"],.409,delta=.002)
        self.assertEqual(r["nominal_candidate_wave_counts"],[])

    def test_zero_flow_is_not_success(self):
        r=estimate(dict(BASE,m_dot_g_s=0))
        self.assertEqual(r["status"],"no_candidate_in_model")
        self.assertEqual(r["possible_candidate_wave_counts"],[])
        self.assertIsNone(r["expected_wave_count"])

    def test_scaling_and_loss(self):
        a=estimate(BASE)
        b=estimate(dict(BASE,m_dot_g_s=BASE["m_dot_g_s"]*2))
        c=estimate(dict(BASE,usable_flow_fraction=.5))
        self.assertAlmostEqual(b["continuous_refill_capacity"],2*a["continuous_refill_capacity"])
        self.assertAlmostEqual(c["continuous_refill_capacity"],.5*a["continuous_refill_capacity"])

    def test_nominal_is_subset_of_possible(self):
        for flow in (0,30,60,90,129.6,200,400):
            r=estimate(dict(BASE,m_dot_g_s=flow))
            self.assertTrue(set(r["nominal_candidate_wave_counts"]) <= set(r["possible_candidate_wave_counts"]))

    def test_reject_invalid_inputs(self):
        for key,value in (("lambda_mm",0),("rho_kg_m3",-1),("U_d_m_s",float("nan")),
                          ("d_c_mm",float("inf")),("annulus_mm",100),("m_dot_g_s",-1),
                          ("usable_flow_fraction",1.1),("lambda_mm",True)):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                estimate(dict(BASE,**{key:value}))
        with self.assertRaises(ValueError): estimate(dict(BASE,typo=1))
        with self.assertRaises(ValueError): estimate({})

    def test_provenance_objects(self):
        b=copy.deepcopy(BASE); b["lambda_mm"]={"value":1.0,"class":"SYNTHETIC","hook":"fixture"}
        self.assertEqual(estimate(b)["expected_wave_count"],2)

    def test_geometry_and_length_can_reject_refill_capacity(self):
        for changes in ({"chamber_length_mm":1},{"d_c_mm":500},{"annulus_mm":.1}):
            r=estimate(dict(BASE,**changes))
            self.assertEqual(r["nominal_candidate_wave_counts"],[])

    def test_cli_json_provenance_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"result.json"
            cmd=[sys.executable,"-m","quick_estimate",str(ROOT/"examples/synthetic.json"),"--out",str(out)]
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            raw=out.read_bytes(); r=json.loads(raw)
            self.assertIn("input_sha256",r["provenance"])
            second=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(second.returncode,2)
            self.assertEqual(raw,out.read_bytes())

if __name__ == "__main__": unittest.main()
