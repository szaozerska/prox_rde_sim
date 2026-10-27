"""Replay archived long planar controls without launching a solver."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from animate_wave import save_movie


def animate(run, output):
    config_path = run / 'case_case.json'
    profile_path = run / 'wave_profiles.npz'
    case = json.loads(config_path.read_text())['wave_case']
    with np.load(profile_path) as archive:
        data = {key: archive[key] for key in archive.files}
    times = data['time_s']
    if len(times) < 2 or not np.isfinite(times).all() or not np.all(np.diff(times) > 0):
        raise ValueError('Need finite, increasing native snapshot times')
    expected_x = (np.arange(case['nx']) + .5) * case['dx_m']
    for name in ('x_m', 'pressure_Pa', 'temperature_K'):
        if data[name].shape != (len(times), case['nx']) or not np.isfinite(data[name]).all():
            raise ValueError(f'Invalid native field: {name}')
    if not np.allclose(data['x_m'], expected_x, rtol=1e-12, atol=1e-15):
        raise ValueError('Grid does not match archived case')
    if not np.isclose(times[-1], case['final_time_s'], rtol=1e-10, atol=1e-15):
        raise ValueError('Missing final native snapshot')
    output.mkdir(parents=True, exist_ok=False)
    x = expected_x * 1e3
    pressure = data['pressure_Pa'] * 1e-6
    temperature = data['temperature_K']
    cj_front = (case['shock_initial_m'] + case['CJ_speed_mps'] * times) * 1e3
    # Fixed crop includes the initial front and its subsequent trajectory.
    xmin = max(0., cj_front[0] - 2.)
    xmax = min(case['length_m'] * 1e3, cj_front[-1] + 3.)
    plim = (0., pressure.max() * 1.08)
    plt.rcParams.update({'font.size': 10})
    fig = plt.figure(figsize=(10, 6.6), dpi=110)
    grid = fig.add_gridspec(3, 2, width_ratios=(1, .025), height_ratios=(1, 1, 2),
                           left=.10, right=.91, bottom=.17, top=.82, hspace=.40, wspace=.04)
    strips, markers = [], []
    for row, field, limits, cmap, label in (
        (0, pressure, plim, 'magma', 'Pressure [MPa]'),
        (1, temperature, (250., temperature.max() * 1.05), 'inferno', 'Temperature [K]'),
    ):
        ax = fig.add_subplot(grid[row, 0])
        artist = ax.imshow(field[0][None, :], extent=(0, case['length_m'] * 1e3, 0, 1),
                           aspect='auto', interpolation='nearest', cmap=cmap,
                           vmin=limits[0], vmax=limits[1])
        ax.set(xlim=(xmin, xmax), yticks=[], title=label)
        ax.tick_params(labelbottom=False)
        strips.append(artist)
        markers.append(ax.axvline(cj_front[0], color='white', ls='--'))
        fig.colorbar(artist, cax=fig.add_subplot(grid[row, 1]))
    ax = fig.add_subplot(grid[2, 0])
    line, = ax.plot(x, pressure[0], color='#187b93', drawstyle='steps-mid', label='Native CFD pressure')
    markers.append(ax.axvline(cj_front[0], color='black', ls='--', label='CJ-speed reference trajectory'))
    ax.set(xlim=(xmin, xmax), ylim=plim, xlabel='Position [mm]', ylabel='Pressure [MPa]')
    ax.grid(alpha=.2)
    ax.legend(fontsize=9, loc='upper right')
    fig.suptitle(f'PeleC planar propagation | {case["dx_m"] * 1e6:g} micrometre cells', y=.98, fontsize=14)
    clock = fig.text(.5, .91, '', ha='center', fontsize=12)
    fig.text(.5, .09, f'{len(times)} native snapshots; no temporal interpolation. Fixed spatial crop; wave moves right.', ha='center', fontsize=9)
    fig.text(.5, .055, 'Strip height is display-only. This is a planar control, not an annular engine.', ha='center', fontsize=9)
    fig.text(.5, .02, 'Late speed approaches CJ; reaction-layer structure remains unresolved in this calculation.',
             ha='center', fontsize=9, color='#8b2525')

    def update(i):
        strips[0].set_data(pressure[i][None, :])
        strips[1].set_data(temperature[i][None, :])
        line.set_ydata(pressure[i])
        for marker in markers:
            marker.set_xdata([cj_front[i], cj_front[i]])
        clock.set_text(f'Physical time: {times[i] * 1e6:.3f} microseconds | frame {i + 1}/{len(times)}')

    durations = save_movie(fig, update, len(times), output, 'long_planar_propagation')
    manifest = {
        'scope': 'Replay of saved native PeleC planar control; no new solver run or annular result',
        'sources': {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (config_path, profile_path)},
        'physical_times_s': times.tolist(), 'playback_frame_duration_ms': durations,
        'temporal_interpolation': False, 'spatial_crop_mm': [xmin, xmax],
        'CJ_reference_speed_mps': case['CJ_speed_mps'],
        'limitations': ['Transverse-mean fields; strip height is display-only',
                        'Not a demonstration of sustained annular detonation'],
    }
    (output / 'animation.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    animate(args.run, args.output)
