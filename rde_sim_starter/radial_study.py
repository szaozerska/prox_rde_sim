"""Read-only, reproducible comparison for the declared radial-wall experiment.

No binary detonation classifier: pressure fronts and nearby heat release alone
are insufficient. Save absolute magnitudes, contrast, separation and budgets for
inspection; do not hide a vanishing reaction signal behind normalized plots.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from coupling import thermal_metrics
from contracts import iter_fields
from window_report import load_native_prefix, reduce_window, _json_default
from workflow import compare_saved_runs


def ring_metrics(pressure, rate, dx):
    p=np.asarray(pressure,dtype=float);w=np.asarray(rate,dtype=float)
    if p.ndim!=1 or w.shape!=p.shape or p.size<2 or not np.isfinite(p).all() or not np.isfinite(w).all() or np.any(p<=0) or np.any(w<0) or not np.isfinite(dx) or dx<=0:
        raise ValueError('finite positive pressure, nonnegative rate and positive spacing required')
    jump=np.abs(np.roll(p,-1)-p);front=int(np.argmax(jump));maximum=float(w.max())
    # Shock location lies on a face, reaction data on cell centers. Periodic distance.
    distance=None
    if maximum>0 and float(jump.max())>0:
        active=np.flatnonzero(w>=.5*maximum)
        delta=np.abs(active-(front+.5));distance=float(np.min(np.minimum(delta,p.size-delta))*dx)
    return dict(pressure_max_Pa=float(p.max()),pressure_mean_Pa=float(p.mean()),
        pressure_contrast=float((p.max()-p.min())/p.mean()),
        largest_neighbor_pressure_jump_Pa=float(jump.max()),reaction_rate_max_per_s=maximum,
        front_to_half_peak_reaction_m=distance,
        qualification='strongest pressure face to nearest half-peak reaction cell; no minimum signal threshold or detonation classification')


def collect(directory):
    inputs,summary,rows,provenance=load_native_prefix(directory)
    r=inputs['resolved'];records=[];pressure=[];reaction=[];last=None
    c=inputs['calibration'];fill=inputs['config']['initialization'].get('fill_height_mm')
    fill=None if fill is None else fill*1e-3
    indices=[min(int(z/r['dy']),r['ny']-1) for z in [.001,.0035]]
    for frame in iter_fields(directory,inputs,summary['steps']):
        if frame['t']>summary['t']:raise ValueError('uncommitted field')
        item=dict(t_s=frame['t'],step=frame['step'],
            global_pressure_max_Pa=float(frame['pressure'].max()),
            global_reaction_rate_max_per_s=float(frame['reaction_rate'].max()),
            rings=[ring_metrics(frame['pressure'][:,j],frame['reaction_rate'][:,j],r['dx']) for j in indices])
        item['thermal_diagnostics'],_=thermal_metrics(frame['pressure'],frame['density'],frame['reaction_rate'],
            c['q'],r['dx'],r['dy'],r['gap'],2*c['p1'],fill)
        if 'inner_pressure' in frame:
            split=(frame['outer_pressure']-frame['inner_pressure'])/frame['pressure']
            item['wall_split_over_mean_max']=float(split.max())
        records.append(item);pressure.append(frame['pressure'][:,indices[0]].copy());reaction.append(frame['reaction_rate'][:,indices[0]].copy());last=frame
    if not records:raise ValueError('no saved fields')
    windows={}
    for lo,hi in [(0.,summary['t']),(100e-6,180e-6)]:
        if lo<hi<=summary['t']:
            windows[f'{lo*1e6:g}_{hi*1e6:g}_us']=reduce_window(inputs,summary,rows,lo,hi)
    return dict(directory=str(Path(directory).resolve()),inputs=inputs,summary=summary,
        provenance=provenance,thermal_diagnostic_pressure_threshold_Pa=2*c['p1'],
        thermal_operator_sha256=hashlib.sha256(Path(__file__).with_name('coupling.py').read_bytes()).hexdigest(),
        thermal_qualification='spatial overlap and axial heat-release distribution, not detonation classification; native integrals remain authoritative',
        actual_ring_z_m=[(j+.5)*r['dy'] for j in indices],
        frame_metrics=records,windows=windows),np.asarray(pressure),np.asarray(reaction),last


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',nargs='+',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();out=Path(args.out).resolve()
    for path in args.runs:
        root=Path(path).resolve()
        if out==root or root in out.parents:raise ValueError('report must be outside native runs')
    if out.exists():raise ValueError('use a new report directory')
    data=[collect(p) for p in args.runs]
    common_end=min(d[0]['summary']['t'] for d in data)
    comparison=compare_saved_runs(args.runs,0.,common_end)
    out.mkdir(parents=True)
    result=dict(analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        interpretation='matched exploratory closure comparison; no calibrated wall parameters or automatic sustained-wave claim',
        runs=[d[0] for d in data],comparison=comparison)
    (out/'metrics.json').write_text(json.dumps(result,default=_json_default,indent=2,allow_nan=False)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    fig,ax=plt.subplots(3,len(data),figsize=(5*len(data),10),squeeze=False,constrained_layout=True)
    pmax=max(float(d[1].max()) for d in data)/1e3;wmax=max(float(d[2].max()) for d in data)
    pmin=min(float(d[1].min()) for d in data)/1e3
    for col,(metrics,p,w,last) in enumerate(data):
        times=np.array([m['t_s'] for m in metrics['frame_metrics']])*1e6
        x=(np.arange(p.shape[1])+.5)*metrics['inputs']['resolved']['dx']*1000
        for row,values,label,kw in [(0,p/1000,'Pressure [kPa, log]',dict(norm=LogNorm(pmin,max(pmax,pmin*(1+1e-6))))),
            (1,np.maximum(w,1e-6),'Reaction rate [1/s]',dict(norm=LogNorm(1e-6,max(wmax,1e-5))))]:
            im=ax[row,col].pcolormesh(x,times,values,shading='nearest',**kw)
            fig.colorbar(im,ax=ax[row,col],label=label);ax[row,col].set(xlabel='Circumference [mm]',ylabel='Time [us]')
        name=Path(metrics['directory']).name;ax[0,col].set_title(name+'\nz='+f"{metrics['actual_ring_z_m'][0]*1e3:.3f} mm")
        ax[2,col].plot(times,[f['rings'][0]['pressure_contrast'] for f in metrics['frame_metrics']],label='pressure contrast')
        ax[2,col].set(xlabel='Time [us]',ylabel='(pmax-pmin)/mean',ylim=(0,None));ax[2,col].grid(alpha=.3)
    fig.suptitle('Saved run comparison; inspect input differences; common scales; reaction display floor 1e-6/s')
    fig.savefig(out/'comparison.png',dpi=140);plt.close(fig)
    # Actual saved wall pressures vs mean at final time (never radial interpolation of a 3D solution).
    fig,axes=plt.subplots(1,len(data),figsize=(5*len(data),3.5),squeeze=False,constrained_layout=True)
    for ax,(metrics,p,w,last) in zip(axes[0],data):
        r=metrics['inputs']['resolved'];x=(np.arange(r['nx'])+.5)*r['dx']*1000;j=r['probe_index']
        for key,label in [('pressure','mean'),('inner_pressure','inner reconstructed'),('outer_pressure','outer reconstructed')]:
            if key in last:ax.plot(x,last[key][:,j]/1000,label=label)
        ax.set(title=Path(metrics['directory']).name,xlabel='Circumference [mm]',ylabel='Pressure [kPa]');ax.legend()
    fig.savefig(out/'final_wall_pressures.png',dpi=140);plt.close(fig)
    fig,axes=plt.subplots(3,len(data),figsize=(5*len(data),10),squeeze=False,constrained_layout=True)
    final_pmax=max(float(d[3]['pressure'].max()) for d in data)/1e3
    final_wmax=max(float(d[3]['reaction_rate'].max()) for d in data)
    for col,(metrics,p,w,last) in enumerate(data):
        r=metrics['inputs']['resolved'];extent=[0,r['width']*1000,0,r['length']*1000]
        for row,key in enumerate(['pressure','reaction_rate','progress']):
            values=last[key]/1000 if row==0 else np.maximum(last[key],1e-6) if row==1 else last[key]
            kw=dict(vmin=0,vmax=final_pmax) if row==0 else dict(norm=LogNorm(1e-6,max(final_wmax,1e-5))) if row==1 else dict(vmin=0,vmax=1)
            im=axes[row,col].imshow(values.T,origin='lower',extent=extent,aspect='auto',**kw)
            fig.colorbar(im,ax=axes[row,col],label=['Pressure [kPa]','Reaction rate [1/s]','Reaction progress'][row])
            axes[row,col].set(xlabel='Circumference [mm]',ylabel='Axial height [mm]')
        axes[0,col].set_title(Path(metrics['directory']).name+f"; {last['t']*1e6:.3f} us")
    fig.suptitle('Full-height final saved states; shared color scales; reaction display floor 1e-6/s')
    fig.savefig(out/'final_fields.png',dpi=140);plt.close(fig)
    print(out)


if __name__=='__main__':main()
