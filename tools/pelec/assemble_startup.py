"""Select verified checkpoint prefixes before combining a recovered trajectory."""
import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
from audit_native_log import EXTREMA, audit_native_log
from combine_startup import combine

TOL = 1e-12


def audit_window(log, start, end):
    lines = []
    for line in log.splitlines(keepends=True):
        match = EXTREMA.fullmatch(line.rstrip('\n')) if line.endswith('\n') else None
        if match:
            time = float(match.group(1))
            if not math.isfinite(time) or start - TOL <= time <= end + TOL:
                lines.append(line)
    return audit_native_log(''.join(lines))


def assemble(manifest_file, output):
    manifest_file, output = Path(manifest_file), Path(output)
    manifest = json.loads(manifest_file.read_text())
    segments = manifest['segments']
    changes = {x['run_id']: x for x in manifest.get('policy_changes', [])}
    if not segments:
        raise ValueError('Empty checkpoint trajectory')
    for previous, current in zip(segments, segments[1:]):
        if not current.get('restart_checkpoint', '').startswith(previous['run_id'] + '/chk'):
            raise ValueError('Broken checkpoint ancestry')
        if not re.fullmatch('[0-9a-f]{64}', current.get('checkpoint_header_sha256', '')):
            raise ValueError('Missing native checkpoint-header evidence')
        if current['restart_time_s'] < previous.get('restart_time_s', 0):
            raise ValueError('Checkpoint time runs backwards')
    output.mkdir(parents=True, exist_ok=True)
    trimmed, provenance = [], []
    for index, segment in enumerate(segments):
        source = Path(segment['directory'])
        original = json.loads((source / 'checks.json').read_text())
        allocation = json.loads((source / 'allocation.json').read_text())
        if json.loads((source / 'fetch.json').read_text())['run_id'] != segment['run_id']:
            raise ValueError('Run identity mismatch')
        if index and 'amr.restart=/results/' + segment['restart_checkpoint'] not in allocation['command']:
            raise ValueError('Checkpoint does not match actual allocation')
        start = segment.get('restart_time_s', 0.)
        with np.load(source / 'preview.npz') as data:
            end = segments[index + 1]['restart_time_s'] if index + 1 < len(segments) else float(data['time_s'][-1])
            if np.any(data['time_s'] < start - TOL):
                raise ValueError('Source includes frames before its restart')
            select = (data['time_s'] >= start - TOL) & (data['time_s'] <= end + TOL)
            # Regridding can change sampled values at the same physical instant.
            # Keep the parent's frame, never average the two or hide a conflict.
            if segment['run_id'] in changes:
                if abs(changes[segment['run_id']]['time_s'] - start) > TOL:
                    raise ValueError('Policy change does not match restart time')
                select &= data['time_s'] > start + TOL
            if not select.any():
                raise ValueError('No retained native frames in segment')
            target = output / 'segments' / f'{index:02d}_{segment["run_id"]}'
            target.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(target / 'preview.npz', **{
                k: data[k] if k in ('theta_rad', 'z_m') else data[k][select] for k in data.files})
            retained_times = data['time_s'][select].tolist()
        rows = [r for r in original['rows'] if start - TOL <= r['time_s'] <= end + TOL]
        audit = audit_window((source / 'solver.log').read_text(), start, end)
        species = audit['fields'].get('massfrac', {})
        closure = audit['every_step_species_sum']
        checks = {
            'finite': all(r['finite'] for r in rows),
            'species_nonnegative': all(r['min_species'] >= -1e-10 for r in rows),
            'species_sum': all(r['species_sum_error'] < 1e-8 for r in rows),
            'positive_pressure': all(r['pressure_Pa'][0] > 0 for r in rows),
            'thermo_range': all(200 <= r['temperature_K'][0] and r['temperature_K'][1] <= 5000 for r in rows),
            'every_step_finite': bool(audit['fields']) and all(v['nonfinite_samples'] == 0 for v in audit['fields'].values()),
            'every_step_species_sum': bool(closure['samples']) and closure['maximum_absolute_error'] < 1e-8,
            'every_step_species_nonnegative': bool(species.get('samples')) and species.get('minimum') is not None and species['minimum'] >= -1e-10,
        }
        history = {'samples': species.get('samples', 0), 'minimum_mass_fraction': species.get('minimum'),
                   'time_interval_s': [start, end], 'note': 'Native extrema restricted to the retained checkpoint interval.'}
        (target / 'checks.json').write_text(json.dumps({'rows': rows, 'checks': checks,
            'every_step_species': history, 'native_log_audit': audit, 'physical_validation_passed': False}, indent=2) + '\n')
        for name in ('case.json', 'allocation.json', 'fetch.json'):
            shutil.copy2(source / name, target / name)
        provenance.append({**segment, 'retained_interval_s': [start, end], 'retained_native_times_s': retained_times,
            'source_checks_sha256': hashlib.sha256((source / 'checks.json').read_bytes()).hexdigest(),
            'source_preview_sha256': hashlib.sha256((source / 'preview.npz').read_bytes()).hexdigest(),
            'original_full_run_checks': original['checks'], 'retained_prefix_checks': checks,
            'retained_log_audit': audit, 'policy_change': changes.get(segment['run_id'])})
        trimmed.append(target)
    result = combine(trimmed, output)
    case = json.loads((output / 'case.json').read_text())
    case['trajectory_policy_changes'] = manifest.get('policy_changes', [])
    (output / 'case.json').write_text(json.dumps(case, indent=2) + '\n')
    (output / 'trajectory_provenance.json').write_text(json.dumps({'volume': manifest['volume'],
        'segments': provenance, 'scope': 'Actual checkpoint prefixes only. Abandoned suffixes remain preserved separately; no temporal interpolation.'}, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest'); parser.add_argument('output')
    args = parser.parse_args()
    print(assemble(args.manifest, args.output))
