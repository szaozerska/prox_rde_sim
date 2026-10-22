"""Reproduce the saved-field collision audit, from the repository root; no CFD."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.resolve().is_relative_to(args.run.resolve()):
        raise ValueError('use a new output directory outside the native run')
    sys.path.insert(0, str(Path.cwd() / 'rde_sim_starter'))
    from contracts import iter_fields
    from coupling import periodic_peaks
    from window_report import load_native_prefix
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    inputs, summary, history, provenance = load_native_prefix(args.run)
    r, c = inputs['resolved'], inputs['calibration']
    x = (np.arange(r['nx']) + .5) * r['dx']
    z = (np.arange(r['ny']) + .5) * r['dy']
    js = [int(np.argmin(abs(z - h * .001))) for h in [.75, 3.8, 8.]]
    times, pressures, rates, metrics, hashes = [], [], [], [], []
    for f in iter_fields(args.run, inputs, summary['steps']):
        p = f['pressure'].astype(float)
        rate = f['reaction_rate'].astype(float)
        times.append(f['t'] * 1e6)
        pressures.append(p[:, js].T)
        rates.append(rate[:, js].T)
        item = dict(time_us=times[-1], rings=[])
        for j in js:
            peaks = []
            for k in periodic_peaks(p[:, j], 2 * c['p1'], .25 * c['p1'], 2):
                d = abs((x - x[k] + r['width']/2) % r['width'] - r['width']/2)
                strong = rate[:, j] > 1000
                peaks.append(dict(x_mm=float(x[k] * 1000), p_MPa=float(p[k, j]/1e6),
                    nearby_rate_per_s={str(mm): float(rate[d <= mm*.001, j].max()) for mm in [2, 4, 8]},
                    distance_to_rate_above_1000_mm=float(d[strong].min()*1000) if strong.any() else None))
            item['rings'].append(dict(z_mm=float(z[j]*1000), max_rate_per_s=float(rate[:, j].max()), peaks=peaks))
        metrics.append(item)
        path = args.run/'fields'/f"step_{f['step']:09d}.npz"
        hashes.append(dict(step=f['step'], sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    times = np.asarray(times)
    pressures, rates = np.asarray(pressures), np.asarray(rates)
    args.out.mkdir(parents=True)
    for compact, name in [(False, 'rings.png'), (True, 'near_injector.png')]:
        n = 1 if compact else 3
        fig, axs = plt.subplots(n, 2, figsize=(12, 4.5 if compact else 10),
                                sharex=True, sharey=True, squeeze=False, layout='constrained')
        for k in range(n):
            a = axs[k, 0].pcolormesh(x*1000, times, pressures[:, k]/1e6,
                cmap='magma', norm=LogNorm(.1, 22), shading='nearest')
            b = axs[k, 1].pcolormesh(x*1000, times, np.maximum(rates[:, k], 1e-4),
                cmap='inferno', norm=LogNorm(1, 1e6), shading='nearest')
            axs[k, 0].set_ylabel(f'Time [us]\nz = {z[js[k]]*1000:.3f} mm')
            for ax in axs[k]:
                ax.set_ylim(0, 140)
                ax.set_xlim(0, r['width']*1000)
        fig.colorbar(a, ax=axs[:, 0], label='Pressure [MPa]')
        fig.colorbar(b, ax=axs[:, 1], label='Reaction rate [1/s]; below 1 is dark')
        axs[0, 0].set_title('Pressure disturbances travel in both directions')
        axs[0, 1].set_title('Reaction: near-injector signal fades; higher layers still burn')
        for ax in axs[-1]:
            ax.set_xlabel('Circumferential x [mm]; periodic ends join')
        if compact:
            axs[0, 0].annotate('Far-side interaction\n~106-110 us', xy=(138.36, 110), xytext=(40, 130),
                color='white', fontsize=9, arrowprops=dict(arrowstyle='->', color='white'))
            axs[0, 1].annotate('By 40 us: maximum across\nthis ring is only 10.8 /s', xy=(27, 40), xytext=(70, 65),
                color='white', fontsize=9, arrowprops=dict(arrowstyle='->', color='white'))
        fig.suptitle(f'Existing radial_active startup | first 140 of {times[-1]:.3f} us | no new CFD')
        fig.savefig(args.out/name, dpi=150)
        plt.close(fig)
    result = dict(provenance=provenance, frame_hashes=hashes, metrics=metrics,
        ring_heights_mm=(z[js]*1000).tolist(), resolved=r, calibration=c,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        definitions=dict(pressure_candidate='p>=2*p1; prominence>=0.25*p1; minimum spacing 2 cells',
            nearby_rate='maximum within periodic +/-2,4,8 mm windows about each pressure peak',
            distance='nearest cell exceeding 1000/s; inspection threshold, not a ZND length'),
        qualifications=['Pressure maxima are not a shock/detonation classifier.',
            'Do not track identities through encounters or infer all-domain extinction from a ring.',
            'Plots show 0-140 us, metrics retain every saved frame through the committed endpoint.',
            'Times of interactions are visual assessments of saved profiles, not exact collision detection.'])
    (args.out/'metrics.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(f'Validated {len(times)} saved frames through {times[-1]:.6f} us; output: {args.out}')


if __name__ == '__main__':
    main()
