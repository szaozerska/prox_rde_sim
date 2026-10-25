"""Read native fields, export SI, and compare the declared control with Cantera.

No native progress/heat-release variable is invented. This does not accept engine
runs or claim propagation, mixing, or high-temperature mechanism validity.
"""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path
import numpy as np
from control import CASE, log_errors, plot_time


def collect(directory):
    status = json.loads((directory/'status.json').read_text())
    archive = directory/'native.tar.gz'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != status['artifact_sha256']:
        raise ValueError('Native archive checksum mismatch')
    target = directory/'native'
    if target.exists():
        raise FileExistsError('Use a fresh extraction directory; native evidence is immutable')
    with tarfile.open(archive) as tar:
        for item in tar.getmembers():
            if item.issym() or item.islnk() or not (item.isfile() or item.isdir()):
                raise ValueError('Unexpected native archive member')
            if not (target/item.name).resolve().is_relative_to(target.resolve()):
                raise ValueError('Archive member escapes extraction directory')
        tar.extractall(target, filter='data')
    return target/'controls'


def check_rows(rows, case, execution, solver_log):
    """Explicit tolerances apply to this short numerical gate only."""
    a, b = rows[0], rows[-1]
    reacting = case['reacting']
    return {
        'native_completion': execution['completion_passed'] and not log_errors(solver_log),
        'time_window': abs(a['time_s']) < 1e-18 and abs(b['time_s']-case['final_time_s']) < 1e-16,
        'monotonic_times': all(y['time_s'] > x['time_s'] for x,y in zip(rows,rows[1:])),
        'active_chemistry': ('Initializing CVODE:' in solver_log and b['species_change'] > 1e-6) if reacting else b['species_change'] < 1e-12,
        'thermo_scope': all(300 <= r['temperature_K'] <= 2500 and r['pressure_Pa'] > 0 for r in rows),
        'temperature_reference': max(r['temperature_relative_error'] for r in rows) < 5e-5,
        'pressure_reference': max(r['pressure_relative_error'] for r in rows) < 5e-5,
        'species_reference': max(r['species_max_absolute_error'] for r in rows) < 2e-6,
        'density_conservation': max(r['density_relative_drift'] for r in rows) < 1e-11,
        'energy_conservation': max(r['energy_relative_drift'] for r in rows) < 1e-10,
        'elements': max(r['element_absolute_drift'] for r in rows) < 1e-9,
        'species_sum': max(r['species_sum_error'] for r in rows) < 1e-10,
        'species_nonnegative': min(r['minimum_Y'] for r in rows) >= -1e-12,
        'uniformity': max(r['nonuniformity'] for r in rows) < 1e-10,
    }


