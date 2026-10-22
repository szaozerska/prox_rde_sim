"""Verify native MOL shock convergence, Cartesian rotations and CPU/GPU equivalence."""
import argparse
import json
from pathlib import Path
import numpy as np
from analyze_sod import load_fields,exact_sod,FIELDS
from validation import native_log_errors


def case(path,record):
    plots=sorted(path.glob('plt[0-9]*'))
    if len(plots)<2:raise ValueError('Initial/final native shock fields required')
    t0,before,dx,lo=load_fields(plots[0],FIELDS+('rho_E',))
    t,after,dx1,lo1=load_fields(plots[-1],FIELDS+('rho_E',))
    axis=record['axis'];n=record['nx'];velocity=('x_velocity','y_velocity','z_velocity')[axis]
    shape=[8,8,8];shape[axis]=n
    if after['density'].shape!=tuple(shape):raise ValueError('Incorrect rotated shock grid')
    if not np.array_equal(dx,dx1) or not np.array_equal(lo,lo1):raise ValueError('Mesh changed')
    if not all(np.isfinite(v).all() for data in (before,after) for v in data.values()):raise ValueError('Nonfinite native shock fields')
    profile={name:np.moveaxis(values,axis,0).mean(axis=(1,2)) for name,values in after.items()}
    x=lo[axis]+(np.arange(n)+.5)*dx[axis];truth=exact_sod(x,t)
    errors={name:float(np.mean(abs(profile[source]-truth[target]))) for name,source,target in
            [('density','density','density'),('pressure','pressure','pressure'),('velocity',velocity,'x_velocity')]}
    cell=float(np.prod(dx));area=float(np.prod([dx[d]*shape[d] for d in range(3) if d!=axis]))
    budgets={name:abs(float(after[field].sum()/before[field].sum()-1)) for name,field in [('mass','density'),('energy','rho_E')]}
    momentum=float(np.sum(after['density']*after[velocity])*cell)
    impulse_error=abs(momentum-.9*area*t)/(.9*area*t)
    transverse=max(float(np.max(abs(after[name]))) for name in FIELDS[3:] if name!=velocity)
    uniform=max(float(np.max(np.ptp(np.moveaxis(values,axis,0),axis=(1,2))))/max(float(np.max(abs(values))),1e-30) for values in after.values())
    checks=dict(completed=record['completion_passed'],mol_selected=record['hydro_method']=='mol',
        no_solver_errors=not native_log_errors((path/'solver.log').read_text()),
        time=abs(t0)<1e-14 and abs(t-.2)<1e-13,isotropic=bool(np.allclose(dx,1/n,rtol=0,atol=1e-14)),
        positive=all(bool((after[name]>0).all()) for name in ('density','pressure','Temp')),
        budgets=max(budgets.values())<1e-11,momentum_impulse=impulse_error<1e-10,
        transverse_motion=transverse<1e-12,transverse_uniformity=uniform<1e-12)
    reduced=dict(x=x,density=profile['density'],pressure=profile['pressure'],velocity=profile[velocity],
                 exact_density=truth['density'],exact_pressure=truth['pressure'],exact_velocity=truth['x_velocity'])
    np.savez_compressed(path/'mol_profiles.npz',**reduced)
    return dict(passed=all(checks.values()),checks=checks,mean_absolute_error=errors,
                budgets=budgets,momentum_impulse_relative_error=impulse_error,
                transverse_motion=transverse,transverse_nonuniformity=uniform,
                wall_seconds=record['wall_seconds']),reduced


def compare(directory):
    manifest=json.loads((directory/'result.json').read_text());reports={};profiles={};keys={}
    for record in manifest['runs']:
        name=record['name'];key=(record['backend'],record['axis'],record['nx'],record['dt'])
        if key in keys:raise ValueError('Duplicate native shock control')
        keys[key]=name;reports[name],profiles[name]=case(directory/name,record)
    levels=[keys['gpu',0,n,dt] for n,dt in ((64,.001),(128,.0005),(256,.00025))]
    base=keys['gpu',0,128,.0005]
    errors={name:[reports[c]['mean_absolute_error'][name] for c in levels] for name in ('density','pressure','velocity')}
    comparisons={}
    for label,key in [('cpu',('cpu',0,128,.0005)),('halfdt',('gpu',0,128,.00025)),('y',('gpu',1,128,.0005)),('z',('gpu',2,128,.0005))]:
        other=profiles[keys[key]];reference=profiles[base]
        comparisons[label]={name:dict(relative_max=float(max(abs(other[name]-reference[name])))/max(float(max(abs(reference[name]))),1e-30),
            mean_absolute=float(np.mean(abs(other[name]-reference[name])))) for name in errors}
    checks=dict(individual_controls=all(r['passed'] for r in reports.values()),
        three_grid_errors_decrease=all(e[2]<e[1]<e[0] for e in errors.values()),fine_errors=all(e[2]<.02 for e in errors.values()),
        cpu_gpu_equivalence=all(v['relative_max']<1e-10 for v in comparisons['cpu'].values()),
        rotated_axis_equivalence=all(v['relative_max']<1e-10 for label in ('y','z') for v in comparisons[label].values()),
        timestep_below_spatial_error=all(comparisons['halfdt'][name]['mean_absolute']<.1*errors[name][1] for name in errors))
    return dict(passed=all(checks.values()),checks=checks,cases=reports,grid_mean_absolute_errors=errors,comparisons=comparisons,
        criteria='Same cold-control criteria as G1a: decreasing three-grid errors, fine MAE <.02, CPU/GPU and axis relative differences <1e-10, timestep difference <10% spatial error; no smooth-order claim across shocks',
        scope='Native MOL Cartesian shock controls; EB dynamic flux/correction, AMR and reactive propagation remain separate'),profiles,levels


def plot(report,profiles,levels,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    for ax,name in zip(axes.flat,('density','pressure','velocity')):
        for label,n in zip(levels,(64,128,256)):
            d=profiles[label];ax.plot(d['x'],d[name],label=f'{n} cells')
        ax.plot(d['x'],d['exact_'+name],'k--',label='Exact Sod')
        ax.set(xlabel='Coordinate along shock normal',ylabel=name);ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    for name,errors in report['grid_mean_absolute_errors'].items():axes[1,1].loglog([64,128,256],errors,'o-',label=name)
    axes[1,1].set(xlabel='Axial cells',ylabel='Mean absolute error',xticks=[64,128,256],xticklabels=['64','128','256'])
    axes[1,1].xaxis.set_minor_locator(matplotlib.ticker.NullLocator());axes[1,1].legend(fontsize=8);axes[1,1].grid(alpha=.2)
    fig.suptitle('Native PeleC MOL shock verification — numerical control, not an RDE result')
    fig.savefig(output,dpi=150)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
    report,profiles,levels=compare(a.directory)
    (a.directory/'mol_shock_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    plot(report,profiles,levels,a.directory/'mol_shock_convergence.png')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2));raise SystemExit(0 if report['passed'] else 1)
