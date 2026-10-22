"""Source-locked semantic mapping -> SI measurements -> explicit 2D case adapter."""
from copy import deepcopy
from decimal import Decimal
import json
import math
from pathlib import Path

import numpy as np

from .geometry import (annulus, bore_record, cylinder, impingement, plane_axial_position,
                       rigid_transform, unique_bores, unit, vector)
from .step import inspect_step, sha256


def reference():
    return json.loads(Path(__file__).with_name('mundt_76_fi_5.json').read_text())


def extract(mapping, source_dir):
    if mapping.get('schema_version') != 1:
        raise ValueError('unsupported mapping schema')
    if not mapping.get('reduction_omissions'):
        raise ValueError('a selected-surface reduction must list its omissions')
    axis = unit(mapping['coordinates']['axis'])
    origin = vector(mapping['coordinates']['origin_m'], 'origin')
    xaxis = unit(mapping['coordinates']['azimuth_zero'])
    if abs(np.dot(axis, xaxis)) > 1e-9:
        raise ValueError('azimuth_zero must be perpendicular to axis')
    yaxis = np.cross(axis, xaxis)
    tol = float(mapping['tolerances']['length_m'])
    angular_tol = float(mapping['tolerances']['axis_sine'])
    if not 0 < tol < 1e-3 or not 0 < angular_tol < .01:
        raise ValueError('invalid extraction tolerances')
    inventories = {}
    for key, spec in mapping['parts'].items():
        rigid_transform(spec['transform'])
        if len(spec.get('sha256', '')) != 64:
            raise ValueError('each part mapping must be locked to a source SHA256')
        inv = inspect_step(Path(source_dir)/spec['file'], spec['sha256'])
        if inv['reader']['version'] != mapping['reader_version']:
            raise ValueError('reader version changed; reinspect face tags before reuse')
        inventories[key] = inv

    def selected(selection):
        part = selection['part']
        matches = [f for f in inventories[part]['faces'] if f['tag'] == selection['face_tag']]
        if len(matches) != 1:
            raise ValueError(f'missing or ambiguous feature {selection}')
        return matches[0], mapping['parts'][part]['transform']

    roles = mapping['roles']
    inlet = plane_axial_position(*selected(roles['inlet_datum']), origin, axis, angular_tol)
    outlet = plane_axial_position(*selected(roles['exit_datum']), origin, axis, angular_tol)
    length = outlet-inlet
    if length <= tol:
        raise ValueError('exit must lie downstream of inlet')
    inlet_origin = origin+inlet*axis
    injector_plane = plane_axial_position(*selected(roles['injector_face']), origin, axis, angular_tol)
    if abs(injector_plane-inlet) > tol:
        raise ValueError('mapped injector face and reduced inlet datum are not aligned')
    wall_measurements = {}
    warnings = list(mapping.get('warnings', []))
    for role in ['inner_wall', 'outer_wall']:
        c = cylinder(*selected(roles[role]))
        if np.linalg.norm(np.cross(c['axis'], axis)) > angular_tol:
            raise ValueError(f'{role}: selected cylinder not parallel to engine axis')
        off = c['point']-origin
        if np.linalg.norm(off-axis*np.dot(off, axis)) > tol:
            raise ValueError(f'{role}: cylinder is eccentric to the selected engine axis')
        extent = sorted(((c['ends']-origin) @ axis).tolist())
        covers = extent[0] <= inlet+tol and extent[1] >= outlet-tol
        if not covers:
            warnings.append(f'{role} selected surface does not cover the entire annulus; '
                            'scalar continuation is an explicit approximation, not a measured gas boundary.')
        wall_measurements[role] = dict(radius_m=c['radius'], source=roles[role],
                                      axial_support_m=extent, covers_reduced_interval=covers)

    families = {}
    for role, selector in mapping['bore_families'].items():
        part = selector['part']
        tr = mapping['parts'][part]['transform']
        diameter_range = selector['diameter_range_m']
        angle_range = selector['inclination_range_deg']
        chosen = []
        for face in inventories[part]['faces']:
            if face['kind'] != 'Cylinder':
                continue
            c = cylinder(face, tr)
            angle = math.degrees(math.acos(np.clip(abs(np.dot(c['axis'], axis)), 0, 1)))
            if diameter_range[0] <= 2*c['radius'] <= diameter_range[1] and angle_range[0] <= angle <= angle_range[1]:
                chosen.append(c)
        if not chosen:
            raise ValueError(f'no cylinders match {role}; review mapping rather than guessing')
        unique = unique_bores(chosen, tol, angular_tol)
        records = [bore_record(c, inlet_origin, axis) for c in unique]
        for record in records:
            p = np.asarray(record['axis_point_m'])-inlet_origin
            record['axis_point_z_m'] = float(p @ axis)
            record['axis_point_azimuth_deg'] = float(math.degrees(math.atan2(p@yaxis, p@xaxis)) % 360)
        families[role] = dict(part=part, surface_patch_count=len(chosen), bore_count=len(unique),
                              normal_area_m2=float(sum(math.pi*c['radius']**2 for c in unique)),
                              bores=records, selector=selector)
        crossings = [b['inlet_axis_intersection_m'] for b in records]
        if all(p is not None for p in crossings):
            transverse = np.asarray(crossings)-inlet_origin
            radii = np.linalg.norm(transverse, axis=1)
            if np.any(radii <= tol):
                raise ValueError(f'{role}: inlet-axis crossing has no defined azimuth')
            phases = np.sort(np.arctan2(transverse@yaxis, transverse@xaxis))
            spacing = np.diff(np.r_[phases, phases[0]+2*math.pi])
            tangential = np.cross(axis, transverse/radii[:, None])
            directions = np.array([b['axis'] for b in records])
            families[role]['inlet_pattern'] = dict(
                radius_min_m=float(radii.min()), radius_max_m=float(radii.max()),
                azimuth_spacing_min_deg=float(np.degrees(spacing.min())),
                azimuth_spacing_max_deg=float(np.degrees(spacing.max())),
                mean_arc_pitch_m=float(2*math.pi*radii.mean()/len(records)),
                max_abs_tangential_direction_cosine=float(np.abs(np.sum(directions*tangential, axis=1)).max()))
    for first, second in [('fuel', 'oxidizer')]:
        if families[first]['part'] == families[second]['part']:
            tags = [{tag for bore in families[r]['bores'] for tag in bore['face_tags']}
                    for r in [first, second]]
            if tags[0] & tags[1]:
                raise ValueError('fuel and oxidizer selectors overlap; review semantic mapping')
    fuel, oxygen = families['fuel'], families['oxidizer']
    dims = annulus(wall_measurements['outer_wall']['radius_m'],
                   wall_measurements['inner_wall']['radius_m'], length,
                   fuel['normal_area_m2']+oxygen['normal_area_m2'])
    for role in ['fuel', 'oxidizer']:
        families[role]['normal_area_fraction_of_annulus'] = families[role]['normal_area_m2']/dims['exit_area_m2']
    additional = {}
    for name, selection in mapping.get('additional_cylinders', {}).items():
        c = cylinder(*selected(selection))
        additional[name] = dict(source=selection, radius_m=c['radius'],
                               axis=c['axis'].tolist(), axis_point_m=c['point'].tolist(),
                               axial_support_from_inlet_m=sorted(((c['ends']-inlet_origin)@axis).tolist()),
                               interpretation='surface evidence only; not a validated fluid boundary')
    meetings = impingement(fuel['bores'], oxygen['bores'], inlet_origin, axis, tol)
    ref = reference()
    paper = ref['geometry']
    comparisons = []
    measured = dict(r_outer_m=dims['r_outer_m'], r_inner_m=dims['r_inner_m'],
                    length_m=dims['length_m'], gap_m=dims['gap_m'], area_ratio=dims['area_ratio'],
                    fuel_diameter_m=float(np.mean([2*b['radius_m'] for b in fuel['bores']])),
                    oxidizer_diameter_m=float(np.mean([2*b['radius_m'] for b in oxygen['bores']])),
                    fuel_count=fuel['bore_count'], oxidizer_count=oxygen['bore_count'])
    if meetings['available']:
        measured.update(impingement_height_m=meetings['height_m'], impingement_diameter_m=meetings['diameter_m'])
    for name, value in measured.items():
        target = paper[name]
        comparisons.append(dict(parameter=name, cad=value, paper=target,
                                difference=value-target, relative_difference=(value-target)/target))
    return dict(schema_version=1, kind='selected_constant_annulus_reduction', units='SI',
                geometry_identity='source-locked parts and mapping; see provenance',
                coordinates={**mapping['coordinates'], 'inlet_position_m': inlet_origin.tolist()},
                tolerances=mapping['tolerances'], dimensions=dims, walls=wall_measurements,
                bore_families=families, additional_cylinders=additional,
                impingement=meetings, paper_comparison=comparisons,
                representation=dict(source='solid parts retained separately',
                    fluid_volume_available=False, assembled_placement_verified=False,
                    full_geometry_supported=False, reduction_requires_acknowledgement=True),
                provenance=dict(mapping=mapping, sources={k:v['source'] for k,v in inventories.items()},
                                reader={k:v['reader'] for k,v in inventories.items()}),
                omissions=mapping['reduction_omissions'], warnings=warnings,
                non_geometric_inputs=ref['not_from_cad']), inventories


