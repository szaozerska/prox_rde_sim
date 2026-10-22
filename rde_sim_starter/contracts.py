"""Small SI contracts for the supported reduced backend; no solver imports.

Native files remain authoritative. This manifest describes their interpretation,
not a universal state-array or a promise of CAD/3D support.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def positive(value, name, zero=False):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be numeric, not boolean')
    number = float(value)
    if not math.isfinite(number) or number < 0 or (number == 0 and not zero):
        raise ValueError(f'{name} must be finite and {"nonnegative" if zero else "positive"}')
    return number


def geometry_contract(config):
    geo = config['geometry']
    if config['model']['geometry'] != 'constant_annulus':
        raise ValueError('only an explicitly selected constant_annulus reduction is supported')
    extra = set(geo) - {'r_outer_mm', 'r_inner_mm', 'length_mm', 'area_ratio'}
    if extra:
        raise ValueError(f'unsupported geometry fields: {sorted(extra)}; CAD/nonuniform geometry needs an adapter')
    ro = positive(geo['r_outer_mm'], 'outer radius') * .001
    ri = positive(geo['r_inner_mm'], 'inner radius') * .001
    length = positive(geo['length_mm'], 'length') * .001
    if ri >= ro:
        raise ValueError('constant annulus requires 0 < inner radius < outer radius; coreless unsupported')
    ratio = positive(geo['area_ratio'], 'injector area ratio', zero=True)
    if ratio > 1:
        raise ValueError('injector area ratio must be <= 1')
    rm, gap = (ri + ro) / 2, ro - ri
    area = math.pi * (ro * ro - ri * ri)
    digest = hashlib.sha256(json.dumps(geo, sort_keys=True, allow_nan=False).encode()).hexdigest()
    return dict(schema_version=1, kind='constant_annulus', units='SI',
        identity='sha256:' + digest, source=dict(kind='manual_dimensions', values=geo.copy(),
            length_unit='mm', length_to_m=0.001, sha256=digest),
        coordinates=dict(axis='+z', origin_m=[0, 0, 0], azimuth='right-handed about +z',
            reduced_coordinates=['x = r_mean * theta', 'z'], velocity_basis=['e_r', 'e_theta', 'e_z']),
        dimensions=dict(r_inner_m=ri, r_outer_m=ro, r_mean_m=rm, gap_m=gap,
            length_m=length, circumference_m=2*math.pi*rm, exit_area_m2=area,
            volume_m3=area*length, lateral_wall_area_m2=2*math.pi*(ri+ro)*length,
            injector_open_area_m2=ratio*area),
        boundaries=dict(inlet='z=0', exit='z=length', seam='periodic theta',
            inner_wall='radially averaged closure', outer_wall='radially averaged closure'),
        omissions=['radial gradients and curvature dynamics', 'separate impinging fuel/oxidizer jets',
            'downstream expansion/nozzle', 'physical pre-detonator', 'CAD surfaces'])


def case_contract(config, resolved):
    geometry = geometry_contract(config)
    return dict(schema_version=1, geometry=geometry,
        physical=dict(feed_model=config['model']['feed'],
            equivalent_plenum=dict(pressure_Pa=resolved['injector'][0], temperature_K=resolved['injector'][1],
                open_area_ratio=resolved['injector'][2], discharge_coefficient=resolved['injector'][3]),
            original_experimental_stream_reference=config.get('experimental_reference', {}),
            feed_reduction='explicit equivalent premixed plenum; separate jet mixing is not resolved',
            ambient_pressure_Pa=resolved['p_back'], models=config['model'].copy(),
            initialization=config['initialization'].copy(), pressure_stations_m=resolved['pressure_stations']),
        backend=dict(name='custom_reactive_euler_2d', dimension=2, schema_version=1,
            capabilities=dict(geometry=['constant_annulus'], feeds=['premixed_plenum'],
                walls=['inviscid', 'constant_cf', 'annular_closure'], chemistry=['one_step', 'disabled'],
                restart='native checkpoint, identical code/environment only', cad=False, radial_dynamics=False, radial_equilibrium_closure=True),
            numerical_settings={k: resolved[k] for k in ('nx', 'ny', 'dx', 'dy', 'cfl', 'source_cfl', 'max_dt')}),
        results=dict(schema_version=1, native_format_version=2,
            mesh=dict(kind='structured_uniform', topology='fixed', location='cell',
                shape=[resolved['nx'], resolved['ny']], axes=['x', 'z'],
                spacing_m=[resolved['dx'], resolved['dy']], radial_velocity='assumed zero; not resolved'),
            fields={name: dict(unit=unit, location='cell') for name, unit in
                [('pressure', 'Pa'), ('density', 'kg/m^3'), ('temperature', 'K'),
                 ('u_theta', 'm/s'), ('u_z', 'm/s'), ('progress', '1'), ('reaction_rate', '1/s')] +
                ([('inner_pressure','Pa'),('outer_pressure','Pa')] if resolved.get('radial') is not None else [])},
            pressure_type='absolute', energy_reference='thermal + kinetic + unspent chemical energy',
            native_files=dict(fields='fields/step_*.npz', history='history.jsonl', checkpoint='checkpoint.npz'),
            authoritative_integrals='RK-weighted native faces and cell sources in history; display fields are float32'))


def iter_fields(directory, inputs, max_step, selected_steps=None):
    """Yield one native snapshot at a time; do not retain a full field history."""
    r = inputs['resolved']
    shape = (r['nx'], r['ny'])
    previous = -1.
    for path in sorted((Path(directory) / 'fields').glob('step_*.npz')):
        # Exclude uncommitted files before opening them (a concurrent writer may exist).
        step = int(path.stem.split('_')[-1])
        if step > max_step or (selected_steps is not None and step not in selected_steps):
            continue
        with np.load(path, allow_pickle=False) as saved:
            if np.asarray(saved['step']).shape!=() or float(saved['step']) != step:
                raise ValueError('snapshot filename and step disagree')
            t = float(saved['t'])
            if not math.isfinite(t) or t <= previous:
                raise ValueError('snapshot times must be finite and increasing')
            arrays = {k: saved[k] for k in ('pressure', 'density', 'temperature', 'u_theta', 'u_z', 'progress', 'reaction_rate')}
            if r.get('radial') is not None:
                for key in ('inner_pressure','outer_pressure'):
                    arrays[key] = saved[key]
                    if np.any(arrays[key] <= 0):
                        raise ValueError('nonpositive reconstructed wall pressure')
            if any(v.shape != shape or not np.isfinite(v).all() for v in arrays.values()):
                raise ValueError('snapshot fields must be finite and match the native mesh')
            if (np.any(arrays['density'] <= 0) or np.any(arrays['pressure'] <= 0)
                    or np.any(arrays['temperature'] <= 0) or np.any(arrays['reaction_rate'] < 0)
                    or np.any(arrays['progress'] < -64*np.finfo(float).eps)
                    or np.any(arrays['progress'] > 1+64*np.finfo(float).eps)):
                raise ValueError('invalid snapshot physical state')
        previous = t
        yield dict(step=step, t=t, **arrays)
