"""Read-only local refill diagnostic, with explicit geometric/thermal definitions.

Usage: python docs/verification/detwave_refill_reduce.py RUN NEW_JSON
The 8--15 mm strip is ahead of the compact-case returning ridge at 30 us.
These definitions are diagnostics, not universal detonability thresholds.
"""
import json
from pathlib import Path
import sys

import numpy as np

p = Path(sys.argv[1])
manifest = json.loads((p / 'inputs.json').read_text())
r, c = manifest['resolved'], manifest['calibration']
x = (np.arange(r['nx']) + .5) * r['dx']
z = (np.arange(r['ny']) + .5) * r['dy']
region = (x > .008) & (x < .015)
rho_ref = c['p1'] / (c['R'] * 300)
j = int(np.argmin(abs(z - .001)))
k = int(np.argmin(abs(z - .003)))
rows = []
missing = []
for us in [0, 10, 20, 30, 40, 50]:
    field = p / 'fields' / f't_{us:05d}.0000us.npz'
    if not field.exists():
        missing.append(us)
        continue
    with np.load(field) as a:
        w, rate = a['primitive'], a['rate']
    temperature = w[3] / w[0] / c['R']
    fresh = w[0] * (1 - w[4])
    cold = (w[4] < .1) & (temperature < 600)
    rows.append(dict(time_us=us,
        fresh_equivalent_height_mm=float(np.mean(fresh[region].sum(1)) * r['dy'] / rho_ref * 1000),
        cold_fresh_cell_depth_mm=float(np.mean(cold[region].sum(1)) * r['dy'] * 1000),
        progress_near_1mm=float(w[4, region, j].mean()),
        progress_near_3mm=float(w[4, region, k].mean()),
        temperature_near_1mm_K=float(temperature[region, j].mean()),
        pressure_near_1mm_MPa=float(w[3, region, j].mean() / 1e6),
        rate_near_1mm_per_s=float(rate[region, j].mean())))
if not rows:
    raise ValueError('no requested saved fields available')
result = dict(run=str(p.resolve()), strip_x_mm=[8, 15], missing_times_us=missing,
    actual_sample_heights_mm=[float(z[j]*1000), float(z[k]*1000)],
    rho_reference_kg_m3=rho_ref,
    definitions='Fresh-equivalent height integrates rho*(1-progress) over the entire axial column and divides by initial fresh density. Cold-cell depth sums cells with progress<0.1 and T<600 K, not necessarily contiguous. Neither is a detonability criterion. Saved primitive arrays are float32.',
    samples=rows)
with Path(sys.argv[2]).open('x') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
