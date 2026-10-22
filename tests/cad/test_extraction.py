"""Geometry and adapter checks; actual archived STEP regression is opt-in."""
from copy import deepcopy
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import yaml

from cad_extract.geometry import annulus, cylinder, rigid_transform, unique_bores
from cad_extract.pipeline import export_case, extract
from cad_extract.step import inspect_step

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'rde_sim_starter'))
from contracts import geometry_contract

IDENTITY = dict(rotation=np.eye(3).tolist(), translation_m=[0, 0, 0])


def face(tag, radius, point=(0, 0, 0), axis=(0, 0, 1), extent=(0, .09)):
    return dict(tag=tag, kind='Cylinder', radius_m=radius,
                axis_point_m=list(point), axis=list(axis), support_interval_m=list(extent))


def fake_mapping():
    """A different annulus, with an inlet 20 mm downstream of the frame origin."""
    mapping = json.loads((ROOT/'examples/cad/mundt_review_mapping.json').read_text())
    for spec in mapping['parts'].values():
        spec['transform'] = deepcopy(IDENTITY)
    mapping['bore_families'] = {k: v for k, v in mapping['bore_families'].items()
                              if k in ['fuel', 'oxidizer']}
    mapping['additional_cylinders'] = {}
    source = dict(name='synthetic', sha256='a'*64)
    reader = dict(version=mapping['reader_version'])
    inv = {
        'core': dict(source=source, reader=reader, faces=[face(1, .028, extent=(.02, .11)),
            dict(tag=3, kind='Plane', properties=[0, 0, 1, -.02]),
            dict(tag=2, kind='Plane', properties=[0, 0, 1, -.11])]),
        'sleeve': dict(source=source, reader=reader, faces=[face(8, .045, extent=(.02, .13))]),
        'injector': dict(source=source, reader=reader, faces=[
            face(1, .0004, (.034, 0, .02), (.5, 0, math.sqrt(.75))),
            face(2, .0006, (.036, 0, .02), (-.5, 0, math.sqrt(.75))),
            dict(tag=528, kind='Plane', properties=[0, 0, 1, -.02])])}

    def read(path, expected_sha256):
        key = next(k for k, v in mapping['parts'].items() if v['file'] == Path(path).name)
        return deepcopy(inv[key])
    return mapping, inv, read


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.base = yaml.safe_load((ROOT/'rde_sim_starter/config.yaml').read_text())

    def test_reference_preserves_operating_chemistry_and_contract(self):
        saved = deepcopy(self.base)
        case = export_case(self.base, None, 'paper', acknowledge_reduction=True)
        self.assertEqual(case['geometry'], dict(r_outer_mm=38.1, r_inner_mm=33.1,
                                               length_mm=76.2, area_ratio=.110))
        for name in set(self.base)-{'geometry', 'diagnostics'}:
            self.assertEqual(case[name], self.base[name])
        self.assertEqual(self.base, saved)
        self.assertEqual(geometry_contract(case)['dimensions']['length_m'], .0762)
        self.assertFalse(case['cad_provenance']['fluid_domain_verified'])

    def test_adapter_requires_acknowledgement_and_supported_backend(self):
        with self.assertRaisesRegex(ValueError, 'acknowledgement'):
            export_case(self.base, None, 'paper')
        self.base['model']['geometry'] = 'full_3d'
        with self.assertRaisesRegex(ValueError, 'constant_annulus'):
            export_case(self.base, None, 'paper', acknowledge_reduction=True)

    def test_split_faces_join_but_nearby_holes_stay_distinct(self):
        a = cylinder(face(1, .0004, (.03, 0, 0)), IDENTITY)
        b = cylinder(face(2, .0004, (.03, 0, .04), axis=(0, 0, -1)), IDENTITY)
        c = cylinder(face(3, .0004, (.0301, 0, 0)), IDENTITY)
        bores = unique_bores([a, b, c])
        self.assertEqual(len(bores), 2)
        self.assertEqual(bores[0]['face_tags'], [1, 2])

    def test_rigid_frame_preserves_radius_and_rotates_axis(self):
        tr = dict(rotation=[[1, 0, 0], [0, 0, -1], [0, 1, 0]], translation_m=[.1, .2, .3])
        c = cylinder(face(1, .004), tr)
        np.testing.assert_allclose(c['axis'], [0, -1, 0])
        np.testing.assert_allclose(c['point'], [.1, .2, .3])
        self.assertEqual(c['radius'], .004)
        with self.assertRaisesRegex(ValueError, 'rigid'):
            rigid_transform(dict(rotation=(2*np.eye(3)).tolist(), translation_m=[0, 0, 0]))

    def test_changed_design_measures_dimensions_without_forcing_mundt_counts(self):
        mapping, _, read = fake_mapping()
        with patch('cad_extract.pipeline.inspect_step', side_effect=read):
            manifest, _ = extract(mapping, '.')
        d = manifest['dimensions']
        self.assertAlmostEqual(d['r_outer_m'], .045)
        self.assertAlmostEqual(d['r_inner_m'], .028)
        self.assertAlmostEqual(d['length_m'], .09)
        self.assertEqual(manifest['bore_families']['fuel']['bore_count'], 1)
        self.assertAlmostEqual(manifest['impingement']['height_m'], .001*math.sqrt(3))
        case = export_case(self.base, manifest, 'cad', acknowledge_reduction=True)
        self.assertAlmostEqual(case['geometry']['r_outer_mm'], 45)
        self.assertEqual(geometry_contract(case)['dimensions']['length_m'], .09)
        self.base['diagnostics']['pressure_stations_mm'] = [91]
        with self.assertRaisesRegex(ValueError, 'outside'):
            export_case(self.base, manifest, 'cad', acknowledge_reduction=True)

    def test_eccentric_or_misaligned_parts_are_rejected(self):
        for part, delta, message in [('sleeve', [.001, 0, 0], 'eccentric'),
                                     ('injector', [0, 0, .001], 'not aligned')]:
            mapping, _, read = fake_mapping()
            mapping['parts'][part]['transform']['translation_m'] = delta
            with patch('cad_extract.pipeline.inspect_step', side_effect=read):
                with self.assertRaisesRegex(ValueError, message):
                    extract(mapping, '.')

    def test_changed_reader_and_non_cylindrical_roles_are_rejected(self):
        mapping, inv, read = fake_mapping()
        inv['core']['reader'] = dict(version='changed')
        with patch('cad_extract.pipeline.inspect_step', side_effect=read):
            with self.assertRaisesRegex(ValueError, 'reader version'):
                extract(mapping, '.')
        mapping, inv, read = fake_mapping()
        inv['sleeve']['faces'][0]['kind'] = 'Cone'
        with patch('cad_extract.pipeline.inspect_step', side_effect=read):
            with self.assertRaisesRegex(ValueError, 'analytic cylinder'):
                extract(mapping, '.')

    def test_units_format_and_hash_fail_before_geometry_import(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'modified.step'
            p.write_text('modified geometry')
            with self.assertRaisesRegex(ValueError, 'source hash changed'):
                inspect_step(p, 'a'*64)
            with self.assertRaisesRegex(ValueError, 'declare length units'):
                inspect_step(p)
            with self.assertRaisesRegex(ValueError, 'STL/3MF'):
                inspect_step(Path(temp)/'unitless.stl')

    def test_annulus_consistency_and_invalid_geometry(self):
        d = annulus(.0381, .0331, .0762, .000123)
        self.assertAlmostEqual(d['circumference_m']*d['gap_m'], d['exit_area_m2'])
        self.assertAlmostEqual(d['inner_wall_area_m2']+d['outer_wall_area_m2'],
                               4*d['volume_m3']/d['hydraulic_diameter_m'])
        for ro, ri, length, area in [(.02, .03, .1, .001), (.03, .02, -.1, .001),
                                      (.03, .02, .1, 1), (.03, .02, float('nan'), 0)]:
            with self.assertRaises(ValueError):
                annulus(ro, ri, length, area)


@unittest.skipUnless(importlib.util.find_spec('gmsh'), 'optional Gmsh installation required')
class StepUnitsTests(unittest.TestCase):
    def test_embedded_mm_metre_and_inch_units_have_correct_si_scale(self):
        import gmsh
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'mm.step'
            gmsh.initialize([], readConfigFiles=False)
            try:
                gmsh.option.setNumber('General.Terminal', 0)
                gmsh.option.setString('Geometry.OCCTargetUnit', 'MM')
                gmsh.model.occ.addCylinder(0, 0, 0, 0, 0, 20, 10)
                gmsh.model.occ.synchronize()
                gmsh.write(str(p))
            finally:
                gmsh.finalize()
            raw = p.read_text()
            self.assertIn('SI_UNIT(.MILLI.,.METRE.)', raw)
            q = Path(temp)/'m.step'
            q.write_text(raw.replace('SI_UNIT(.MILLI.,.METRE.)', 'SI_UNIT($,.METRE.)'))
            inch = Path(temp)/'inch.step'
            inch_raw, count = re.subn(r'LENGTH_UNIT\(\) NAMED_UNIT\(\*\) SI_UNIT\(\.MILLI\.,\.METRE\.\)',
                "CONVERSION_BASED_UNIT('INCH',#10001) LENGTH_UNIT() NAMED_UNIT(#10002)", raw)
            self.assertEqual(count, 1)
            unit_defs = ('#10000=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT($,.METRE.));\n'
                         '#10001=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.0254),#10000);\n'
                         '#10002=DIMENSIONAL_EXPONENTS(1.,0.,0.,0.,0.,0.,0.);\n')
            pos = inch_raw.rfind('ENDSEC;')
            inch.write_text(inch_raw[:pos]+unit_defs+inch_raw[pos:])
            for source, radius, length in [(p, .01, .02), (q, 10, 20), (inch, .254, .508)]:
                inventory = inspect_step(source)
                cyl = next(f for f in inventory['faces'] if f['kind'] == 'Cylinder')
                self.assertAlmostEqual(cyl['radius_m'], radius)
                self.assertAlmostEqual(np.ptp(cyl['support_interval_m']), length)
                self.assertAlmostEqual(inventory['solids'][0]['volume_m3'], math.pi*radius**2*length)


@unittest.skipUnless(os.environ.get('RDE_CAD_SOURCE_DIR'), 'local Drive archive required')
class ArchiveRegressionTests(unittest.TestCase):
    def test_mundt_reconstruction_measured_values_and_uncertainty_flags(self):
        mapping = json.loads((ROOT/'examples/cad/mundt_review_mapping.json').read_text())
        manifest, _ = extract(mapping, os.environ['RDE_CAD_SOURCE_DIR'])
        d, families = manifest['dimensions'], manifest['bore_families']
        self.assertAlmostEqual(d['r_outer_m'], .0381, places=10)
        self.assertAlmostEqual(d['r_inner_m'], .0330962, places=10)
        self.assertAlmostEqual(d['length_m'], .0762, places=10)
        self.assertAlmostEqual(d['area_ratio'], .1095925137, places=8)
        self.assertEqual([families[k]['bore_count'] for k in ['fuel', 'oxidizer']], [72, 72])
        self.assertEqual(families['oxidizer']['surface_patch_count'], 288)
        self.assertAlmostEqual(manifest['impingement']['height_m'], .00215571044, places=10)
        self.assertAlmostEqual(manifest['impingement']['diameter_m'], .0709168, places=10)
        self.assertAlmostEqual(families['fuel']['inlet_pattern']['azimuth_spacing_min_deg'], 5)
        self.assertFalse(manifest['representation']['fluid_volume_available'])
        self.assertFalse(manifest['walls']['outer_wall']['covers_reduced_interval'])
        self.assertTrue(manifest['omissions'])


if __name__ == '__main__':
    unittest.main()
