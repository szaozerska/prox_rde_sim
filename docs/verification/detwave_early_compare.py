"""Read-only, pre-return comparison of the two Run 937 studies.

Usage: python docs/verification/detwave_early_compare.py NEW_OUTPUT.json
The fixed forward sector is appropriate only for the saved 10/15 us frames.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def compare():
    root = Path(__file__).resolve().parents[2]
    result = {'definition': 'Rightmost p > 2 p_initial in x=22..100 mm; '
              'rate maximum behind that front in same forward sector; '
              '2 mm near-front neighborhood. Valid only before periodic return; '
              'pressure threshold is not a detonation classifier.', 'cases': []}
    for name in ['detwave_original_40us', 'detwave_short_189us']:
        directory = root / 'rde_sim_starter/runs' / name
        manifest = json.loads((directory / 'inputs.json').read_text())
        with np.load(directory / 'checkpoint.npz', allow_pickle=False) as saved:
            times = saved['times'].copy()
            rings = saved['rings'].copy()
        x = (np.arange(manifest['resolved']['nx']) + .5) * manifest['resolved']['dx']
        sector = (x >= .022) & (x <= .100)
        records = []
        for time_us in [10, 15]:
            frame = int(np.argmin(abs(times * 1e6 - time_us)))
            if abs(times[frame] * 1e6 - time_us) > 1e-6:
                raise ValueError(f'{name}: missing {time_us} us frame')
            for height in [.0005, .001, .003]:
                row = int(np.argmin(abs(np.asarray(manifest['actual_ring_heights_m']) - height)))
                pressure = rings[frame, 3, :, row]
                rate = rings[frame, 5, :, row]
                front = np.flatnonzero(sector & (pressure > 2 * manifest['calibration']['p1']))[-1]
                behind = sector & (x <= x[front])
                peak = np.flatnonzero(behind)[np.argmax(rate[behind])]
                near = abs(x - x[front]) <= .002
                records.append(dict(time_us=time_us,
                    height_mm=manifest['actual_ring_heights_m'][row] * 1000,
                    front_mm=x[front] * 1000,
                    forward_pressure_max_MPa=float(pressure[sector].max()) / 1e6,
                    front_to_rate_peak_mm=(x[front] - x[peak]) * 1000,
                    near_front_rate_per_s=float(rate[near].max()),
                    forward_rate_max_per_s=float(rate[behind].max())))
        result['cases'].append(dict(case=name, latest_time_us=float(times[-1] * 1e6),
            inputs_sha256=hashlib.sha256((directory / 'inputs.json').read_bytes()).hexdigest(),
            records=records))
    return result


if __name__ == '__main__':
    with Path(sys.argv[1]).open('x') as output:
        json.dump(compare(), output, indent=2, allow_nan=False)
        output.write('\n')
