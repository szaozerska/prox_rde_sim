"""Replay analyzed native planar-wave snapshots; no solver or cloud calls."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def read_inputs(run, reference):
    case = json.loads((run / 'case.json').read_text())
    report = json.loads((run / 'wave_checks.json').read_text())
    result = json.loads((run / 'result.json').read_text())
    ref = json.loads((reference / 'reference.json').read_text())
    with np.load(run / 'wave_profiles.npz') as archive:
        data = {key: archive[key] for key in archive.files}
    with np.load(reference / 'znd.npz') as archive:
        znd = {key: archive[key] for key in archive.files}
    times = data['time_s']
    if len(times) < 2 or not np.all(np.isfinite(times)) or not np.all(np.diff(times) > 0):
        raise ValueError('Need at least two finite, increasing snapshot times')
    history = report['history']
    if len(history) != len(times) or not np.allclose(
        times, [row['time_s'] for row in history], rtol=0, atol=1e-15
    ):
        raise ValueError('Analysis history does not match snapshot times')
    front = np.array([row['shock_locations_m'][1] for row in history], dtype=float)
    if not np.all(np.isfinite(front)):
        raise ValueError('Pressure front is missing in one or more frames')
    for key in ('x_m', 'pressure_Pa', 'temperature_K', 'heat_fraction'):
        if data[key].shape != (len(times), case['nx']) or not np.isfinite(data[key]).all():
            raise ValueError(f'Unexpected shape or nonfinite field: {key}')
    expected_x = (np.arange(case['nx']) + .5) * case['dx_m']
    if not np.allclose(data['x_m'], expected_x, rtol=1e-12, atol=1e-15):
        raise ValueError('Unsupported moving or nonuniform grid')
    if not np.isclose(case['CJ_speed_mps'], ref['CJ']['CJ_speed_mps'], rtol=1e-12):
        raise ValueError('Case/reference speed mismatch')
    return case, report, result, ref, data, znd, front


def save_movie(fig, update, count, output, name):
    frames = []
    for index in range(count):
        update(index)
        fig.canvas.draw()
        frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert('RGB'))
    durations = [250] * count
    durations[0] = durations[-1] = 1000
    frames[0].save(output / f'{name}.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2, optimize=False)
    frames[-1].save(output / f'{name}_final.png')
    plt.close(fig)
    with Image.open(output / f'{name}.gif') as movie:
        if movie.n_frames != count:
            raise ValueError('GIF frame count differs from native snapshots')
        for index, duration in enumerate(durations):
            movie.seek(index)
            if movie.info['duration'] != duration:
                raise ValueError('GIF playback timing changed during encoding')
    return durations


def animate(run, reference, output):
    case, report, result, ref, data, znd, front = read_inputs(run, reference)
    output.mkdir(parents=True, exist_ok=False)
    times = data['time_s']
    x = data['x_m'][0] * 1e3
    speed = ref['CJ']['CJ_speed_mps']
    cj_front = (case['shock_initial_m'] + speed * times) * 1e3
    pressure = data['pressure_Pa'] * 1e-6
    temperature = data['temperature_K']
    plim = (0, 1.08 * max(pressure.max(), znd['pressure_Pa'].max() * 1e-6))
    tlim = (250, 1.05 * max(temperature.max(), znd['temperature_K'].max()))
    status = 'Propagation check: ' + ('PASS' if report['short_propagation_checks_passed'] else 'FAIL')
    title = f'PeleC planar-wave diagnostic | {case["dx_m"] * 1e6:g} micrometre cells'
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11})
    fig = plt.figure(figsize=(10, 6.6), dpi=110)
    grid = fig.add_gridspec(3, 2, width_ratios=(1, .025), height_ratios=(1, 1, 2),
                           left=.10, right=.90, bottom=.15, top=.84, hspace=.36, wspace=.035)
    strips, markers = [], []
    for row, (field, limits, cmap, label) in enumerate((
        (pressure, plim, 'magma', 'Pressure [MPa]'),
        (temperature, tlim, 'inferno', 'Temperature [K]')
    )):
        ax = fig.add_subplot(grid[row, 0])
        artist = ax.imshow(field[0][None, :], extent=(0, case['length_m'] * 1e3, 0, 1),
                           aspect='auto', interpolation='nearest', cmap=cmap,
                           vmin=limits[0], vmax=limits[1])
        ax.set(yticks=[], title=label)
        ax.tick_params(labelbottom=False)
        markers.append(ax.axvline(cj_front[0], color='white', linestyle='--', lw=1.7))
        strips.append(artist)
        fig.colorbar(artist, cax=fig.add_subplot(grid[row, 1]))
    ax = fig.add_subplot(grid[2, 0])
    line, = ax.plot(x, pressure[0], color='#187b93', drawstyle='steps-mid', label='Native CFD pressure')
    expected = ax.axvline(cj_front[0], color='black', linestyle='--', label='CJ reference front')
    ax.set(xlim=(0, case['length_m'] * 1e3), ylim=plim, xlabel='Position [mm]', ylabel='Pressure [MPa]')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(alpha=.2)
    fig.suptitle(title, y=.98, fontsize=14)
    clock = fig.text(.5, .91, '', ha='center', fontsize=12)
    fig.text(.5, .065, 'Wave moves right. White/black dashed line: independent CJ speed.', ha='center')
    fig.text(.5, .025, f'{status} | Transverse-mean strips; height is display-only. Not a rotating engine.',
             ha='center', fontsize=9, color='#8b2525')

    def update_motion(i):
        strips[0].set_data(pressure[i][None, :])
        strips[1].set_data(temperature[i][None, :])
        line.set_ydata(pressure[i])
        for marker in markers + [expected]:
            marker.set_xdata([cj_front[i], cj_front[i]])
        clock.set_text(f'Physical time: {times[i] * 1e6:.4f} microseconds | saved frame {i + 1}/{len(times)}')

    durations = save_movie(fig, update_motion, len(times), output, 'wave_propagation')

    fig, axes = plt.subplots(3, 1, figsize=(9, 7.7), dpi=110, sharex=True)
    fig.subplots_adjust(left=.12, right=.97, bottom=.14, top=.84, hspace=.22)
    lines = []
    for ax, key, scale, label, limits in zip(
        axes, ('pressure_Pa', 'temperature_K', 'heat_fraction'), (1e-6, 1, 1),
        ('Pressure [MPa]', 'Temperature [K]', 'Heat fraction'),
        (plim, tlim, (min(-.05, data['heat_fraction'].min() - .02),
                      max(1.05, data['heat_fraction'].max() + .02, znd['heat_fraction'].max() + .02)))
    ):
        line, = ax.plot([], [], color='#187b93', drawstyle='steps-mid', label='Native CFD')
        lines.append((line, key, scale))
        ax.plot(-znd['distance_m'] * 1e6, znd[key] * scale, 'k--', lw=1.5, label='Independent ZND reference')
        # ZND describes the region behind the shock; fresh gas is ahead.
        fresh = {'pressure_Pa': ref['CJ']['pressure_Pa'], 'temperature_K': 300, 'heat_fraction': 0}[key]
        ax.plot([0, 70], [fresh * scale] * 2, 'k--', lw=1.5)
        ax.axvline(0, color='.6', lw=.8)
        ax.set(xlim=(-150, 70), ylim=limits, ylabel=label)
        ax.grid(alpha=.2)
    axes[0].legend(loc='upper right', fontsize=9)
    axes[-1].set_xlabel('Position relative to measured pressure front [micrometres]')
    fig.suptitle('Reaction-zone close-up | follows the native pressure front', y=.98, fontsize=13)
    clock = fig.text(.5, .915, '', ha='center', fontsize=12)
    fig.text(.5, .065, 'Left = behind the shock; right = fresh mixture. Fixed axes throughout.', ha='center')
    fig.text(.5, .027, f'{status} | Compare the native reaction layer with the independent reference.',
             ha='center', fontsize=9, color='#8b2525')

    def update_structure(i):
        for line, key, scale in lines:
            line.set_data((data['x_m'][i] - front[i]) * 1e6, data[key][i] * scale)
        clock.set_text(f'Physical time: {times[i] * 1e6:.4f} microseconds | saved frame {i + 1}/{len(times)}')

    save_movie(fig, update_structure, len(times), output, 'reaction_structure')
    sources = [run / name for name in ('wave_profiles.npz', 'wave_checks.json', 'case.json', 'result.json')]
    sources += [reference / name for name in ('reference.json', 'znd.npz')]
    manifest = dict(
        scope='Replay of analyzed planar native 3D thin-grid snapshots; not an engine validation',
        native_run=str(run.resolve()), reference=str(reference.resolve()),
        sources={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        frames=len(times), physical_times_s=times.tolist(), playback_frame_duration_ms=durations,
        temporal_interpolation=False, spatial_display='Native cell values; nearest-neighbour strips and step profiles',
        strip_height='Display only; transverse-mean data',
        reference_speed_mps=speed, measured_pressure_front_m=front.tolist(),
        short_propagation_checks_passed=report['short_propagation_checks_passed'],
        full_G2b_passed=report['full_G2b_passed'], native_wall_seconds=result['wall_seconds'],
        artifacts=['wave_propagation.gif', 'reaction_structure.gif',
                   'wave_propagation_final.png', 'reaction_structure_final.png'],
    )
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print(f'Saved {len(times)} native frames in each GIF: {output}')
    print(status + '; rendering does not change validation status.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path, help='Analyzed wave directory')
    parser.add_argument('reference', type=Path, help='Independent reference directory')
    parser.add_argument('output', type=Path, help='New animation directory (refuses overwrite)')
    args = parser.parse_args()
    animate(args.run, args.reference, args.output)


if __name__ == '__main__':
    main()
