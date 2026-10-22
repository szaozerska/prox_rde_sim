"""Timed, read-only GIF products from committed native snapshots; never run CFD."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from contracts import iter_fields
from window_report import load_native_prefix, reduce_window, _json_default


def playback_durations(times, seconds=14., final_hold_ms=1500):
    """Physical-time-proportional intervals, quantized to GIF's 10 ms clock."""
    times = np.asarray(times, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or not np.isfinite(times).all()
            or np.any(np.diff(times) <= 0) or not np.isfinite(seconds) or seconds <= 0):
        raise ValueError('animation needs at least two increasing times and positive playback duration')
    ticks = np.rint((times-times[0])/(times[-1]-times[0])*seconds*100).astype(int)
    if np.any(np.diff(ticks) < 2):
        raise ValueError('saved cadence is too dense for GIF playback; increase --seconds')
    return [int(v)*10 for v in np.diff(ticks)] + [int(final_hold_ms)]


def surface_blocks(values, max_theta=112, max_z=38):
    """Area-average display cells only; native data/diagnostics stay unchanged."""
    nx, nz = values.shape
    xe = np.linspace(0, nx, min(nx, max_theta)+1, dtype=int)
    ze = np.linspace(0, nz, min(nz, max_z)+1, dtype=int)
    mean = np.add.reduceat(np.add.reduceat(values.astype(float), xe[:-1], axis=0), ze[:-1], axis=1)
    mean /= np.diff(xe)[:, None]*np.diff(ze)[None, :]
    return xe, ze, mean


def fuel_accounting(inputs, summary, rows, start, end):
    """Unreacted mixture equivalent rho*(1-xi), not methane-species mass."""
    report = reduce_window(inputs, summary, rows, start, end)
    b = report['budgets']
    if not b['available']:
        raise ValueError('native inventory/source/boundary accounting required')
    first, last = b['start_inventory'], b['end_inventory']
    B, S = b['boundary_integral'], b['source_integral']
    fresh_start = float(first[0]-first[4]); fresh_end = float(last[0]-last[4])
    transport = B[:, 0]-B[:, 4]
    net = float(transport[0]-transport[1]+transport[2]-transport[3]+S[0]-S[4])
    return dict(window_s=[start, end], initial_unreacted_mixture_kg=fresh_start,
        final_unreacted_mixture_kg=fresh_end, injected_unreacted_mixture_kg=float(transport[2]),
        exited_unreacted_mixture_kg=float(transport[3]), converted_mixture_kg=float(S[4]),
        unreacted_balance_residual_kg=fresh_end-fresh_start-net,
        mass_flow=report['mass_flow'], max_scaled_budget_residual=b['max_scaled_residual'],
        definition='rho*(1-progress) integrated over the annulus; mixture-equivalent chemical inventory, not methane mass')


