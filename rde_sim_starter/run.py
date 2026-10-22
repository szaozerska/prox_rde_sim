"""One saved reduced-annulus run, bounded by expected passage intervals.

New runs stop at three intervals; --resume extends the same saved run to five.
Reference frequency budgets time only. No wave count or actual passage detection
is inferred from that cap. Chemistry/source and outlet validation remain separate.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
import yaml

from analyze import conservation_budget, exit_contribution
from calibrate import calibrate
from physics import total_energy
from solver import Solver, InvalidStateError, NG, PERIODIC, INJECTOR, OUTFLOW

HERE = Path(__file__).resolve().parent
FORMAT_VERSION = 1


def _safe_json(value):
    if isinstance(value, np.ndarray):
        return _safe_json(value.tolist())
    if isinstance(value, np.generic):
        return _safe_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)  # preserve failed-state evidence without invalid JSON NaN tokens
    if isinstance(value, dict):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_safe_json(v) for v in value]
    return value


def _json_bytes(value):
    return (json.dumps(_safe_json(value), sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def _atomic_write(path, writer):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _write_json(path, value):
    _atomic_write(path, lambda stream: stream.write(_json_bytes(value)))


def _write_npz(path, **arrays):
    _atomic_write(path, lambda stream: np.savez_compressed(stream, **arrays))


@contextmanager
def _run_lock(directory):
    # OS-owned lock releases even after a killed process; the small lock file may remain.
    with (Path(directory) / '.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('another process is writing this run') from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _fingerprint():
    return dict(
        source_sha256={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                       for name in ['solver.py', 'physics.py', 'run.py', 'analyze.py', 'calibrate.py']},
        python=sys.version.split()[0],
        packages={name: version(name) for name in ['numpy', 'numba', 'llvmlite', 'scipy', 'PyYAML']},
    )


def _positive(value, name, allow_zero=False):
    value = float(value)
    if not math.isfinite(value) or value < 0 or (not allow_zero and value == 0):
        raise ValueError(f'{name} must be finite and {"nonnegative" if allow_zero else "positive"}')
    return value


def resolve_case(config, calibration):
    """Resolve explicit model/units and numerical settings before creating output."""
    if config.get('schema_version') != 1:
        raise ValueError('case schema_version must be 1; use the current config.yaml')
    geo, op, nm = config['geometry'], config['operating_point'], config['numerics']
    model = config['model']
    if model['geometry'] != 'constant_annulus' or model['feed'] != 'premixed_plenum' or model['walls'] != 'inviscid':
        raise ValueError('this backend supports only a constant annulus, equivalent premixed plenum, and inviscid walls')
    if model['chemistry'] not in ('one_step', 'disabled'):
        raise ValueError('unsupported chemistry')
    ro = _positive(geo['r_outer_mm'], 'outer radius') * 1e-3
    ri = _positive(geo['r_inner_mm'], 'inner radius') * 1e-3
    length = _positive(geo['length_mm'], 'length') * 1e-3
    if ri >= ro:
        raise ValueError('inner radius must be smaller than outer radius; coreless geometry is unsupported')
    gap, rm = ro - ri, (ro + ri) / 2
    width = 2 * math.pi * rm
    requested_dx = _positive(nm['dx_mm'], 'cell spacing') * 1e-3
    nx, ny = round(width / requested_dx), round(length / requested_dx)
    if nx < 2 or ny < 1:
        raise ValueError('case needs at least two circumferential and one axial cells')
    f_ref = _positive(op['f_paper_kHz'], 'reference passage frequency') * 1e3
    # Reject a shared calibration that was generated for a different mixture/state.
    expected = calibrate(config)  # verify compatibility; never replace supplied parameters
    for key in ['gamma', 'R', 'q', 'k', 'Ea', 'T1', 'p1', 'D_CJ', 'L_half']:
        if not math.isclose(float(calibration[key]), expected[key], rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError(f'calibration {key} does not match the case; recalibrate explicitly')
    for key in ['p', 'T']:
        if not math.isclose(float(calibration['CJ'][key]), expected['CJ'][key], rel_tol=1e-9):
            raise ValueError(f'calibration CJ {key} does not match the case')
    gas = [calibration[key] for key in ['gamma', 'q', 'R', 'k', 'Ea']]
    if model['chemistry'] == 'disabled':
        gas[3] = 0.0
    average_start = _positive(nm['average_start_us'], 'averaging start', True) * 1e-6
    snapshot_interval = _positive(nm['snapshot_every_us'], 'snapshot interval') * 1e-6
    checkpoint_interval = _positive(nm['checkpoint_every_us'], 'checkpoint interval') * 1e-6
    max_dt = nm.get('max_step_ns')
    if max_dt is not None:
        max_dt = _positive(max_dt, 'maximum step') * 1e-9
    stations = np.asarray(config['diagnostics']['pressure_stations_mm'], dtype=float) * 1e-3
    if stations.ndim != 1 or not np.all(np.isfinite(stations)) or np.any(stations < 0) or np.any(stations > length):
        raise ValueError('pressure stations must lie within the modeled annulus')
    probe_z = _positive(nm['probe_y_mm'], 'probe position', True) * 1e-3
    if probe_z >= length:
        raise ValueError('probe must lie inside the axial domain')
    resolved = dict(nx=nx, ny=ny, dx=width / nx, dy=length / ny,
                    width=width, length=length, r_outer=ro, r_mean=rm, gap=gap,
                    gas=gas, cfl=nm['cfl'],
                    injector=[op['p_plenum_kPa'] * 1e3, op['T_plenum_K'], geo['area_ratio'], model['discharge_coefficient']],
                    p_back=op['p_back_kPa'] * 1e3, f_ref=f_ref,
                    average_start=average_start, snapshot_interval=snapshot_interval,
                    checkpoint_interval=checkpoint_interval, max_dt=max_dt,
                    probe_index=min(int(probe_z / (length / ny)), ny - 1),
                    pressure_stations=stations.tolist(), initialization=config['initialization'])
    return resolved


def periodic_band(x, start, width, circumference):
    if not 0 < width <= circumference:
        raise ValueError('periodic band width must lie in (0, circumference]')
    return (x - start) % circumference < width


def build_solver(resolved, calibration, initialize=True):
    r = resolved
    solver = Solver(r['nx'], r['ny'], r['dx'], r['dy'], tuple(r['gas']),
                    (PERIODIC, PERIODIC, INJECTOR, OUTFLOW), inj=r['injector'],
                    p_back=r['p_back'], cfl=r['cfl'])
    if not initialize:
        return solver
    x = (np.arange(solver.nx) + .5) * solver.dx
    z = (np.arange(solver.ny) + .5) * solver.dy
    X, Z = np.meshgrid(x, z, indexing='ij')
    init = r['initialization']
    p1, T1 = calibration['p1'], calibration['T1']
    if init['kind'] == 'uniform':
        pressure = np.full_like(X, init.get('pressure_Pa', p1))
        temperature = np.full_like(X, init.get('temperature_K', T1))
        progress = np.full_like(X, init.get('progress', 0.0))
        baseline_energy = None
    elif init['kind'] == 'ignition':
        height = _positive(init['fill_height_mm'], 'fill height') * 1e-3
        if height > r['length']:
            raise ValueError('fill height exceeds domain length')
        fresh = Z < height
        temperature = np.where(fresh, T1, _positive(init['product_temperature_K'], 'product temperature'))
        progress = np.where(fresh, 0., 1.)
        pressure = np.full_like(X, p1)
        rho = pressure / (solver.R * temperature)
        baseline_energy = float(total_energy(rho, init.get('u_theta', 0.), init.get('u_z', 0.),
                                            pressure, progress, solver.g, solver.q).sum()
                                * solver.dx * solver.dy * r['gap'])
        patches = init['patches']
        if not isinstance(patches, int) or isinstance(patches, bool) or patches < 1:
            raise ValueError('ignition patches must be a positive integer')
        patch_width = _positive(init['patch_width_mm'], 'ignition width') * 1e-3
        behind_width = _positive(init['products_behind_mm'], 'products-behind width') * 1e-3
        if patch_width + behind_width > r['width'] / patches:
            raise ValueError('ignition/product masks overlap adjacent patches')
        offset = float(init['offset_fraction'])
        multiplier = _positive(init['pressure_multiplier'], 'ignition pressure multiplier')
        if not math.isfinite(offset):
            raise ValueError('ignition offset must be finite')
        for n in range(patches):
            x0 = (offset + n / patches) * r['width']
            behind = periodic_band(X, x0 - behind_width, behind_width, r['width']) & fresh
            patch = periodic_band(X, x0, patch_width, r['width']) & fresh
            progress[behind] = 1.
            temperature[behind] = init['product_temperature_K']
            pressure[patch] = multiplier * calibration['CJ']['p']
            temperature[patch] = calibration['CJ']['T']
            progress[patch] = 1.
    else:
        raise ValueError('initialization kind must be uniform or ignition')
    if not np.all(np.isfinite(temperature)) or np.any(temperature <= 0):
        raise ValueError('initial temperature must be finite and positive')
    solver.set_prim(pressure / (solver.R * temperature), init.get('u_theta', 0.),
                    init.get('u_z', 0.), pressure, progress)
    resolved['initialization_energy_change_J'] = (None if baseline_energy is None else
            float(solver.conserved_totals()[3] * r['gap'] - baseline_energy))
    return solver


def _manifest_hash(directory):
    return hashlib.sha256((Path(directory) / 'inputs.json').read_bytes()).hexdigest()


def _snapshot(solver, resolved, directory):
    W = solver.prim()
    _write_npz(Path(directory) / 'fields' / f'step_{solver.steps:09d}.npz',
               t=np.array(solver.t), step=np.array(solver.steps), pressure=W[3].astype('float32'),
               progress=W[4].astype('float32'), density=W[0].astype('float32'),
               u_theta=W[1].astype('float32'), u_z=W[2].astype('float32'),
               temperature=(W[3] / (solver.R * W[0])).astype('float32'))


def _checkpoint(solver, state, directory, history):
    if _manifest_hash(directory) != state['inputs_sha256']:
        raise ValueError('saved inputs changed during the run')
    history.flush()
    os.fsync(history.fileno())
    metadata = dict(format_version=FORMAT_VERSION, inputs_sha256=state['inputs_sha256'],
                    t=solver.t, steps=solver.steps, rho_min=solver.rho_min, p_min=solver.p_min,
                    invalid_state_count=solver.invalid_state_count, last_failure=solver.last_failure,
                    history_bytes=history.buffer.tell(), average_weight=state['average_weight'],
                    snapshot_tick=state['snapshot_tick'], checkpoint_tick=state['checkpoint_tick'],
                    passage_tick=state['passage_tick'])
    _write_npz(Path(directory) / 'checkpoint.npz',
               state_json=np.array(_json_bytes(metadata).decode()),
               U=solver.U[:, NG:-NG, NG:-NG], initial_totals=state['initial_totals'],
               cumulative_boundary=solver.cumulative_boundary, cumulative_source=solver.cumulative_source,
               average_sum=state['average_sum'])


def _history_row(solver, r):
    W = solver.prim()
    profile = W[3].mean(axis=0)
    z = (np.arange(solver.ny) + .5) * solver.dy
    budget = conservation_budget(solver.conserved_totals(), r['initial_totals'],
                                 solver.cumulative_boundary, solver.cumulative_source,
                                 r['gap'], r['r_mean'])
    row = dict(step=solver.steps, t=solver.t, dt=0., inventory=budget['inventory'],
               residual=budget['residual'], angular_residual=budget['angular_residual'],
               pressure_stations=np.interp(r['pressure_stations'], z, profile).tolist(),
               exit_cell_force_estimate_N=exit_contribution(W[0, :, -1], W[2, :, -1],
                                                          W[3, :, -1], solver.dx * r['gap'], r['p_back']))
    mach = W[2, :, -1] / np.sqrt(solver.g * W[3, :, -1] / W[0, :, -1])
    row.update(exit_cell_axial_mach_min=float(mach.min()), exit_cell_axial_mach_max=float(mach.max()),
               exit_cell_subsonic_fraction=float(np.mean(np.abs(mach) < 1)),
               exit_cell_reverse_fraction=float(np.mean(mach < 0)))
    if solver.last_step_budget is not None:
        step = solver.last_step_budget
        rates = step['boundary'] * r['gap'] / step['dt']
        row.update(dt=step['dt'], boundary_integral=step['boundary'] * r['gap'],
                   source_integral=step['source'] * r['gap'],
                   mdot_in=rates[2, 0], mdot_out=rates[3, 0],
                   exit_numerical_force_N=rates[3, 2] - r['p_back'] * r['width'] * r['gap'])
    return row, profile


def _save_summary(solver, r, state, directory, status, target, error=None):
    budget = conservation_budget(solver.conserved_totals(), state['initial_totals'],
                                 solver.cumulative_boundary, solver.cumulative_source, r['gap'], r['r_mean'])
    weight = state['average_weight']
    average = dict(available=weight > 0, start_s=r['average_start'], end_s=solver.t,
                   duration_s=weight, interpretation='transient short-window mean; startup may be included',
                   pressure_profile_Pa=(state['average_sum'] / weight).tolist() if weight > 0 else None,
                   reason=None if weight > 0 else 'no accepted steps overlap the averaging window')
    result = dict(format_version=FORMAT_VERSION, status=status, t=solver.t, steps=solver.steps,
                  target_time_s=target, reference_frequency_Hz=r['f_ref'], observed_passages=None,
                  observed_passages_reason='front/arrival tracking is not implemented in D0',
                  average=average, budgets=budget, invalid_state_count=solver.invalid_state_count,
                  last_failure=solver.last_failure, error=error,
                  engine_torque_Nm=None, torque_reason='no wall-traction model; angular residual is a conservation check')
    _write_json(Path(directory) / 'summary.json', result)
    return _safe_json(result)


def _drive(solver, r, state, directory, target_passages):
    directory = Path(directory)
    target = target_passages / r['f_ref']
    if target <= solver.t:
        raise ValueError('requested total cap must be later than the saved state')
    r = dict(r, initial_totals=state['initial_totals'])
    last_progress = time.monotonic()
    with (directory / 'history.jsonl').open('a', encoding='utf8') as history:
        if solver.steps == 0 and history.tell() == 0:
            row, _ = _history_row(solver, r)
            history.write(json.dumps(_safe_json(row), allow_nan=False) + '\n')
            _snapshot(solver, r, directory)
            _checkpoint(solver, state, directory, history)
        _save_summary(solver, r, state, directory, 'running', target)
        coherent = True
        try:
            while solver.t < target:
                stops = [target, state['snapshot_tick'] * r['snapshot_interval'],
                         state['checkpoint_tick'] * r['checkpoint_interval'],
                         state['passage_tick'] / r['f_ref']]
                stop = min(stops)
                limit = stop - solver.t
                if r['max_dt'] is not None:
                    limit = min(limit, r['max_dt'])
                previous_time = solver.t
                coherent = False
                try:
                    solver.step(dt_max=limit)
                except InvalidStateError:
                    # The solver rejects invalid RK candidates before committing state.
                    coherent = True
                    raise
                row, profile = _history_row(solver, r)
                history.write(json.dumps(_safe_json(row), allow_nan=False) + '\n')
                history.flush()
                overlap = max(0., solver.t - max(previous_time, r['average_start']))
                state['average_sum'] += overlap * profile
                state['average_weight'] += overlap
                snapshot_due = solver.t >= state['snapshot_tick'] * r['snapshot_interval']
                checkpoint_due = solver.t >= state['checkpoint_tick'] * r['checkpoint_interval']
                if snapshot_due:
                    state['snapshot_tick'] += 1
                if solver.t >= state['passage_tick'] / r['f_ref']:
                    state['passage_tick'] += 1
                if checkpoint_due:
                    state['checkpoint_tick'] += 1
                coherent = True  # state, history, accumulators and schedules now agree
                if snapshot_due:
                    _snapshot(solver, r, directory)
                if checkpoint_due:
                    _checkpoint(solver, state, directory, history)
                    _save_summary(solver, r, state, directory, 'running', target)
                if time.monotonic() - last_progress >= 5.:
                    print(f't={solver.t * 1e6:.3f} us / {target * 1e6:.3f} us; step={solver.steps}', flush=True)
                    last_progress = time.monotonic()
            _snapshot(solver, r, directory)
            _checkpoint(solver, state, directory, history)
            return _save_summary(solver, r, state, directory, 'completed_limit', target)
        except BaseException as error:
            # Never checkpoint between accepting a step and recording its history.
            # A killed process or an I/O error can leave a tail; resume preserves it
            # separately and continues from the last complete checkpoint.
            failure = dict(type=type(error).__name__, message=str(error),
                           attempted_time_s=solver.t, last_failure=solver.last_failure)
            if coherent:
                try:
                    _checkpoint(solver, state, directory, history)
                    _snapshot(solver, r, directory)
                except (OSError, ValueError):
                    pass  # retain the original error and the previous atomic checkpoint
            try:
                saved_solver, saved_r, saved_state, _ = _load_checkpoint(directory)
                _save_summary(saved_solver, saved_r, saved_state, directory,
                              'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                              target, failure)
            except (OSError, ValueError, KeyError):
                pass  # full disks cannot guarantee a new status file
            raise


def start_run(config, calibration, directory, test_passages=3, source_text=None):
    if test_passages != 3:
        raise ValueError('new development runs use three intervals; resume the saved run to extend to five')
    # JSON round trip isolates the run from later mutation of caller dictionaries.
    config = json.loads(json.dumps(config, allow_nan=False))
    calibration = json.loads(json.dumps(calibration, allow_nan=False))
    r = resolve_case(config, calibration)
    solver = build_solver(r, calibration)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with _run_lock(directory):
        (directory / 'fields').mkdir()
        manifest = dict(format_version=FORMAT_VERSION, created_utc=datetime.now(timezone.utc).isoformat(),
                        config=config, calibration=calibration, resolved=r,
                        source_text=source_text, implementation=_fingerprint(),
                        definitions=dict(boundary_order=['left', 'right', 'bottom', 'top'],
                            boundary_normals=['+theta', '+theta', '+z', '+z'],
                            conserved_order=['mass', 'azimuthal_momentum', 'axial_momentum', 'total_energy', 'reacted_mass'],
                            conserved_units=['kg', 'kg m/s', 'kg m/s', 'J', 'kg'],
                            angular_momentum_units='kg m^2/s', pressure_units='Pa', time_units='s',
                            pressure_operator='circumferential cell-centre mean, axial interpolation with endpoint extension',
                            total_energy='thermal + kinetic + unspent chemical energy',
                            force='annulus-exit numerical momentum/pressure contribution; not whole-engine thrust'))
        _write_json(directory / 'inputs.json', manifest)
        state = dict(inputs_sha256=_manifest_hash(directory),
                     initial_totals=solver.conserved_totals(), average_sum=np.zeros(solver.ny),
                     average_weight=0., snapshot_tick=1, checkpoint_tick=1, passage_tick=1)
        return _drive(solver, r, state, directory, test_passages)


def _load_checkpoint(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'inputs.json').read_text())
    if manifest['format_version'] != FORMAT_VERSION or manifest['implementation'] != _fingerprint():
        raise ValueError('restart requires the same format, solver source and numerical environment')
    r = manifest['resolved']
    solver = build_solver(r, manifest['calibration'], initialize=False)
    with np.load(directory / 'checkpoint.npz', allow_pickle=False) as saved:
        metadata = json.loads(str(saved['state_json']))
        if metadata['format_version'] != FORMAT_VERSION or metadata['inputs_sha256'] != _manifest_hash(directory):
            raise ValueError('checkpoint does not match saved inputs')
        interior = saved['U']
        if interior.shape != (5, solver.nx, solver.ny):
            raise ValueError('checkpoint shape does not match saved geometry')
        solver.U[:, NG:-NG, NG:-NG] = interior
        solver.t, solver.steps = metadata['t'], metadata['steps']
        if not math.isfinite(solver.t) or not 0 <= solver.t <= 5 / r['f_ref'] or not isinstance(solver.steps, int) or solver.steps < 0:
            raise ValueError('invalid checkpoint time/step')
        solver.rho_min, solver.p_min = metadata['rho_min'], metadata['p_min']
        solver.invalid_state_count = metadata['invalid_state_count']
        solver.last_failure = metadata['last_failure']
        solver._check_state(solver.U, 'checkpoint load')
        for name, shape in [('cumulative_boundary', (4, 5)), ('cumulative_source', (5,))]:
            value = saved[name]
            if value.shape != shape or not np.all(np.isfinite(value)):
                raise ValueError('invalid checkpoint ' + name)
            setattr(solver, name, value.copy())
        state = {name: metadata[name] for name in ['inputs_sha256', 'average_weight', 'snapshot_tick', 'checkpoint_tick', 'passage_tick']}
        state['initial_totals'] = saved['initial_totals'].copy()
        state['average_sum'] = saved['average_sum'].copy()
    if state['initial_totals'].shape != (5,) or state['average_sum'].shape != (solver.ny,):
        raise ValueError('invalid checkpoint accumulator shape')
    if not np.all(np.isfinite(state['initial_totals'])) or not np.all(np.isfinite(state['average_sum'])):
        raise ValueError('nonfinite checkpoint accumulator')
    if not math.isfinite(state['average_weight']) or not 0 <= state['average_weight'] <= solver.t * (1 + 1e-12):
        raise ValueError('invalid checkpoint averaging duration')
    next_events = dict(snapshot_tick=state['snapshot_tick'] * r['snapshot_interval'],
                       checkpoint_tick=state['checkpoint_tick'] * r['checkpoint_interval'],
                       passage_tick=state['passage_tick'] / r['f_ref'])
    for key, event_time in next_events.items():
        if not isinstance(state[key], int) or state[key] < 1 or event_time <= solver.t:
            raise ValueError('invalid checkpoint output schedule')
    return solver, r, state, metadata


def _recover_outputs(directory, metadata):
    """Preserve any writes beyond the saved checkpoint, then restore its history prefix."""
    directory = Path(directory)
    history = directory / 'history.jsonl'
    offset = metadata['history_bytes']
    if not isinstance(offset, int) or offset < 1 or history.stat().st_size < offset:
        raise ValueError('history is missing the checkpoint prefix')
    with history.open('rb') as stream:
        prefix = stream.read(offset)
        tail = stream.read()
    if not prefix.endswith(b'\n'):
        raise ValueError('checkpoint history offset is not a complete record')
    last = json.loads(prefix.splitlines()[-1])
    if last['step'] != metadata['steps'] or last['t'] != metadata['t']:
        raise ValueError('checkpoint time/step does not match history')
    extras = [p for p in (directory / 'fields').glob('step_*.npz') if int(p.stem.split('_')[1]) > metadata['steps']]
    if tail or extras:
        recovery = directory / 'recovery' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        recovery.mkdir(parents=True)
        if tail:
            (recovery / 'history_after_checkpoint.jsonl').write_bytes(tail)
            with history.open('r+b') as stream:
                stream.truncate(offset)
        for p in extras:
            p.rename(recovery / p.name)


def resume_run(directory, test_passages=5):
    if test_passages not in (3, 5):
        raise ValueError('resume total cap must be three or five intervals')
    directory = Path(directory)
    with _run_lock(directory):
        solver, r, state, metadata = _load_checkpoint(directory)
        if test_passages / r['f_ref'] <= solver.t:
            raise ValueError('requested total cap must be later than the saved state')
        _recover_outputs(directory, metadata)
        return _drive(solver, r, state, directory, test_passages)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, help='new-run YAML case; defaults to config.yaml')
    parser.add_argument('--calibration', type=Path, help='new-run surrogate JSON; defaults to calib.json')
    parser.add_argument('--out', type=Path, help='new output directory; must not exist')
    parser.add_argument('--resume', type=Path, help='existing run directory; uses only its saved inputs')
    parser.add_argument('--test-passages', type=int, choices=(3, 5), help='total expected intervals, not additional intervals')
    args = parser.parse_args(argv)
    try:
        if args.resume:
            if args.case or args.calibration or args.out:
                parser.error('--resume cannot be combined with new-run inputs/output')
            result = resume_run(args.resume, args.test_passages or 5)
        else:
            if args.out is None:
                parser.error('a new run needs --out')
            case = args.case or HERE / 'config.yaml'
            calibration = args.calibration or HERE / 'calib.json'
            case_text, calibration_text = case.read_text(), calibration.read_text()
            result = start_run(yaml.safe_load(case_text), json.loads(calibration_text), args.out,
                               args.test_passages or 3,
                               dict(case_yaml=case_text, calibration_json=calibration_text))
    except KeyboardInterrupt:
        print('Interrupted; resume uses the last complete checkpoint.', file=sys.stderr)
        return 130
    except (ValueError, RuntimeError, OSError, KeyError, FloatingPointError) as error:
        print(f'Run stopped: {error}', file=sys.stderr)
        return 2
    print(f"{result['status']}: {result['t'] * 1e6:.3f} us, {result['steps']} steps")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
