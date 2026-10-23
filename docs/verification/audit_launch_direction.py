"""Read-only launch audit of the existing 40 us prefix; no CFD or retuning.
Run from repo root with .venv/bin/python docs/verification/audit_launch_direction.py.
"""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'rde_sim_starter'))
from contracts import iter_fields
from window_report import load_native_prefix


def main():
    out = ROOT / 'docs/verification/launch_direction_audit'
    if out.exists():
        raise ValueError('refusing existing report')
    run = ROOT / 'rde_sim_starter/runs/directional_startup_40us'
    inputs, summary, history, provenance = load_native_prefix(run)
    r = inputs['resolved']
    frames = list(iter_fields(run, inputs, summary['steps']))
    initial = frames[0]
    assert initial['t'] == 0 and frames[-1]['t'] >= 40e-6 - 1e-13
    rho = initial['density'].astype(float)
    u = initial['u_theta'].astype(float)
    v = initial['u_z'].astype(float)
    volume = r['dx'] * r['dy'] * r['gap']
    momentum = np.array([(rho*u).sum(), (rho*v).sum()]) * volume
    # Independent float32 field reconstruction against native double inventories.
    np.testing.assert_allclose(momentum, history[0]['inventory'][1:3], rtol=2e-7, atol=1e-12)
    assert np.all(u >= 0) and np.all(v == 0)
    metrics_file = ROOT / 'docs/verification/directional_startup_comparison/metrics.json'
    prior = json.loads(metrics_file.read_text())
    records = prior['runs'][1]
    # Verify the comparison's field identities before reusing its peak extraction.
    for h in records['frame_hashes']:
        source = run / 'fields' / f"step_{h['step']:09d}.npz"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == h['sha256']
    rows = []
    for f in records['metrics']:
        if not any(abs(f['time_us'] - t) < 1e-8 for t in (10, 20, 30, 40)):
            continue
        peaks = f['rings'][0]['peaks']
        # Explicit windows from the already inspected space-time tracks, not a
        # generic wave tracker. Both tracks stay within these windows through 40 us.
        forward = max((p for p in peaks if 25 < p['x_mm'] < 100), key=lambda p:p['pressure_MPa'])
        backward = max((p for p in peaks if 180 < p['x_mm'] < 220), key=lambda p:p['pressure_MPa'])
        ref = inputs['calibration']['p1'] / 1e6
        rows.append(dict(time_us=f['time_us'], forward=forward, backward=backward,
                         pressure_ratio=forward['pressure_MPa']/backward['pressure_MPa'],
                         excess_over_initial_p1_ratio=(forward['pressure_MPa']-ref)/(backward['pressure_MPa']-ref)))
    out.mkdir()
    result = dict(provenance=provenance, native_status=summary['status'],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        comparison_sha256=hashlib.sha256(metrics_file.read_bytes()).hexdigest(),
        initial=dict(max_u_theta_mps=float(u.max()), min_u_theta_mps=float(u.min()),
            max_abs_u_z_mps=float(abs(v).max()),
            positive_theta_momentum_kg_mps=float((rho*np.maximum(u,0)).sum()*volume),
            negative_theta_momentum_kg_mps=float((rho*np.minimum(u,0)).sum()*volume),
            kinetic_energy_J=float((.5*rho*(u*u+v*v)).sum()*volume),
            max_pressure_MPa=float(initial['pressure'].max()/1e6)),
        ring_z_mm=records['metrics'][0]['rings'][0]['z_mm'],
        initial_p1_MPa=inputs['calibration']['p1']/1e6,
        peak_comparisons=rows,
        qualification='Peak ratios are not energy ratios, local shock jumps or proof of detonation. The overpressure reference is initial p1, not measured upstream pressure. Saved fields are float32. No new CFD.')
    (out/'metrics.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    x = (np.arange(r['nx'])+.5)*r['dx']
    x = ((x-r['formed_initialization']['shock_m']+r['width']/2)%r['width']-r['width']/2)*1e3
    order = np.argsort(x); x = x[order]
    z = (np.arange(r['ny'])+.5)*r['dy']*1e3
    fig, axes = plt.subplots(4, 1, figsize=(12, 10), layout='constrained', sharex=True)
    for ax, t in zip(axes, (0, 2, 10, 20)):
        f = min(frames, key=lambda f:abs(f['t']*1e6-t))
        assert abs(f['t']*1e6-t) < 1e-8
        im = ax.pcolormesh(x, z, f['pressure'][order,:].T/1e6,
                          norm=LogNorm(.1,22), cmap='inferno', shading='nearest')
        ix = np.where((x>-43)&(x<63))[0][::10]
        iz = np.where(z<19)[0][::4]
        xx, zz = np.meshgrid(x[ix], z[iz], indexing='ij')
        q = ax.quiver(xx, zz, f['u_theta'][order,:][np.ix_(ix,iz)],
                      f['u_z'][order,:][np.ix_(ix,iz)], color='cyan',
                      angles='xy', scale_units='xy', scale=160, width=.0025)
        ax.set(xlim=(-45,65), ylim=(0,20), ylabel='Axial z [mm]', aspect='equal',
               title=f't = {t} us | arrows: gas velocity; pressure color is not luminosity')
        if t == 0:
            ax.axvline(-30, color='white', linestyle=':', linewidth=1)
            ax.axvline(0, color='white', linestyle=':', linewidth=1)
            ax.text(-29, 15, 'Finite charge: -30 to 0 mm\nInitial flow is entirely +theta', color='white')
            ax.text(2, 4, 'Leading front →', color='white')
        ax.quiverkey(q, .87, .8, 1000, '1000 m/s', labelpos='N', color='cyan',
                     labelcolor='white', coordinates='axes')
    axes[-1].set_xlabel('Circumferential distance from INITIAL leading front [mm]; +theta →')
    fig.colorbar(im, ax=axes, label='Pressure [MPa]; fixed logarithmic scale', shrink=.7)
    fig.suptitle('Current formed startup: equal spatial scale on both axes; periodic seam moved out of view')
    fig.savefig(out/'launch_fields.png', dpi=150)
    plt.close(fig)
    print(json.dumps(result['initial'], indent=2)); print(out)


if __name__ == '__main__':
    main()