def render_gifs(directory, destination, start=0., end=None, seconds=14.):
    """Use every saved frame in the window; fixed scales, no interpolated fronts."""
    from PIL import Image
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    directory, destination = Path(directory), Path(destination)
    if destination.resolve().is_relative_to(directory.resolve()):
        raise ValueError('GIF output must be outside the native run')
    if destination.exists():
        raise FileExistsError(destination)
    inputs, summary, rows, provenance = load_native_prefix(directory)
    end = summary['t'] if end is None else end
    fuel = fuel_accounting(inputs, summary, rows, start, end)
    r = inputs['resolved']
    frames = []; pmin = np.inf; pmax = 0.; rate_max = 0.
    for f in iter_fields(directory, inputs, summary['steps']):
        if f['t'] > summary['t']:
            raise ValueError('snapshot exceeds committed time')
        if start <= f['t'] <= end:
            frames.append(dict(step=f['step'], time_s=f['t'],
                sha256=hashlib.sha256((directory/'fields'/f"step_{f['step']:09d}.npz").read_bytes()).hexdigest()))
            pmin = min(pmin, float(f['pressure'].min()))
            pmax = max(pmax, float(f['pressure'].max()))
            rate_max = max(rate_max, float(f['reaction_rate'].max()))
    durations = playback_durations([f['time_s'] for f in frames], seconds)
    pnorm = LogNorm(pmin/1e6, max(pmax, pmin*1.001)/1e6)
    rnorm = LogNorm(max(rate_max*1e-6, 1e-12), max(rate_max*1.001, 1e-11))
    cmaps = [plt.get_cmap(name).with_extremes(bad=plt.get_cmap(name)(0.), under=plt.get_cmap(name)(0.))
             for name in ('magma', 'inferno')]
    norms = [pnorm, rnorm]
    labels = ['Pressure [MPa], fixed log scale', 'Reaction rate [1/s], fixed log scale']
    selected = {f['step'] for f in frames}
    destination.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema_version=1, source=str(directory.resolve()), provenance=provenance,
        renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        status=summary['status'], committed_end_s=summary['t'], requested_window_s=[start, end],
        frames=frames, durations_ms=durations, playback_seconds=seconds, final_hold_ms=durations[-1],
        loop='once; endpoint held, no restart presented as physical recovery',
        pressure_range_Pa=[pmin, pmax], reaction_rate_range_per_s=[rnorm.vmin, rnorm.vmax],
        fuel_accounting=fuel, radial_settings=inputs['config']['model'].get('radial'),
        qualifications=[
            'Every saved snapshot in the window; zero-order hold, no temporal interpolation or detonation classifier.',
            'Color limits are fixed over time; tiny reaction rates below the displayed floor use the lowest color.',
            'Wrapped surfaces display the same 2D mean-radius fields, not a 3D simulation or radial wall pressure.',
            'Opposite stationary cameras expose both sides; +theta arrows indicate coordinates, not detected wave travel.',
            'Wrapped faces use area-averaged display cells; unwrapped fields retain the native mesh.',
            'End of saved run is not evidence of fuel exhaustion, complete extinction, or a detected extinction time.'])
    try:
        for wrapped, name in [(False, 'unwrapped.gif'), (True, 'wrapped.gif')]:
            fig = plt.figure(figsize=(12, 8.2 if wrapped else 6.4), dpi=85)
            fig.subplots_adjust(left=.065, right=.87, top=.83, bottom=.18 if wrapped else .30,
                                wspace=.25 if wrapped else .48, hspace=.25)
            header = fig.text(.5, .965, '', ha='center', va='top', fontsize=15, weight='bold')
            fig.text(.5, .91, 'Pressure pulses are not proof of detonation: compare pressure AND reaction.', ha='center', fontsize=10)
            footer = fig.text(.5, .065, '', ha='center', fontsize=10)
            fig.text(.5, .022, 'Fresh mixture supplied throughout | saved snapshots, slowed physical-time playback | final frame held', ha='center', fontsize=9)
            axes = []; artists = []; pictures = []
            if wrapped:
                for k in range(4):
                    ax = fig.add_subplot(2, 2, k+1, projection='3d')
                    ax.view_init(elev=20, azim=-65 if k % 2 == 0 else 115)
                    radius = r['r_mean']*1000
                    ax.set(xlim=(-radius, radius), ylim=(-radius, radius), zlim=(0, r['length']*1000),
                        xlabel='X [mm]', ylabel='Y [mm]', zlabel='Axial z [mm]',
                        title=('Pressure' if k < 2 else 'Reaction rate') + (' | front' if k % 2 == 0 else ' | opposite side'))
                    ax.set_box_aspect((2*radius, 2*radius, r['length']*1000))
                    ax.tick_params(labelsize=7)
                    # Stationary coordinate arrow and seam; never claims a tracked wave direction.
                    angle = np.linspace(0, .65, 24)
                    ax.plot(radius*np.cos(angle), radius*np.sin(angle), np.full(len(angle), -2.), color='teal', lw=2)
                    ax.quiver(radius*np.cos(.65), radius*np.sin(.65), -2., -np.sin(.65), np.cos(.65), 0, length=5, color='teal')
                    ax.plot([radius, radius], [0, 0], [0, r['length']*1000], '--', color='cyan', lw=.8)
                    axes.append(ax)
                fig.text(.065, .12, 'Same 2D fields on mean-radius cylinder; cyan seam = 0/360 deg; teal arrow = +theta. Display faces averaged.', fontsize=9)
                for k in range(2):
                    cbax = fig.add_axes([.91, .58 if k == 0 else .22, .016, .22])
                    fig.colorbar(plt.cm.ScalarMappable(norm=norms[k], cmap=cmaps[k]), cax=cbax, label=labels[k])
            else:
                for k in range(2):
                    ax = fig.add_subplot(1, 2, k+1)
                    artist = ax.imshow(np.ones((r['ny'], r['nx'])), origin='lower',
                        extent=(0, 360, 0, r['length']*1000), aspect='auto', interpolation='nearest',
                        norm=norms[k], cmap=cmaps[k])
                    ax.set(xlabel='Azimuth theta [deg]  (+theta to the right)', ylabel='Axial z [mm]' if k == 0 else '',
                        title='Pressure' if k == 0 else 'Reaction rate', xticks=[0, 90, 180, 270, 360])
                    ax.text(.5, -.16, '0 and 360 deg join | injector at z=0', transform=ax.transAxes, ha='center', fontsize=9)
                    fig.colorbar(artist, ax=ax, fraction=.04, pad=.03, label=labels[k])
                    axes.append(ax); artists.append(artist)
            try:
                for index, f in enumerate(iter_fields(directory, inputs, summary['steps'], selected_steps=selected)):
                    values = [f['pressure']/1e6, f['reaction_rate']]
                    header.set_text(f"{'Wrapped' if wrapped else 'Unwrapped'} reduced 2D | t = {f['t']*1e6:.3f} us | saved frame {index+1}/{len(frames)}")
                    endpoint = index == len(frames)-1
                    footer.set_text(('END OF SAVED WINDOW — not a fuel-exhaustion stop.\n' if endpoint else '') +
                        f"Peak reaction: {float(f['reaction_rate'].max()):.3g} /s; at z={(r['probe_index']+.5)*r['dy']*1000:.3f} mm: {float(f['reaction_rate'][:,r['probe_index']].max()):.3g} /s")
                    if wrapped:
                        for artist in artists:
                            artist.remove()
                        artists = []
                        for k, ax in enumerate(axes):
                            xe, ze, field = surface_blocks(values[k//2])
                            theta, zz = np.meshgrid(xe*r['dx']/r['r_mean'], ze*r['dy']*1000, indexing='ij')
                            artists.append(ax.plot_surface(radius*np.cos(theta), radius*np.sin(theta), zz,
                                facecolors=cmaps[k//2](norms[k//2](np.ma.masked_less_equal(field, 0))),
                                rstride=1, cstride=1, shade=False, linewidth=0, antialiased=False))
                    else:
                        for artist, value in zip(artists, values):
                            artist.set_data(np.ma.masked_less_equal(value.T, 0))
                    fig.canvas.draw()
                    rgb = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
                    pictures.append(Image.fromarray(rgb).quantize(colors=256))
                    if index in (0, len(frames)//2, len(frames)-1):
                        # PNG previews permit QA without relying on a viewer's GIF clock.
                        Image.fromarray(rgb).save(destination/f'{Path(name).stem}_{index:03d}.png')
                pictures[0].save(destination/name, save_all=True, append_images=pictures[1:],
                    duration=durations, disposal=2, optimize=False)
                # No loop extension: play once and hold. Check actual encoded timing/count.
                with Image.open(destination/name) as gif:
                    encoded = []
                    for index in range(gif.n_frames):
                        gif.seek(index); encoded.append(gif.info['duration'])
                    if gif.n_frames != len(frames) or encoded != durations:
                        raise ValueError('GIF encoding changed frame count or time intervals')
                manifest[name] = dict(sha256=hashlib.sha256((destination/name).read_bytes()).hexdigest(), frames=len(pictures))
            finally:
                plt.close(fig)
                for picture in pictures:
                    picture.close()
        (destination/'manifest.json').write_text(json.dumps(manifest, default=_json_default, indent=2, allow_nan=False)+'\n')
        (destination/'COMPLETE').write_text('Two saved-data GIFs verified; no physical validation claim.\n')
    except Exception:
        (destination/'INCOMPLETE').write_text('Rendering failed; do not use partial GIFs as a complete product.\n')
        raise
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='new directory outside native run')
    parser.add_argument('--start-us', type=float, default=0.)
    parser.add_argument('--end-us', type=float)
    parser.add_argument('--seconds', type=float, default=14., help='playback time before final hold')
    args = parser.parse_args(argv)
    render_gifs(args.run, args.out, args.start_us*1e-6,
        None if args.end_us is None else args.end_us*1e-6, args.seconds)
    print(args.out)


if __name__ == '__main__':
    main()
