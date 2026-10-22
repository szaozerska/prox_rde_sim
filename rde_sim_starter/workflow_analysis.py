"""Saved-data spectral, reference and cross-run reductions; no solver/render imports."""
import numpy as np
from window_report import unavailable


def pressure_spectrum(times, pressure, start, end):
    """One-sided Hann PSD on a conservative uniform grid, in Pa^2/Hz.

    Linear resampling cannot recover unresolved frequencies. Grid spacing is at
    least the largest native sample gap that overlaps the requested window.
    Peaks are pressure oscillations, never automatic wave counts/detonation labels.
    """
    t, p = np.asarray(times, float), np.asarray(pressure, float)
    if (t.ndim != 1 or t.size < 2 or p.shape != t.shape or
            not np.isfinite(t).all() or not np.isfinite(p).all() or np.any(np.diff(t) <= 0)):
        raise ValueError('finite matching pressure and increasing time samples required')
    if not np.isfinite([start, end]).all() or not t[0] <= start < end <= t[-1]:
        raise ValueError('spectrum window must be entirely within saved samples')
    intervals = (t[:-1] < end) & (t[1:] > start)
    max_gap = float(np.max(np.diff(t)[intervals]))
    n = int(np.floor((end - start) / max_gap)) + 1
    if n < 16:
        return unavailable('fewer than 16 conservative uniform samples in this window')
    grid = np.linspace(start, end, n)
    dt = float(grid[1] - grid[0])
    signal = np.interp(grid, t, p)
    trend = np.polyval(np.polyfit(grid - start, signal, 1), grid - start)
    signal -= trend
    if np.max(np.abs(signal)) <= 128 * np.finfo(float).eps * max(1., float(np.max(np.abs(p)))):
        return unavailable('no resolved pressure fluctuation after linear detrending')
    window = np.hanning(n)
    density = np.abs(np.fft.rfft(signal * window))**2 * dt / np.sum(window**2)
    density[1:-1 if n % 2 == 0 else None] *= 2
    frequency = np.fft.rfftfreq(n, dt)
    peak = int(np.argmax(density[1:])) + 1
    cycles = float(frequency[peak] * (end-start))
    return dict(available=True, frequency_Hz=frequency, density_Pa2_per_Hz=density,
        peak_pressure_frequency_Hz=float(frequency[peak]), peak_cycles_in_window=cycles,
        frequency_bin_Hz=float(frequency[1]), nyquist_Hz=float(frequency[-1]),
        sampling_nyquist_Hz=.5/dt, native_max_gap_s=max_gap, uniform_sample_count=n,
        window_s=[start, end], window_function='Hann; linear detrend; one-sided PSD',
        qualification=('fewer than three cycles: peak is poorly constrained; ' if cycles < 3 else '') +
            'pressure oscillation only; interpolation cannot undo aliasing; harmonics need front/reaction inspection')


def pressure_spectrogram(times, pressure, start, end, segment_s):
    if not np.isfinite(segment_s) or segment_s <= 0 or segment_s > end-start:
        raise ValueError('spectrogram segment must be positive and fit within the window')
    # Avoid an accidental unbounded list when a nonsensical segment is requested.
    count = int(np.floor((end-start-segment_s)/(segment_s/2) + 1e-10)) + 1
    if count > 2000:
        raise ValueError('spectrogram would exceed 2000 segments; increase segment duration')
    spectra = []
    for i in range(count):
        a = start + i * segment_s / 2
        b = min(end, a + segment_s)
        spectra.append(pressure_spectrum(times, pressure, a, b))
    return dict(segment_s=segment_s, overlap_fraction=.5, segments=spectra,
                qualification='each segment retains its own sampling limit and frequency bins')


def run937_reference(config, resolved, report):
    """Explicit nominal identity guard, never a measured-thrust validation."""
    reasons = []
    nominal_geometry = dict(r_outer_mm=38.1, r_inner_mm=33.1, length_mm=76.2, area_ratio=.110)
    nominal_operating = dict(phi=1.176, mdot_target_gps=268.65, p_back_kPa=100.2,
        mass_flux=240.21, p_plenum_kPa=1350., T_plenum_K=300.)
    for section, expected in [('geometry', nominal_geometry), ('operating_point', nominal_operating)]:
        for key, value in expected.items():
            actual = config.get(section, {}).get(key)
            if actual is None or not np.isfinite(actual) or not np.isclose(actual, value, rtol=1e-8, atol=1e-12):
                reasons.append(f'{section}.{key} differs from nominal Run 937 reduction')
    if report.get('run_mode') == 'development_benchmark':
        reasons.append('development benchmark is not an experimental comparison')
    if reasons:
        return dict(available=False, reason='; '.join(reasons), case='Mundt Run 937')
    reference = config.get('experimental_reference', {})
    z = np.asarray(reference.get('pressure_stations_mm', []), float) * .001
    pressure = np.asarray(reference.get('mean_pressures_kPa', []), float) * 1000
    measured_z = np.array([0,22.2,34.9,47.6,60.3,73.0])*.001
    measured_p = np.array([368.5,323.3,292.3,281.1,255.4,238.4])*1000
    # Prevent accidentally relabelling edited or another experiment's values.
    if (z.shape != measured_z.shape or pressure.shape != measured_p.shape or
            not np.allclose(z, measured_z, rtol=1e-8, atol=1e-12) or
            not np.allclose(pressure, measured_p, rtol=1e-8, atol=1e-8)):
        return unavailable('saved reference values do not match the audited Mundt Run 937 table')
    stations = report['pressure_stations']
    if not stations['available']:
        return unavailable('saved station means unavailable')
    model_z = np.asarray(stations['stations_m'])
    if model_z.size < 2 or np.any(np.diff(model_z) <= 0) or z.min() < model_z[0] or z.max() > model_z[-1]:
        return unavailable('saved station range/order cannot support the reference locations without extrapolation')
    prediction = np.interp(z, model_z, stations['mean_Pa'])
    return dict(available=True, case='Mundt Run 937', source='Mundt2023.pdf: Tables 2-1, 2-2, 3-2 and 4-1; audited in docs/verification/mundt_model_audit.md',
        stations_m=z, experimental_mean_Pa=pressure, model_window_mean_Pa=prediction,
        discrepancy_percent=100*(prediction-pressure)/pressure,
        qualification='transient reduced-model vs experimental long-window mean; nominal case identity only, not validation',
        measured_thrust=unavailable('Mundt Run 937 has no measured thrust target'),
        measured_torque=unavailable('no matched target-engine torque measurement'))


def roll_response(times, impulses, inertia, omega0=0.):
    """Constant-inertia illustrative response to interval engine torque impulses.

    Impulses are N m s, times bound each interval. Angular acceleration is
    constant within each interval. Returned angle is relative to the window start.
    """
    t, j = np.asarray(times, float), np.asarray(impulses, float)
    if (t.ndim != 1 or j.shape != (t.size-1,) or t.size < 2 or
        not np.isfinite(t).all() or not np.isfinite(j).all() or np.any(np.diff(t) <= 0) or
        not np.isfinite([inertia, omega0]).all() or inertia <= 0):
        raise ValueError('positive finite inertia and finite consecutive torque intervals required')
    omega = np.r_[omega0, omega0+np.cumsum(j)/inertia]
    angle = np.r_[0., np.cumsum(.5*(omega[:-1]+omega[1:])*np.diff(t))]
    return dict(times_s=t, angular_velocity_rad_s=omega, angle_rad=angle, inertia_kg_m2=inertia,
                qualification='constant inertia; no damping/control/structural model; not a stability verdict')
