"""Input-contract tests for source-backed startup and MPI device assignment."""
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/pelec'))
from prepare_startup import prepare_startup

class NetlStartupTests(unittest.TestCase):
    def config(self,**kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            c=prepare_startup(Path(tmp)/'case.json',**kwargs)
        inputs={line.split('=',1)[0].strip():line.split('=',1)[1].strip()
                for line in c['inputs'].splitlines() if '=' in line}
        return c,inputs

    def test_documented_initial_conditions_and_cgs_units(self):
        c,p=self.config()
        self.assertEqual(float(p['prob.p0'])/10,1e6)
        self.assertEqual(float(p['prob.exit_p'])/10,1e5)
        self.assertEqual(float(p['prob.height'])/100,.005)
        self.assertEqual(float(p['prob.seed_p'])/10,4e6)
        self.assertEqual(float(p['prob.seed_T']),3000)
        self.assertEqual(float(p['prob.seed_u']),0)
        self.assertAlmostEqual(float(p['prob.seed_angle'])*180/3.141592653589793,2)
        for key in ('prob.Y','prob.Yprod','prob.Yseed'):
            values=list(map(float,p[key].split()))
            self.assertAlmostEqual(sum(values),1,places=14)
            self.assertGreaterEqual(min(values),0)
        y=list(map(float,p['prob.Y'].split()));air=list(map(float,p['prob.Yprod'].split()))
        self.assertAlmostEqual(y[c['species'].index('CH4')],.2004397856045177,places=6)
        self.assertGreater(air[c['species'].index('N2')],.75)
        self.assertEqual(p['prob.Yseed'],p['prob.Y'])
        self.assertTrue(c['startup']['assumptions'])

    def test_resolution_changes_without_changing_startup(self):
        coarse,p=self.config(mesh_um=200);fine,q=self.config(mesh_um=100)
        self.assertAlmostEqual(coarse['finest_dx_m']*1e6,198.4375)
        self.assertAlmostEqual(fine['finest_dx_m']*1e6,99.21875)
        self.assertEqual(coarse['startup'],fine['startup'])
        self.assertEqual(p['tagging.inlet.max_level'],'1')
        self.assertEqual(q['tagging.inlet.max_level'],'2')

    def test_no_unused_amr_control_for_uniform_smoke(self):
        c,p=self.config(base_n=96,max_level=0)
        self.assertNotIn('amr.ref_ratio',p)
        self.assertNotIn('amr.regrid_int',p)

    def test_each_mpi_rank_selects_its_allocated_device(self):
        for rank in range(4):
            env=dict(os.environ,OMPI_COMM_WORLD_LOCAL_RANK=str(rank),CUDA_VISIBLE_DEVICES='GPU-a,GPU-b,GPU-c,GPU-d')
            run=subprocess.run([sys.executable,str(ROOT/'tools/pelec/mpi_gpu_rank.py'),sys.executable,'-c',
                'import os; print(os.environ["CUDA_VISIBLE_DEVICES"])'],env=env,text=True,capture_output=True,check=True)
            self.assertEqual(run.stdout.splitlines()[-1],'GPU-'+chr(ord('a')+rank))

if __name__=='__main__':unittest.main()
