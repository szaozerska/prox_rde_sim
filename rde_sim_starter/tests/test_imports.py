import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ImportTests(unittest.TestCase):
    def test_imports_do_not_read_cases_run_solver_or_render(self):
        # A fresh interpreter and unrelated cwd catch argv/config/output side effects.
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            env=dict(os.environ,PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1')
            script="""
import sys
sys.argv = ['unrelated-program', '--not-a-simulator-option']
import solver
solver.Solver.step = lambda *a, **k: (_ for _ in ()).throw(AssertionError('simulation on import'))
import calibrate
calibrate.calibrate = lambda *a, **k: (_ for _ in ()).throw(AssertionError('calibration on import'))
import run, analyze, plot, test_1d, physics, coupling, experiments, reference, controlled, model_audit, short_reaction, formed, window_report, contracts, workflow_analysis, workflow
assert 'matplotlib.pyplot' not in sys.modules
assert 'cantera' not in sys.modules
assert 'sdtoolbox' not in sys.modules
"""
            result=subprocess.run([sys.executable,'-c',script],cwd=directory,env=env,capture_output=True,text=True,timeout=90)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(result.stdout,'')
            self.assertEqual(list(Path(directory).iterdir()),[])
