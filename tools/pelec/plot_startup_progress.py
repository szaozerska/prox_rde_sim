"""Show native pressure, heat release, and reactants versus azimuth and time."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm


def plot(run,output):
    run=Path(run);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with np.load(run/'preview.npz') as d:data={k:d[k] for k in d.files}
    times=data['time_s'];theta=data['theta_rad']*180/np.pi;z=data['z_m']
    if len(times)<2 or not np.all(np.diff(times)>0):raise ValueError('Need increasing native snapshot times')
    band=(z>=.001)&(z<=.010)
    if not band.any():raise ValueError('Missing injector-region samples')
    pressure=data['pressure_Pa'][:,:,band].mean(axis=2)*1e-6
    heat=np.maximum(data['heat_release_W_m3'][:,:,band],0).mean(axis=2)
    methane=data['methane_Y'][:,:,band].mean(axis=2)
    if not all(np.isfinite(a).all() for a in (pressure,heat,methane)):
        raise ValueError('Nonfinite or missing native pressure/heat-release/reactant fields')
    fig,axes=plt.subplots(1,3,figsize=(12,5.4),sharey=True,layout='constrained')
    hmax=max(1.,float(heat.max()))
    descriptions=[(pressure,LogNorm(.1,max(1.,float(pressure.max()))),'inferno','Pressure [MPa]'),
        (np.maximum(heat,hmax*1e-6),LogNorm(hmax*1e-6,hmax),'magma','Positive chemical heat release [W/m³]'),
        (methane,None,'viridis','Methane mass fraction')]
    for ax,(a,norm,cmap,label) in zip(axes,descriptions):
        image=ax.pcolormesh(theta,times*1e6,a,shading='nearest',norm=norm,cmap=cmap)
        ax.set(xlabel='Azimuth [degrees]',xlim=(0,360),ylim=(times[0]*1e6,times[-1]*1e6),title=label)
        fig.colorbar(image,ax=ax,orientation='horizontal',pad=.12)
    axes[0].set_ylabel('Physical time [µs]')
    fig.suptitle('Native annular history | axial mean over z = 1–10 mm\nDiagonal bands indicate motion; matching heat release is necessary evidence of reacting propagation.',fontsize=12)
    fig.savefig(output/'azimuth_time.png',dpi=150);plt.close(fig)
    summary={'physical_time_range_s':[float(times[0]),float(times[-1])],
        'native_frames':len(times),'axial_band_m':[.001,.010],
        'maximum_mean_pressure_Pa':float(pressure.max()*1e6),'maximum_mean_positive_heat_release_W_m3':hmax,
        'scope':'Native sampled fields; no prescribed rotation, temporal interpolation, or automatic detonation certification.'}
    (output/'azimuth_time.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('output');a=p.parse_args();print(plot(a.run,a.output))
