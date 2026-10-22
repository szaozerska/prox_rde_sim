"""Compare native shock controls to exact data and to each other."""
import argparse
import json
from pathlib import Path
import numpy as np
from analyze_sod import analyze,load_fields


def compare(directory):
    records=json.loads((directory/'result.json').read_text())['runs']
    cases={}
    final={}
    for record in records:
        if record['case']!='Sod': continue
        name=record['name'];path=directory/name
        cases[name]=analyze(path,.2,reference=True)
        cases[name]['native_completion_passed']=record['completion_passed']
        final[name]=load_fields(sorted(path.glob('plt[0-9]*'))[-1])[1]
    levels=['gpu_Sod_n64_dt0.001','gpu_Sod_n128_dt0.0005','gpu_Sod_n256_dt0.00025']
    base='gpu_Sod_n128_dt0.0005';half='gpu_Sod_n128_dt0.00025';cpu='cpu_Sod_n128_dt0.0005'
    needed=levels+[half,cpu]
    if any(name not in cases for name in needed):
        raise ValueError('Incomplete shock set; preserve failure before comparing')
    errors={n:[cases[c]['mean_absolute_error'][n] for c in levels]
            for n in ('density','pressure','x_velocity')}
    checks={'individual_controls':all(c['passed'] and c['native_completion_passed'] for c in cases.values()),
            'three_grid_error_decreases':all(e[2]<e[1]<e[0] for e in errors.values()),
            'fine_mean_absolute_error':all(e[-1]<.02 for e in errors.values())}
    equivalence={n:float(np.max(abs(final[base][n]-final[cpu][n])))/max(float(np.max(abs(final[base][n]))),1e-30)
                 for n in final[base]}
    temporal={n:float(np.mean(abs(final[base][n]-final[half][n]))) for n in errors}
    checks['cpu_gpu_equivalence']=all(value<1e-10 for value in equivalence.values())
    checks['temporal_error_below_spatial']=all(temporal[n]<.1*errors[n][1] for n in errors)
    return {'passed':all(checks.values()),'checks':checks,'cases':cases,
            'grid_mean_absolute_errors':errors,'cpu_gpu_relative_max_error':equivalence,
            'timestep_mean_absolute_difference':temporal,
            'criteria':'Predeclared: cold CPU/GPU relative max <1e-10; all three grid errors decrease; fine MAE <.02; temporal difference <10% of same-grid exact error. Discontinuous shock: not a formal smooth second-order claim.'}


def plot(directory,report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    names=[('density','Density / left density'),('pressure','Pressure / left pressure'),('x_velocity','Velocity / sqrt(p_left/rho_left)')]
    for (name,label),ax in zip(names,axes.flat):
        for nx,dt in [(64,.001),(128,.0005),(256,.00025)]:
            data=np.load(directory/f'gpu_Sod_n{nx}_dt{dt:g}'/'sod_profiles.npz')
            ax.plot(data['x'],data[name],label=f'{nx} axial cells',linewidth=1)
        ax.plot(data['x'],data['exact_'+name],'k--',label='Exact Sod',linewidth=1)
        ax.set(xlabel='x / domain length',ylabel=label)
        ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8)
    for name,error in report['grid_mean_absolute_errors'].items():
        axes[1,1].loglog([64,128,256],error,'o-',label=name)
    axes[1,1].set(xlabel='Axial cells',ylabel='Mean absolute error',xticks=[64,128,256],xticklabels=['64','128','256'])
    axes[1,1].xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    axes[1,1].legend(fontsize=8);axes[1,1].grid(alpha=.2)
    fig.suptitle('PeleC GPU: upstream nonreacting Sod, normalized time 0.2\nVerification control — not methane or RDE validation')
    fig.savefig(output,dpi=160);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    report=compare(args.directory)
    (args.directory/'shock_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    plot(args.directory,report,args.directory/'shock_convergence.png')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
    raise SystemExit(0 if report['passed'] else 1)