def analyze(root, output):
    import cantera as ct
    import yt
    yt.set_log_level(40)
    output.mkdir(parents=True,exist_ok=False)
    lock = json.loads(Path(__file__).with_name('source_lock.json').read_text())
    build = json.loads((root/'build/manifest.json').read_text())
    for key in ('pelec_commit','submodules','mechanism_sha256','dimension','mechanism'):
        if build[key] != lock[key]: raise ValueError('Build/source lock mismatch: '+key)
    for name,digest in lock['mechanism_sha256'].items():
        if hashlib.sha256((root/'mechanism'/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Mechanism checksum mismatch')
    mechanism=root/'mechanism/mechanism.yaml'
    source=ct.Solution(str(mechanism))
    names=source.species_names
    # Confirm actual generated species ordering instead of assuming YAML order.
    header=(root/'mechanism/mechanism.H').read_text()
    for i,name in enumerate(names):
        import re
        match=re.search(r'^#define '+re.escape(name.replace('(','_').replace(')',''))+r'_ID\s+(\d+)\b',header,re.M)
        if match is None or int(match.group(1))!=i: raise ValueError('Native species order mismatch: '+name)
    source.TPX=CASE['temperature_K'],CASE['pressure_Pa'],{'CH4':CASE['phi'],'O2':2}
    initial_y=source.Y.copy();initial_elements=np.array([source.elemental_mass_fraction(e) for e in source.element_names])
    u_scale=max(abs(source.int_energy_mass),source.cv_mass*source.T)
    results={};fields={}
    for name in ('reacting','half_step','frozen'):
        run=root/name
        case=json.loads((run/'case.json').read_text())
        if any(case[k]!=v for k,v in CASE.items()):raise ValueError('Unexpected control case')
        execution=json.loads((run/'execution.json').read_text())
        gas=ct.Solution(str(mechanism));gas.TPX=CASE['temperature_K'],CASE['pressure_Pa'],{'CH4':CASE['phi'],'O2':2}
        reactor=ct.IdealGasReactor(gas,clone=True)
        network=ct.ReactorNet([reactor]);network.rtol=1e-12;network.atol=1e-23
        rows=[];snapshots=[];first=None
        plots=sorted(run.glob('plt[0-9]*'),key=plot_time)
        if len(plots)<2:raise ValueError('Missing initial/final native fields')
        for plot in plots:
            t=plot_time(plot);ds=yt.load(str(plot))
            if ds.dimensionality!=2 or tuple(ds.domain_dimensions[:2])!=(8,8):raise ValueError('Unexpected mesh')
            grid=ds.covering_grid(0,ds.domain_left_edge,ds.domain_dimensions)
            def field(key):
                a=np.asarray(grid['boxlib',key].d,dtype=float)
                if not np.isfinite(a).all():raise ValueError('Nonfinite native '+key)
                return a[:,:,0]
            T=field('Temp');p=field('pressure')*.1;rho=field('density')*1000;energy=field('rho_E')*.1
            Y=np.stack([field('Y('+n+')') for n in names],axis=-1)
            if first is None:first=(rho.copy(),energy.copy())
            if case['reacting'] and t>0:network.advance(t)
            truth=reactor.phase
            y=Y.mean(axis=(0,1));source.TDY=float(T.mean()),float(rho.mean()),y
            elements=np.array([source.elemental_mass_fraction(e) for e in source.element_names])
            rows.append(dict(time_s=t,temperature_K=float(T.mean()),pressure_Pa=float(p.mean()),
                reference_temperature_K=truth.T,reference_pressure_Pa=truth.P,
                temperature_relative_error=float(np.max(abs(T/truth.T-1))),
                pressure_relative_error=float(np.max(abs(p/truth.P-1))),
                species_max_absolute_error=float(np.max(abs(Y-truth.Y))),
                species_change=float(np.max(abs(Y-initial_y))),
                species_sum_error=float(np.max(abs(Y.sum(axis=-1)-1))),minimum_Y=float(Y.min()),
                element_absolute_drift=float(np.max(abs(elements-initial_elements))),
                density_relative_drift=float(np.max(abs(rho/first[0]-1))),
                energy_relative_drift=float(np.max(abs(energy-first[1]))/max(abs(first[1].mean()),first[0].mean()*u_scale)),
                nonuniformity=float(max(np.ptp(T)/T.mean(),np.ptp(p)/p.mean(),np.ptp(rho)/rho.mean(),np.max(np.ptp(Y,axis=(0,1)))))))
            snapshots.append((t,T,p,rho,energy,Y))
        checks=check_rows(rows,case,execution,(run/'solver.log').read_text())
        results[name]=dict(checks=checks,passed=all(checks.values()),rows=rows,execution=execution)
        fields[name]=dict(time_s=np.array([s[0] for s in snapshots]),temperature_K=np.stack([s[1] for s in snapshots]),
            pressure_Pa=np.stack([s[2] for s in snapshots]),density_kg_m3=np.stack([s[3] for s in snapshots]),
            energy_J_m3=np.stack([s[4] for s in snapshots]),mass_fractions=np.stack([s[5] for s in snapshots]))
        np.savez_compressed(output/(name+'_fields_si.npz'),**fields[name],species=np.array(names),
            x_m=(np.arange(8)+.5)*CASE['extent_m'][0]/8,
            y_m=(np.arange(8)+.5)*CASE['extent_m'][1]/8)
    step_error=float(np.max(abs(fields['reacting']['mass_fractions'][-1]-fields['half_step']['mass_fractions'][-1])))
    report=dict(backend='pelec',dimension=2,mechanism='grimech30',species=names,case=CASE,
        status='passed' if all(v['passed'] for v in results.values()) and step_error<2e-6 else 'failed',
        timestep_species_max_absolute_difference=step_error,timestep_tolerance=2e-6,runs=results,
        units=dict(time='s',pressure='Pa',density='kg/m3',energy_density='J/m3',temperature='K'),
        source_lock=lock,build=build,reference_cantera_version=ct.__version__,
        adapter_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
        limitations=['Uniform closed-reactor control on a 2D mesh; no shock or engine',
                     'No validation above 2500 K; no artificial inversion-bound extension',
                     'No measured injector mixing, gap dynamics or sustained-wave prediction',
                     'Old progress-based report format is not used for multispecies fields'])
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,2,figsize=(10,3.6))
    for name,result in results.items():
        rows=result['rows'];t=np.array([r['time_s'] for r in rows])*1e6
        ax[0].plot(t,[r['temperature_K']-CASE['temperature_K'] for r in rows],'o-',label=name)
        if name=='reacting':ax[0].plot(t,[r['reference_temperature_K']-CASE['temperature_K'] for r in rows],'k--',label='Cantera reference')
        ax[1].plot(t,[r['species_change'] for r in rows],'o-',label=name)
    ax[0].set_ylabel('Temperature change (K)');ax[1].set_ylabel('Maximum species mass-fraction change')
    for a in ax:a.set_xlabel('Time (microseconds)');a.legend();a.grid(alpha=.3)
    fig.suptitle('Native PeleC 2D methane integration check — NOT an RDE run')
    fig.tight_layout();fig.savefig(output/'reactor_check.png',dpi=150);plt.close(fig)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--collected',action='store_true',help='Read already extracted native/controls')
    args=parser.parse_args()
    root=args.run/'native/controls' if args.collected else collect(args.run)
    result=analyze(root,args.output)
    print(json.dumps({'status':result['status'],'checks':{k:v['checks'] for k,v in result['runs'].items()}},indent=2))
    raise SystemExit(0 if result['status']=='passed' else 1)

if __name__=='__main__':main()
