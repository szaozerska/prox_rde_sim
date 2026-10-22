"""Case transcription and fixed-model checks for the secondary engine controls."""
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np
import yaml

from detwave_study import setup, run
from physics import injector_flux


class SecondaryCaseTests(unittest.TestCase):
    def cases(self):
        root=Path(__file__).resolve().parents[1]/'cases'
        return [yaml.safe_load((root/f'detwave_25fi5_{name}.yaml').read_text())
                for name in ('geometry','high_flux')]

    def test_geometry_and_chemistry_are_explicit_and_fixed(self):
        _,base,_,_=setup(dx_mm=1.)
        for config in self.cases():
            before=copy.deepcopy(config)
            cfg,c,r,s=setup(dx_mm=1.,config=config)
            self.assertEqual(config,before)
            self.assertAlmostEqual(r['width'],2*np.pi*.0102,places=13)
            self.assertAlmostEqual(r['width']*r['gap'],np.pi*(.0127**2-.0077**2),places=14)
            self.assertAlmostEqual(r['length'],.0254,places=13)
            for k in ('gamma','R','q','k','Ea','T1','D_CJ','L_half'):
                self.assertEqual(c[k],base[k],k)
            self.assertLess(r['formed_initialization']['inventory_max_scaled_error'],1e-10)
            self.assertLessEqual(max(r['pressure_stations']),r['length'])
            self.assertNotIn('mean_pressures_kPa',cfg['experimental_reference'])
            for _ in range(3):s.step(dt_max=1e-9)
            self.assertEqual(s.invalid_state_count,0)

    def test_high_flux_plenum_has_declared_choked_capacity(self):
        cfg,c,r,s=setup(dx_mm=1.,config=self.cases()[1])
        flux=np.empty(5)
        capacity=injector_flux(c['p1'],*r['injector'][:2],c['R'],c['gamma'],c['q'],
                               *r['injector'][2:],flux)
        self.assertAlmostEqual(capacity,319.2,places=9)
        self.assertEqual(cfg['operating_point']['phi'],1.176)
        self.assertEqual(cfg['experimental_reference']['phi'],1.19)
        self.assertEqual(r['p_back'],97000.)
        self.assertNotEqual(c['p1'],setup(dx_mm=1.)[1]['p1'])

    def test_saved_secondary_run_uses_supplied_case(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            case=Path(tmp)/'case.yaml';case.write_text(yaml.safe_dump(self.cases()[1]))
            out=Path(tmp)/'run'
            run(out,dx_mm=1.,end_us=.03,case_path=case)
            saved=json.loads((out/'inputs.json').read_text())
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(saved['config']['study_provenance']['kind'],'high_flux_secondary')
            self.assertEqual(saved['resolved']['p_back'],97000.)
            self.assertEqual(summary['status'],'completed')
            self.assertLess(summary['history'][-1]['budget_scaled_residual'],1e-10)
            self.assertEqual(summary['invalid_state_count'],0)
