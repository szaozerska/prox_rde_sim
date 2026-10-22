"""Independent finite-state, budget and optional exact-Sod checks of native fields."""
import argparse
import json
from pathlib import Path
import numpy as np
FIELDS = ('density', 'Temp', 'pressure', 'x_velocity', 'y_velocity', 'z_velocity')


def load_fields(plot):
    import yt
    yt.set_log_level(40)
    ds = yt.load(str(plot))
    if ds.index.max_level != 0:
        raise ValueError('This small uniform-grid control analyzer does not flatten AMR')
    grid = ds.covering_grid(0, ds.domain_left_edge, ds.domain_dimensions)
    # Read native fields, never generic yt thermodynamic reconstructions.
    values = {name: np.asarray(grid['boxlib', name]) for name in FIELDS}
    dx = np.asarray(ds.domain_width)/ds.domain_dimensions
    return float(ds.current_time), values, dx, np.asarray(ds.domain_left_edge)


def exact_sod(x, time):
    """Classical gamma=1.4 Sod solution; star values also used by inherited tests."""
    gamma = 1.4
    pstar, ustar = .30313017805064685, .9274526200489499
    astar = np.sqrt(gamma) * pstar**((gamma-1)/(2*gamma))
    xi = (x-.5)/time
    rho = np.where(xi < ustar, pstar**(1/gamma),
                   .125*((pstar/.1)+(gamma-1)/(gamma+1))/
                   ((gamma-1)/(gamma+1)*(pstar/.1)+1))
    pressure = np.full_like(x, pstar)
    velocity = np.full_like(x, ustar)
    left = xi <= -np.sqrt(gamma)
    right = xi >= 1.7521557320301782
    rho[left], pressure[left], velocity[left] = 1., 1., 0.
    rho[right], pressure[right], velocity[right] = .125, .1, 0.
    fan = (xi > -np.sqrt(gamma)) & (xi < ustar-astar)
    sound = 2/(gamma+1)*(np.sqrt(gamma)-(gamma-1)*xi[fan]/2)
    rho[fan] = (sound/np.sqrt(gamma))**(2/(gamma-1))
    pressure[fan] = (sound/np.sqrt(gamma))**(2*gamma/(gamma-1))
    velocity[fan] = 2/(gamma+1)*(np.sqrt(gamma)+xi[fan])
    return {'density': rho, 'pressure': pressure, 'x_velocity': velocity}


def analyze(run, expected_time, reference=False):
    paths = sorted(run.glob('plt[0-9]*'))
    if len(paths) < 2:
        raise ValueError('Need initial and final native plotfiles')
    first, last = load_fields(paths[0]), load_fields(paths[-1])
    t0, initial, dx, lo = first
    time, final, final_dx, final_lo = last
    checks = {'initial_time': abs(t0) < 1e-14,
              'final_time': abs(time-expected_time) < 1e-13,
              'same_mesh': np.array_equal(dx, final_dx) and np.array_equal(lo, final_lo),
              'finite_fields': all(np.isfinite(a).all() for a in final.values()),
              'positive_density_pressure_temperature': all((final[n] > 0).all()
                                            for n in ('density','pressure','Temp'))}
    def integrals(values):
        rho, p = values['density'], values['pressure']
        ke = .5*rho*sum(values[n]**2 for n in FIELDS[3:])
        return {'mass': float(rho.sum()*np.prod(dx)),
                'energy': float((p/.4+ke).sum()*np.prod(dx)),
                'xmomentum': float((rho*values['x_velocity']).sum()*np.prod(dx))}
    before, after = integrals(initial), integrals(final)
    drift = {n: abs(after[n]-before[n])/abs(before[n]) for n in ('mass','energy')}
    transverse = max(float(np.max(np.abs(final[n]))) for n in ('y_velocity','z_velocity'))
    uniformity = max(float(np.max(np.ptp(a,axis=(1,2))))/max(float(np.max(np.abs(a))),1e-30)
                     for a in final.values())
    checks.update(mass_conservation=drift['mass'] < 1e-11,
                  energy_conservation=drift['energy'] < 1e-11,
                  transverse_velocity=transverse < 1e-12,
                  transverse_uniformity=uniformity < 1e-11)
    expected_momentum = before['xmomentum'] + .9*np.prod(dx[1:]*np.array(initial['density'].shape[1:]))*time
    checks['wall_pressure_impulse'] = abs(after['xmomentum']-expected_momentum) < 1e-10
    report = dict(time=time, shape=list(final['density'].shape), checks=checks,
                  initial_integrals=before, final_integrals=after, relative_drift=drift,
                  max_transverse_velocity=transverse, relative_transverse_nonuniformity=uniformity,
                  native_minmax={n:[float(a.min()),float(a.max())] for n,a in final.items()})
    if reference:
        if not np.isclose(time,.2,rtol=0,atol=1e-13):
            raise ValueError('Sod accuracy thresholds are specified at t=0.2 only')
        x = lo[0]+(np.arange(final['density'].shape[0])+.5)*dx[0]
        exact = exact_sod(x,time)
        profiles = {n: final[n].mean(axis=(1,2)) for n in exact}
        report['mean_absolute_error'] = {n:float(np.mean(abs(profiles[n]-exact[n]))) for n in exact}
        i = int(np.argmin(abs(x-.75)))
        shock = float(x[np.where(profiles['density']>.2)[0].max()])
        report['shock_location'] = shock
        checks.update(star_pressure=abs(profiles['pressure'][i]/.30313017805064685-1)<.02,
                      star_velocity=abs(profiles['x_velocity'][i]/.9274526200489499-1)<.02,
                      shock_location=abs(shock-.850431146406)<2*dx[0])
        np.savez(run/'sod_profiles.npz',x=x,**profiles,**{'exact_'+n:a for n,a in exact.items()})
    report['checks'] = {name: bool(value) for name, value in checks.items()}
    report['passed'] = all(report['checks'].values())
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--time',type=float,required=True)
    parser.add_argument('--reference',action='store_true')
    args=parser.parse_args()
    report=analyze(args.run,args.time,args.reference)
    (args.run/'field_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)
