import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from unittest.mock import patch
from analyze import load_saved_run
from plot import plot_run
from run import start_run
from solver import Solver
from tests.test_run import toy_case


class SavedOutputTests(unittest.TestCase):
    def test_plotting_only_reads_saved_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); case=root/'case'
            config,calibration=toy_case()
            start_run(config,calibration,case)
            before={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in case.rglob('*') if p.is_file()}
            with patch.object(Solver,'step',side_effect=AssertionError('plot advanced solver')):
                result=plot_run(case,root/'plots')
            self.assertEqual(result['status'],'completed_limit')
            self.assertEqual(result['pressure_event_count'],0)
            for name in ['fields.png','space_time.png','diagnostics.png','analysis.json']:
                self.assertGreater((root/'plots'/name).stat().st_size,0)
            after={str(p.relative_to(case)):hashlib.sha256(p.read_bytes()).hexdigest() for p in case.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            self.assertTrue(result['reaction_rate_available'])
            # Earlier saved runs lack this field; missing data must not imply zero reaction.
            for path in (case/'fields').glob('*.npz'):
                with np.load(path,allow_pickle=False) as saved:
                    fields={key:saved[key].copy() for key in saved.files if key!='reaction_rate'}
                np.savez_compressed(path,**fields)
            with patch.object(Solver,'step',side_effect=AssertionError('plot advanced solver')):
                legacy=plot_run(case,root/'legacy_plots')
            self.assertFalse(legacy['reaction_rate_available'])

    def test_reader_ignores_uncommitted_tail_and_rejects_missing_committed_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            case=Path(temporary)/'case'
            config,calibration=toy_case()
            result=start_run(config,calibration,case)
            path=case/'history.jsonl'
            original=path.read_text()
            path.write_text(original+json.dumps(dict(step=result['steps']+1,t=1.))+'\n{"partial":')
            data=load_saved_run(case)
            self.assertEqual(data['history'][-1]['step'],result['steps'])
            path.write_text('\n'.join(original.splitlines()[:-1])+'\n')
            with self.assertRaisesRegex(ValueError,'summary does not match'):
                load_saved_run(case)

    def test_benchmark_plot_retains_scope_and_omits_experimental_mean_overlay(self):
        from tests.test_formed_engine import formed_case
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);case=root/'case'
            config,calibration=formed_case()
            config['experimental_reference'].update(pressure_stations_mm=[0.,2.,4.],mean_pressures_kPa=[1.,2.,3.])
            start_run(config,calibration,case,benchmark_us=.03)
            with patch.object(Solver,'step',side_effect=AssertionError('plot advanced solver')):
                result=plot_run(case,root/'plots')
            self.assertEqual(result['run_mode'],'development_benchmark')
            self.assertFalse(result['experimental_pressure_overlay'])
            self.assertEqual(result['time_s'],.03e-6)


    def test_legacy_viewer_rejects_changed_inputs_and_corrupt_uncommitted_field_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            native=Path(tmp)/'run';config,calibration=toy_case()
            start_run(config,calibration,native)
            (native/'fields'/'step_999999999.npz').write_bytes(b'partial')
            self.assertTrue(load_saved_run(native)['fields'])
            path=native/'inputs.json';manifest=json.loads(path.read_text())
            manifest['resolved']['gap']*=2;path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'verified native prefix'):
                load_saved_run(native)
