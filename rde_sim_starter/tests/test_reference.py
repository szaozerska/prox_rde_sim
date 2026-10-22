"""Reference bookkeeping and independent algebra checks; no optional install needed."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import yaml
from reference import jump_residuals, sampled_crossing, validate_reference_inputs, compute_reference
from plot import plot_reference
from solver import Solver

ROOT=Path(__file__).resolve().parents[1]


class ReferenceTests(unittest.TestCase):
    def test_jump_residuals_against_analytic_normal_shock(self):
        gamma,R,T,p,M=1.4,287.,300.,1e5,3.
        rho=p/(R*T);speed=M*np.sqrt(gamma*R*T);cp=gamma*R/(gamma-1)
        ratio=(gamma+1)*M*M/(2+(gamma-1)*M*M)
        pressure_ratio=1+2*gamma/(gamma+1)*(M*M-1)
        upstream=dict(rho=rho,p=p,h=cp*T)
        downstream=dict(rho=rho*ratio,p=p*pressure_ratio,h=cp*T*pressure_ratio/ratio)
        residuals=jump_residuals(upstream,downstream,speed)
        self.assertLess(max(abs(v) for v in residuals.values()),1e-14)
        downstream['p']*=1.1
        self.assertGreater(abs(jump_residuals(upstream,downstream,speed)['momentum']),.01)

    def test_heat_fraction_crossing_uses_first_event_without_extrapolation(self):
        self.assertAlmostEqual(sampled_crossing([0.,1.,2.,3.],[0.,.8,.1,1.],.4),.5)
        self.assertIsNone(sampled_crossing([0.,1.],[0.,.8],.9))
        self.assertEqual(sampled_crossing([0.,1.],[.7,.8],.5),0.)
        for time,values,target in [([1.,0.],[0.,1.],.5),([0.,1.],[0.,np.nan],.5),([0.,1.],[0.,1.],np.nan)]:
            with self.assertRaises(ValueError):sampled_crossing(time,values,target)

    def test_mismatched_calibration_rejected_before_optional_dependencies(self):
        config=yaml.safe_load((ROOT/'config.yaml').read_text())
        calibration=json.loads((ROOT/'calib.json').read_text())
        validate_reference_inputs(config,calibration)
        original=copy.deepcopy(config);config['operating_point']['phi']+=.05
        with tempfile.TemporaryDirectory() as temp, patch('reference._libraries',side_effect=AssertionError('loaded dependencies')):
            out=Path(temp)/'mismatch'
            with self.assertRaisesRegex(ValueError,'does not match'):
                compute_reference(config,calibration,out)
            self.assertFalse(out.exists())
        self.assertEqual(original['operating_point']['phi'],1.176)

    def test_failed_reference_retains_inputs_and_reports_failure(self):
        config=yaml.safe_load((ROOT/'config.yaml').read_text());c=json.loads((ROOT/'calib.json').read_text())
        with tempfile.TemporaryDirectory() as temp, patch('reference._libraries',side_effect=RuntimeError('dependency unavailable')):
            out=Path(temp)/'failed'
            with self.assertRaisesRegex(RuntimeError,'dependency unavailable'):compute_reference(config,c,out)
            self.assertEqual(json.loads((out/'failure.json').read_text())['status'],'failed')
            self.assertEqual(json.loads((out/'inputs.json').read_text())['calibration'],c)
            self.assertFalse((out/'summary.json').exists())
            with self.assertRaises(FileExistsError):compute_reference(config,c,out)

    def test_reference_plotting_uses_only_saved_arrays(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);run=root/'reference';run.mkdir()
            nominal=dict(phi=1.176,pressure_Pa=377916.,CJ_speed_mps=2532.,q_equilibrium_Jkg=5.42e6)
            report=dict(nominal=nominal,neighborhood=[nominal],surrogate=dict(D_CJ=2471.,q=5.5e6),
                        znd=dict(induction_time_max_dTdt_s=1.34e-7,peak_thermicity_time_s=1.34e-7))
            (run/'summary.json').write_text(json.dumps(report))
            data={prefix+key:np.array(values) for prefix in ['', 'surrogate_'] for key,values in [
                ('distance_m',[0.,4e-5,5e-4]),('temperature_K',[2000.,3500.,4000.]),
                ('pressure_Pa',[23e6,15e6,12e6]),('heat_fraction',[0.,.5,1.])]}
            np.savez_compressed(run/'profiles.npz',**data,time_s=[0.,1.34e-7,2e-6],dTdt_K_s=[0.,1e10,0.])
            before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}
            with patch.object(Solver,'step',side_effect=AssertionError('CFD')),patch('reference._libraries',side_effect=AssertionError('chemistry')):
                plot_reference(run,root/'plots')
            self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
            for name in ['reference_profiles.png','reference_neighborhood.png']:
                self.assertGreater((root/'plots'/name).stat().st_size,1000)
