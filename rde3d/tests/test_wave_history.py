import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/pelec'))
from wave_history import audit_history

class WaveHistoryTests(unittest.TestCase):
    def history(self):
        rows=[]
        for t in (0.,1e-10,2e-10):
            for name,lo,hi in [('density',.001,.01),('Temp',300,4200),('pressure',1e6,2e8),('massfrac',0,.8),('sumYminus1',-1e-15,1e-15)]:
                rows.append(f'TIME = {t:g} {name} MIN = {lo:g} MAX = {hi:g}')
        return '\n'.join(rows)
    def test_complete_valid_history_passes(self):
        self.assertTrue(audit_history(self.history(),2e-10,1e-10)['passed'])
    def test_intermediate_failure_cannot_hide_behind_valid_endpoints(self):
        text=self.history().replace('TIME = 1e-10 massfrac MIN = 0','TIME = 1e-10 massfrac MIN = -1e-5')
        self.assertFalse(audit_history(text,2e-10,1e-10)['passed'])
    def test_missing_duplicate_and_nonfinite_history_fail(self):
        original=self.history()
        for text in (original.replace('TIME = 1e-10 Temp','OMITTED 1e-10 Temp'),original+'\n'+original,original.replace('MIN = 300','MIN = nan',1)):
            self.assertFalse(audit_history(text,2e-10,1e-10)['passed'])
if __name__=='__main__':unittest.main()
