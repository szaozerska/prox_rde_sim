import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
import yaml
import contracts
import run
from test_run import toy_case, HERE


class ContractTests(unittest.TestCase):
    def test_dimensions_units_area_and_source_identity(self):
        config, cal = toy_case()
        g = contracts.geometry_contract(config)
        d = g['dimensions']
        self.assertAlmostEqual(d['exit_area_m2'], math.pi * 20e-6)
        self.assertAlmostEqual(d['volume_m3'], math.pi * 80e-9)
        self.assertAlmostEqual(d['lateral_wall_area_m2'] / d['volume_m3'], 1000.)
        self.assertAlmostEqual(d['circumference_m'] * d['gap_m'], d['exit_area_m2'])
        self.assertEqual(g['coordinates']['velocity_basis'], ['e_r', 'e_theta', 'e_z'])
        same = contracts.geometry_contract(dict(config, geometry=dict(reversed(list(config['geometry'].items())))))
        self.assertEqual(g['identity'], same['identity'])
        config['geometry']['length_mm'] *= 2
        self.assertNotEqual(g['identity'], contracts.geometry_contract(config)['identity'])
        self.assertEqual(g['source']['values']['length_mm'], 4.)

    def test_unsupported_geometry_rejected_by_real_runner_before_output(self):
        config, cal = toy_case()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            for edit in [dict(r_inner_mm=0), dict(r_inner_mm=6), dict(length_mm=float('nan')),
                         dict(area_ratio=1.1), dict(cad_file='unread.step'),
                         dict(gap_profile_mm=[2, 3]), dict(r_outer_mm=True)]:
                c = copy.deepcopy(config); c['geometry'].update(edit)
                with self.subTest(edit=edit), self.assertRaises(ValueError):
                    run.start_run(c, cal, out)
                self.assertFalse(out.exists())

    def test_saved_contract_stream_and_corrupted_field(self):
        config, cal = toy_case()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            summary = run.start_run(config, cal, out)
            inputs = json.loads((out / 'inputs.json').read_text())
            contract = inputs['contracts']
            self.assertEqual(contract['results']['fields']['pressure']['unit'], 'Pa')
            self.assertFalse(contract['backend']['capabilities']['cad'])
            self.assertEqual(contract['physical']['original_experimental_stream_reference']['oxygen_plenum_kPa'], 1309.5)
            frames = list(contracts.iter_fields(out, inputs, summary['steps']))
            self.assertEqual(frames[0]['t'], 0)
            self.assertEqual(frames[-1]['t'], summary['t'])
            (out / 'fields' / 'step_999999999.npz').write_bytes(b'uncommitted partial file')
            self.assertEqual(len(list(contracts.iter_fields(out, inputs, summary['steps']))), len(frames))
            path = sorted((out / 'fields').glob('*.npz'))[0]
            with np.load(path) as saved:
                fields = {k: saved[k] for k in saved.files}
            for key,value in [('pressure',np.nan),('progress',2.),('temperature',-1.),('reaction_rate',-1.),('step',.5)]:
                changed={k:v.copy() for k,v in fields.items()}
                if key=='step': changed[key]=np.array(value)
                else: changed[key][0,0]=value
                np.savez(path,**changed)
                with self.subTest(key=key), self.assertRaises(ValueError):
                    list(contracts.iter_fields(out,inputs,summary['steps']))

    def test_preflight_cli_and_no_outputs(self):
        config, _ = toy_case()
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / 'case.yaml'; case.write_text(yaml.safe_dump(config))
            result = subprocess.run([sys.executable, str(HERE / 'run.py'), '--preflight', '--case', str(case)],
                cwd=tmp, env=dict(os.environ, NUMBA_NUM_THREADS='2'), capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['schema_version'], 1)
            self.assertEqual(list(Path(tmp).iterdir()), [case])