def export_case(base, manifest, basis, *, acknowledge_reduction=False):
    """Export only the current solver's four supported geometry keys.

    Operating conditions, chemistry, numerics and initial conditions come from
    the supplied base case. CAD cannot supply or validate them.
    """
    if base['model']['geometry'] != 'constant_annulus':
        raise ValueError('adapter only supports the constant_annulus backend')
    if basis not in {'paper', 'cad'}:
        raise ValueError('choose paper or cad explicitly')
    if not acknowledge_reduction:
        raise ValueError('export requires explicit acknowledgement of the reduction and omissions')
    case = deepcopy(base)
    ref = reference()
    if basis == 'paper':
        d = ref['geometry']
        reason = 'Mundt Table 2-1 nominal values, not CAD-extracted measurements'
    else:
        if manifest is None or manifest.get('schema_version') != 1:
            raise ValueError('CAD export requires a measured manifest')
        d = manifest['dimensions']
        reason = 'provisional CAD selected-surface reduction; normal bore area, not projected face ellipses'
    annulus(d['r_outer_m'], d['r_inner_m'], d['length_m'],
            d['area_ratio']*math.pi*(d['r_outer_m']**2-d['r_inner_m']**2))
    stations = ref['annular_pressure_stations_mm'] if basis == 'paper' else base['diagnostics']['pressure_stations_mm']
    if any(not math.isfinite(float(z)) or not 0 <= z <= d['length_m']*1000 for z in stations):
        raise ValueError('base-case pressure station is outside the extracted annulus; review diagnostics')
    # Decimal conversion preserves nominal values such as 33.1 mm exactly as
    # serialized in the existing case, avoiding an artificial geometry identity change.
    case['geometry'] = {k: float(Decimal(str(d[k[:-3]+'_m']))*1000)
                        for k in ['r_outer_mm', 'r_inner_mm', 'length_mm']}
    case['geometry']['area_ratio'] = float(d['area_ratio'])
    case['diagnostics']['pressure_stations_mm'] = stations
    case['cad_provenance'] = dict(schema_version=1, basis=basis, interpretation=reason,
                                reference=ref['source'], operating_conditions_source='unchanged supplied base case',
                                fluid_domain_verified=False,
                                omissions=ref['reduction_omissions'] if manifest is None else manifest['omissions'])
    if manifest is not None:
        case['cad_provenance']['sources'] = manifest['provenance']['sources']
        case['cad_provenance']['warnings'] = manifest['warnings']
        case['cad_provenance']['mapping'] = manifest['provenance']['mapping']
    return case


