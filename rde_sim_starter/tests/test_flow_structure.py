"""Analytical controls distinguish compressive fronts, contacts and shear."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
import numpy as np
from PIL import Image
import run
from flow_structure import gradient, structure_fields, interface_cells, render_structures
from test_run import toy_case
from test_workflow import hashes


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.dx=1e-3;self.dz=1e-3
        self.x=(np.arange(128)+.5)*self.dx
        self.z=(np.arange(32)+.5)*self.dz
        shape=(128,32)
        self.f={key:np.zeros(shape) for key in ('pressure','density','u_theta','u_z','progress','reaction_rate')}
        self.f['pressure'][:]=1e5;self.f['density'][:]=1.;self.f['progress'][:]=1.
        self.r=dict(dx=self.dx,dy=self.dz)
        self.c=dict(gamma=1.4,q=5e6,p1=1e5,R=300.,T1=300.)

    def fields(self):return structure_fields(self.f,self.r,self.c,2e5)

    def test_periodic_gradient_and_known_shear_divergence(self):
        a=np.sin(2*np.pi*self.x/.128)[:,None]+3*self.z[None,:]
        gx,gz=gradient(a,self.dx,self.dz)
        np.testing.assert_allclose(gx[:,0],2*np.pi/.128*np.cos(2*np.pi*self.x/.128),atol=.021)
        np.testing.assert_allclose(gz,3.,atol=1e-12)
        self.f['u_theta'][:]=4*self.z;self.f['u_z'][:]=3*self.z
        a=self.fields()
        np.testing.assert_allclose(a['vorticity'],-4.,atol=1e-12)
        np.testing.assert_allclose(a['divergence'],3.,atol=1e-12)
        self.assertFalse(a['shock_candidate'].any())
        self.assertFalse(a['product_shear_contact_candidate'].any())

    def test_contact_is_not_shock_and_shear_contact_needs_shear(self):
        layer=np.tanh((self.z-.016)/.001)
        self.f['density'][:]=1.+.4*layer
        a=self.fields()
        self.assertGreater(a['density_gradient'].max(),100)
        self.assertFalse(a['shock_candidate'].any())
        self.assertFalse(a['product_shear_contact_candidate'].any())
        self.f['u_theta'][:]=200*layer
        a=self.fields()
        self.assertTrue(a['product_shear_contact_candidate'].any())
        self.assertFalse(a['shock_candidate'].any())
        self.f['progress'][:]=.2
        self.assertFalse(self.fields()['product_shear_contact_candidate'].any())

    def test_compressive_pressure_front_and_expansion_are_distinct(self):
        layer=np.tanh((self.x-.064)/.001)[:,None]
        self.f['pressure'][:]=2e5+1e5*layer
        self.f['density'][:]=2.+layer
        self.f['u_theta'][:]=-400*layer
        a=self.fields()
        self.assertTrue(a['shock_candidate'][60:68].any())
        self.assertFalse(a['injector_blocked'][:50].any())
        self.assertTrue(a['injector_blocked'][80:].all())
        self.f['u_theta']*=-1
        self.assertFalse(self.fields()['shock_candidate'][60:68].any())

    def test_interface_periodic_seam_but_no_axial_wrap(self):
        xi=np.zeros((8,4));xi[0,:]=1
        a=interface_cells(xi)
        self.assertTrue(a[0].all());self.assertTrue(a[-1].all())
        xi[:]=0;xi[:,0]=1
        a=interface_cells(xi)
        self.assertTrue(a[:,0].all());self.assertFalse(a[:,-1].any())

    def test_export_is_readonly_complete_and_contains_both_gifs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config,cal=toy_case();config['numerics']['snapshot_every_us']=1.
            native=root/'native';out=root/'out';run.start_run(config,cal,native)
            before=hashes(native)
            with patch('solver.Solver.step',side_effect=AssertionError('renderer launched CFD')):
                report=render_structures(native,out,seconds=2.)
            self.assertEqual(hashes(native),before)
            self.assertTrue((out/'COMPLETE').exists())
            self.assertEqual(len(report['frames']),2)
            self.assertIn('no age tracer',report['qualifications'][1])
            for name in ('unwrapped.gif','wrapped.gif'):
                with Image.open(out/name) as gif:
                    self.assertEqual(gif.n_frames,2);self.assertNotIn('loop',gif.info)
                    self.assertEqual(gif.info['duration'],2000);gif.seek(1)
                    self.assertEqual(gif.info['duration'],1500)
            with self.assertRaises(ValueError):render_structures(native,native/'view')
            with self.assertRaises(FileExistsError):render_structures(native,out)
            with patch('PIL.Image.Image.save',side_effect=OSError('disk full')):
                with self.assertRaises(OSError):render_structures(native,root/'failed')
            self.assertTrue((root/'failed'/'INCOMPLETE').exists())
            self.assertFalse((root/'failed'/'COMPLETE').exists())
