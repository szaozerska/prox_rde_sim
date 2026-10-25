"""Regression checks for false passes and unit/provenance mistakes in the adapter."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'cfd/pelec'))
from control import CASE,inputs,log_errors,plot_time,validate
from analyze import check_rows,collect

class ContractTests(unittest.TestCase):
    def test_units_and_reaction_switch(self):
        text=inputs(CASE,1e-8)
        values={s.split('=',1)[0].strip():s.split('=',1)[1].strip() for s in text.splitlines() if '=' in s}
        self.assertEqual(float(values['prob.p_init']),CASE['pressure_Pa']*10)
        self.assertEqual(list(map(float,values['geometry.prob_hi'].split())),[.1,.1])
        self.assertEqual(values['geometry.is_periodic'],'1 1')
        self.assertEqual(values['pelec.do_hydro'],'1')
        self.assertIn('pelec.do_react = 0',inputs(CASE,1e-8,False))
        self.assertNotIn('L_half',text)
        self.assertNotIn('cvode.',inputs(CASE,1e-8,False))
        self.assertNotIn('ode.',inputs(CASE,1e-8,False))

    def test_invalid_case_is_not_silently_accepted(self):
        for key,value in [('temperature_K',4000),('phi',float('nan')),('cells',[8,8,8]),('final_time_s',.001)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                c=copy.deepcopy(CASE);c[key]=value;validate(c)
        with self.assertRaises(ValueError):inputs(CASE,float('nan'))
        with self.assertRaises(ValueError):validate(dict(CASE,custom_rate=1))

    def test_printed_cvode_failure_fails_even_with_exit_zero(self):
        self.assertTrue(log_errors('[CVODE ERROR] maximum steps exceeded'))
        self.assertTrue(log_errors('WARNING: turning on reactions while using ReactorNull'))
        self.assertFalse(log_errors('Initializing CVODE:\nSTEP = 20\nRun time = 1'))

    def test_dimension_and_native_time(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'Header').write_text('HyperCLaw\n2\ndensity\nTemp\n2\n2e-7\n0\n')
            self.assertEqual(plot_time(p),2e-7)
            (p/'Header').write_text('HyperCLaw\n2\ndensity\nTemp\n3\n2e-7\n0\n')
            with self.assertRaises(ValueError):plot_time(p)

class FalsePassTests(unittest.TestCase):
    def fixture(self):
        row=dict(time_s=0.,temperature_K=1800.,pressure_Pa=377916.972,
                 species_change=0.,temperature_relative_error=0.,pressure_relative_error=0.,
                 species_max_absolute_error=0.,density_relative_drift=0.,energy_relative_drift=0.,
                 element_absolute_drift=0.,species_sum_error=0.,minimum_Y=0.,nonuniformity=0.)
        return [row,dict(row,time_s=2e-7,species_change=3e-5)]

    def test_noop_chemistry_cannot_pass(self):
        rows=self.fixture();rows[-1]['species_change']=0
        checks=check_rows(rows,dict(CASE,reacting=True),{'completion_passed':True},'Initializing CVODE:')
        self.assertFalse(checks['active_chemistry'])

    def test_corrupt_physics_and_early_end_fail(self):
        mutations={'time_s':1e-7,'energy_relative_drift':1e-3,'species_max_absolute_error':.01,
                   'minimum_Y':-.01,'temperature_K':3100,'element_absolute_drift':.01}
        for key,value in mutations.items():
            with self.subTest(key=key):
                rows=self.fixture();rows[-1][key]=value
                checks=check_rows(rows,dict(CASE,reacting=True),{'completion_passed':True},'Initializing CVODE:')
                self.assertFalse(all(checks.values()))

    def test_failure_log_veto(self):
        checks=check_rows(self.fixture(),dict(CASE,reacting=True),{'completion_passed':True},
                          'Initializing CVODE:\n[CVODE ERROR] failure')
        self.assertFalse(checks['native_completion'])

    def test_frozen_cannot_pass_with_reaction(self):
        checks=check_rows(self.fixture(),dict(CASE,reacting=False),{'completion_passed':True},'')
        self.assertFalse(checks['active_chemistry'])

    def test_bad_archive_or_path_cannot_be_collected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);buf=io.BytesIO()
            with tarfile.open(fileobj=buf,mode='w:gz') as tar:
                item=tarfile.TarInfo('../escaped');item.size=1;tar.addfile(item,io.BytesIO(b'x'))
            raw=buf.getvalue();(p/'native.tar.gz').write_bytes(raw)
            (p/'status.json').write_text(json.dumps({'artifact_sha256':'bad'}))
            with self.assertRaisesRegex(ValueError,'checksum'):collect(p)
            (p/'status.json').write_text(json.dumps({'artifact_sha256':hashlib.sha256(raw).hexdigest()}))
            with self.assertRaisesRegex(ValueError,'escapes'):collect(p)

if __name__=='__main__':unittest.main()
