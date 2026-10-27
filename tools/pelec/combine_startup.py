"""Combine native snapshots from checkpoint continuations without interpolating time."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np


def combine(sources, output):
    sources = [Path(p) for p in sources]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cases = [json.loads((p / 'case.json').read_text()) for p in sources]
    for case in cases[1:]:
        for key in ('startup', 'species', 'finest_dx_m'):
            if case[key] != cases[0][key]:
                raise ValueError(f'Cannot combine different {key}')
    for previous, current in zip(sources, sources[1:]):
        previous_id = json.loads((previous / 'fetch.json').read_text())['run_id']
        command = json.loads((current / 'allocation.json').read_text())['command']
        if not any(arg.startswith('amr.restart=/results/' + previous_id + '/chk') for arg in command):
            raise ValueError('Sources are not consecutive checkpoint continuations')
    frames, audits, provenance = {}, [], []
    coordinates = None
    for source in sources:
        audit = json.loads((source / 'checks.json').read_text())
        audits.append(audit)
        with np.load(source / 'preview.npz') as data:
            current = (data['theta_rad'], data['z_m'])
            if coordinates is None:
                coordinates = tuple(a.copy() for a in current)
            elif not all(np.array_equal(a, b) for a, b in zip(coordinates, current)):
                raise ValueError('Mismatched sampling coordinates')
            for i, t in enumerate(data['time_s']):
                key = round(float(t), 14)
                frame = {k: data[k][i].copy() for k in data.files if k not in ('time_s', 'theta_rad', 'z_m')}
                if key in frames:
                    old = frames[key][0]
                    if not all(np.allclose(old[k], frame[k], rtol=1e-10, atol=1e-10, equal_nan=True) for k in old):
                        raise ValueError(f'Conflicting native snapshots at {t}')
                    continue
                row = next(r for r in audit['rows'] if abs(r['time_s'] - t) < 1e-14)
                frames[key] = (frame, row)
        provenance.append({'directory': str(source.resolve()),
            'preview_sha256': hashlib.sha256((source / 'preview.npz').read_bytes()).hexdigest(),
            'allocation': json.loads((source / 'allocation.json').read_text()) if (source / 'allocation.json').exists() else None})
    ordered = [frames[k] for k in sorted(frames)]
    if not ordered:
        raise ValueError('No native snapshots')
    np.savez_compressed(output / 'preview.npz', time_s=[r['time_s'] for _, r in ordered],
        theta_rad=coordinates[0], z_m=coordinates[1],
        **{k: np.stack([f[k] for f, _ in ordered]) for k in ordered[0][0]})
    checks = {k: all(a['checks'].get(k, False) for a in audits) for k in set().union(*(a['checks'] for a in audits))}
    histories = [a['every_step_species'] for a in audits if a.get('every_step_species', {}).get('minimum_mass_fraction') is not None]
    worst = min(histories, key=lambda h: h['minimum_mass_fraction']) if histories else {}
    result = {'rows': [r for _, r in ordered], 'checks': checks, 'every_step_species': worst,
        'segment_species_histories': histories, 'physical_validation_passed': False,
        'sampling': 'Native checkpoint trajectory snapshots; no temporal interpolation. GIF frames may have unequal physical spacing.',
        'scope': 'Allocation records establish consecutive checkpoint lineage; input and field checks reject incompatible snapshots.',
        'sources': provenance}
    (output / 'checks.json').write_text(json.dumps(result, indent=2) + '\n')
    (output / 'case.json').write_text(json.dumps(cases[0], indent=2) + '\n')
    return {'frames': len(ordered), 'last_time_s': ordered[-1][1]['time_s']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output'); parser.add_argument('sources', nargs='+')
    args = parser.parse_args(); print(combine(args.sources, args.output))