def write_preview(manifest, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    d = manifest['dimensions']
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout='constrained')
    ax = axes[0]
    length, ri, ro = [d[k]*1000 for k in ['length_m','r_inner_m','r_outer_m']]
    ax.fill_between([0,length], ri, ro, color='#b9dae9', label='Selected annular reduction')
    for role,color in [('inner_wall','#345477'),('outer_wall','#b35b3a')]:
        wall=manifest['walls'][role]
        inlet_offset = np.dot(np.asarray(manifest['coordinates']['inlet_position_m'])
                              - np.asarray(manifest['coordinates']['origin_m']),
                              unit(manifest['coordinates']['axis']))
        z=(np.array(wall['axial_support_m'])-inlet_offset)*1000
        ax.plot(z,[wall['radius_m']*1000]*2,color=color,lw=2,label=role.replace('_',' '))
    ax.axvline(0,color='gray',ls=':');ax.axvline(length,color='gray',ls=':')
    ax.set(xlabel='Engine-axis coordinate (mm)',ylabel='Radius (mm)',
           title='Selected surfaces and reduced chamber')
    ax.legend(fontsize=8,loc='best');ax.grid(alpha=.2)
    ax=axes[1]
    for role,color in [('fuel','#b35b3a'),('oxidizer','#345477')]:
        points=np.array([b['inlet_axis_intersection_m'] for b in manifest['bore_families'][role]['bores']])
        origin=np.asarray(manifest['coordinates']['inlet_position_m'])
        axis=unit(manifest['coordinates']['axis']);xx=unit(manifest['coordinates']['azimuth_zero']);yy=np.cross(axis,xx)
        ax.scatter((points-origin)@xx*1000,(points-origin)@yy*1000,s=9,label=f'{role}: {len(points)} bore axes',color=color)
    for r in [ri,ro]:
        ax.add_patch(plt.Circle((0,0),r,fill=False,color='gray',lw=.8))
    ax.set(aspect='equal',xlabel='Transverse x (mm)',ylabel='Transverse y (mm)',title='Bore-axis intersections with inlet plane')
    ax.legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.16));ax.grid(alpha=.2)
    fig.suptitle('Mundt CAD audit | solid-part reconstruction; fluid domain not validated',fontsize=11)
    fig.savefig(destination,dpi=160)
    plt.close(fig)


