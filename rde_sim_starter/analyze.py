"""Numerical reductions only: no file loading, rendering, or solver execution.

The old automatic mode/roll-stability report is retired. It mixed heuristic
classification with unsupported torque claims. Front tracking, native flux
budgets and short-run reporting are the next increment, not validated here.
"""
import numpy as np


def weighted_mean(values, weights):
    """Weighted scalar/field mean along time axis; empty windows are errors."""
    values, weights = np.asarray(values, dtype=float), np.asarray(weights, dtype=float)
    if values.ndim < 1 or weights.ndim != 1 or values.shape[0] != weights.size or weights.size == 0:
        raise ValueError("values and nonempty time weights must have matching lengths")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)) or np.any(weights < 0) or weights.sum() <= 0:
        raise ValueError("finite values and nonnegative weights with positive total required")
    return np.tensordot(weights / weights.sum(), values, axes=(0, 0))


def window_weights(times, dt, start, end):
    """Overlap of saved step intervals (t-dt,t] with the requested window.

    Step-end sample values are a rectangle-rule approximation. This does not
    turn a short transient record into a converged statistical mean.
    """
    times, dt = np.asarray(times, dtype=float), np.asarray(dt, dtype=float)
    if times.ndim != 1 or times.size == 0 or dt.shape != times.shape:
        raise ValueError("matching nonempty 1D time and dt arrays required")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(dt)) or np.any(dt <= 0) or np.any(np.diff(times) <= 0):
        raise ValueError("finite increasing times and positive finite dt required")
    if not np.isfinite(start) or not np.isfinite(end) or end <= start:
        raise ValueError("window must be finite with end > start")
    return np.maximum(0.0, np.minimum(times, end) - np.maximum(times-dt, start))


def exit_contribution(rho, axial_velocity, pressure, area, ambient_pressure):
    """Planar exit momentum/pressure contribution [N], not whole-engine thrust."""
    r, uz, p, a = np.broadcast_arrays(rho, axial_velocity, pressure, area)
    if not all(np.all(np.isfinite(v)) for v in (r,uz,p,a)) or not np.isfinite(ambient_pressure):
        raise ValueError("finite exit states required")
    if np.any(r <= 0) or np.any(p <= 0) or np.any(a <= 0) or ambient_pressure < 0:
        raise ValueError("positive density/pressure/area and nonnegative ambient pressure required")
    return float(np.sum((r*uz*uz+p-ambient_pressure)*a))


def directional_spectrum(pressure, times):
    """Inherited FFT reduction, without inferring a mode from its strongest peak.

    Pressure is [time, circumferential sample]. The data are linearly resampled
    to uniform time and Hann-windowed. Returned power is unnormalized; this is
    not a camera spectrum or a fine-frequency measurement of a short record.
    With NumPy's convention +x travel gives f > 0, k < 0.
    """
    pressure, times = np.asarray(pressure,dtype=float), np.asarray(times,dtype=float)
    if pressure.ndim != 2 or times.ndim != 1 or pressure.shape[0] != times.size or times.size < 4 or pressure.shape[1] < 2:
        raise ValueError("at least four times and two circumferential samples required")
    if not np.all(np.isfinite(pressure)) or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
        raise ValueError("finite signals and strictly increasing times required")
    uniform_times = np.linspace(times[0],times[-1],times.size)
    uniform = np.array([np.interp(uniform_times,times,pressure[:,i]) for i in range(pressure.shape[1])]).T
    signal = (uniform-uniform.mean())*np.hanning(times.size)[:,None]
    return dict(times=uniform_times, pressure=uniform,
                frequency=np.fft.fftfreq(times.size,uniform_times[1]-uniform_times[0]),
                wave_number=np.fft.fftfreq(pressure.shape[1],1.0/pressure.shape[1]),
                power=np.abs(np.fft.fft2(signal))**2)


def conservation_budget(current, initial, boundary_integral, source_integral, depth, mean_radius):
    """Storage minus actual RK-weighted net numerical transport/source.

    Solver inputs are per radial depth. Boundary order: left/right/bottom/top,
    each with a positive-coordinate normal, so net influx is L-R+B-T.
    Angular momentum uses the reduced model's constant mean-radius approximation.
    The angular residual is not an engine-torque estimate.
    """
    current, initial = np.asarray(current), np.asarray(initial)
    boundary, source = np.asarray(boundary_integral), np.asarray(source_integral)
    if current.shape != (5,) or initial.shape != (5,) or boundary.shape != (4, 5) or source.shape != (5,):
        raise ValueError('unexpected conserved-budget shape')
    if not all(np.all(np.isfinite(v)) for v in (current, initial, boundary, source)):
        raise ValueError('nonfinite budget input')
    if not np.isfinite(depth) or not np.isfinite(mean_radius) or min(depth, mean_radius) <= 0:
        raise ValueError('positive finite depth and mean radius required')
    storage = (current - initial) * depth
    net = (boundary[0] - boundary[1] + boundary[2] - boundary[3] + source) * depth
    residual = storage - net
    return dict(inventory=current * depth, storage=storage, net_influx_and_source=net,
                boundary_integral=boundary * depth, source_integral=source * depth,
                residual=residual, angular_inventory=current[1] * depth * mean_radius,
                angular_storage=storage[1] * mean_radius, angular_net=net[1] * mean_radius,
                angular_residual=residual[1] * mean_radius)