def report_markdown(manifest):
    lines=['# Mundt CAD parameter audit', '',
           'Measured from the source-locked STEP reconstructions. This is a selected constant-annulus reduction, not an assembled CFD fluid domain.', '',
           '| Parameter | CAD (SI) | Paper (SI) | Difference (%) |',
           '|---|---:|---:|---:|']
    for row in manifest['paper_comparison']:
        lines.append(f"| {row['parameter']} | {row['cad']:.9g} | {row['paper']:.9g} | {100*row['relative_difference']:+.5f} |")
    lines += ['', '## Bore counting', '',
              'Areas are normal circular bore areas, summed once per distinct cylindrical axis/radius. Split B-rep faces are joined; feed passages and process-stage parts are not additional injection holes.', '']
    for role, family in manifest['bore_families'].items():
        lines.append(f"- {role}: {family['surface_patch_count']} surface patches -> {family['bore_count']} distinct bores.")
    lines += ['', '## Interpretation and unresolved geometry', '']
    lines += ['- '+x for x in manifest['warnings']+manifest['omissions']]
    lines += ['', '## Inputs CAD cannot determine', '']
    lines += ['- '+x for x in manifest['non_geometric_inputs']]
    lines += ['', 'The paper case uses nominal table values. The CAD case is a geometry sensitivity candidate; it retains the supplied base case operating/chemistry/startup settings. Neither case demonstrates sustained detonation or paper-result reproduction.', '']
    return '\n'.join(lines)
