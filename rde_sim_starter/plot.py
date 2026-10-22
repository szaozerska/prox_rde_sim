"""Rendering from supplied/saved data only; never advances the solver.

CLIs render saved calibration, 1D experiments, or bounded engine-run directories.
Plots are diagnostics; pressure crossings alone are not detonation classification.
"""
import argparse
import json
from pathlib import Path


def plot_znd(profile, calibration, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    c = calibration
    fig, axes = plt.subplots(1,4,figsize=(14,3.4))
    try:
        xi = profile['progress']
        for ax,values,label in zip(axes[:3],
                [profile['mach'],profile['pressure']/1e6,profile['temperature']],
                ['Mach (shock frame)','Pressure [MPa]','Temperature [K]']):
            ax.plot(xi,values)
            ax.set_xlabel('Reaction progress')
            ax.set_ylabel(label)
            ax.grid(alpha=.3)
        axes[0].plot([0],[c['M_CJ']],'o')
        axes[1].plot([0],[c['p1']/1e6],'ko')
        axes[2].plot([0],[c['T1']],'ko')
        axes[3].plot(profile['distance']*1e3,xi)
        axes[3].axhline(.5,ls=':',c='k')
        axes[3].set_xlabel('Distance behind shock [mm]')
        axes[3].set_ylabel('Reaction progress')
        axes[3].grid(alpha=.3)
        fig.suptitle(f"One-step surrogate ZND: gamma={c['gamma']:.3f}, half-reaction length={c['L_half']*1e3:.2f} mm")
        fig.tight_layout()
        fig.savefig(destination,dpi=120)
    finally:
        plt.close(fig)


def plot_sod(x, primitive, destination):
    """A small field preview for the nonreacting baseline, supplied by the caller."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes = plt.subplots(1,3,figsize=(11,3.3))
    try:
        for ax,index,label in zip(axes,[0,1,3],['Density','Velocity','Pressure']):
            ax.plot(x,primitive[index,:,0])
            ax.set(xlabel='x (nondimensional)',ylabel=label)
            ax.grid(alpha=.3)
        fig.suptitle('Nonreacting Sod tube at nondimensional time 0.2')
        fig.tight_layout()
        fig.savefig(destination,dpi=120)
    finally:
        plt.close(fig)



def _pyplot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    return plt


def plot_tube(directory, destination):
    import numpy as np
    directory,destination=Path(directory),Path(destination)
    summary=json.loads((directory/'summary.json').read_text())
    with np.load(directory/'fields.npz',allow_pickle=False) as saved:
        x,t,W,h=(saved[key].copy() for key in ['x','times','primitive','history'])
    destination.mkdir(parents=True,exist_ok=False)
    plt=_pyplot()
    fig,axes=plt.subplots(2,2,figsize=(12,7),layout='constrained')
    try:
        for index in np.unique(np.round(np.linspace(0,len(t)-1,5)).astype(int)):
            label=f'{t[index]*1e6:.0f} µs'
            axes[0,0].plot(x*1e3,W[index,3]/1e6,label=label)
            axes[0,1].plot(x*1e3,W[index,4],label=label)
        axes[0,0].set(xlabel='Axial distance [mm]',ylabel='Pressure [MPa]',yscale='log')
        axes[0,1].set(xlabel='Axial distance [mm]',ylabel='Reaction progress',ylim=(-.02,1.02))
        axes[0,0].legend(ncol=2,fontsize=8)
        if h.size:
            axes[1,0].plot(h[:,0]*1e6,h[:,1]*1e3,label='Pressure front > 2p₁')
            axes[1,0].plot(h[:,0]*1e6,h[:,2]*1e3,label='50% reaction front')
            axes[1,1].plot(h[:,0]*1e6,(h[:,1]-h[:,2])*1e3)
        axes[1,0].set(xlabel='Time [µs]',ylabel='Front position [mm]')
        axes[1,0].legend(fontsize=8)
        axes[1,1].set(xlabel='Time [µs]',ylabel='Pressure-to-50% front distance [mm]')
        for ax in axes.flat:
            ax.grid(alpha=.2)
        speed=summary['speed_mps']
        label='not enough samples' if speed is None else f'{speed:.1f} m/s, {summary["speed_relative_error"]:+.2%} relative error against fitted CJ'
        fig.suptitle(f'1D one-step propagation: {summary["status"]} — {label}')
        fig.savefig(destination/'propagation.png',dpi=150)
    finally:
        plt.close(fig)
    return summary


def plot_run(directory, destination):
    import numpy as np
    from matplotlib.colors import LogNorm
    from analyze import load_saved_run, pressure_arrivals
    data=load_saved_run(directory)
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    inputs,summary,rows,fields=(data[key] for key in ['inputs','summary','history','fields'])
    r=inputs['resolved']; config=inputs['config']; calibration=inputs['calibration']
    mode=summary.get('run_mode','engine_intervals')
    benchmark=mode=='development_benchmark'
    mode_label='Development benchmark (not a sustaining-wave study)' if benchmark else 'Reduced annulus'
    t=np.array([row['t'] for row in rows]); ts=np.array([float(f['t']) for f in fields])
    x=(np.arange(r['nx'])+.5)*r['dx']*1e3
    z=(np.arange(r['ny'])+.5)*r['dy']*1e3
    pressure=np.stack([f['pressure'] for f in fields])/1e6
    progress=np.stack([f['progress'] for f in fields])
    rate_available=all('reaction_rate' in f for f in fields)
    rate=np.stack([f['reaction_rate'] for f in fields]) if rate_available else None
    low=float(pressure.min()); high=float(pressure.max())
    norm=LogNorm(max(low,1e-9),max(high,low*1.01))
    plt=_pyplot()
    chosen=np.unique(np.round(np.linspace(0,len(fields)-1,4)).astype(int))
    fig,axes=plt.subplots(2,len(chosen),figsize=(3.4*len(chosen)+1,6),squeeze=False,layout='constrained')
    try:
        for column,index in enumerate(chosen):
            extent=[0,r['width']*1e3,0,r['length']*1e3]
            im=axes[0,column].imshow(pressure[index].T,origin='lower',extent=extent,aspect='auto',norm=norm,cmap='magma')
            xi=axes[1,column].imshow(progress[index].T,origin='lower',extent=extent,aspect='auto',vmin=0,vmax=1,cmap='viridis')
            axes[0,column].set_title(f'{ts[index]*1e6:.2f} µs')
            for row in range(2):
                axes[row,column].set_xlabel('Circumferential distance [mm]')
                if column==0:
                    axes[row,column].set_ylabel('Axial distance [mm]')
        fig.colorbar(im,ax=axes[0,:].tolist(),label='Pressure [MPa], logarithmic')
        fig.colorbar(xi,ax=axes[1,:].tolist(),label='Reaction progress')
        fig.suptitle(f'{mode_label}: {summary["status"]}; pressure and reaction share the saved times')
        fig.savefig(destination/'fields.png',dpi=150)
    finally:
        plt.close(fig)

    probe=r['probe_index']
    fig,axes=plt.subplots(1,3,figsize=(13,5),sharex=True,sharey=True,layout='constrained')
    try:
        arrays=[pressure[:,:,probe],progress[:,:,probe],rate[:,:,probe] if rate_available else None]
        titles=['Pressure [MPa], log','Reaction progress','Reaction rate [1/s], log']
        for i,(ax,values,title) in enumerate(zip(axes,arrays,titles)):
            if values is None:
                ax.text(.5,.5,'Reaction rate was not saved',ha='center',transform=ax.transAxes)
            elif len(ts)<2 or (i==2 and not np.any(values>0)):
                ax.text(.5,.5,'Insufficient time samples' if len(ts)<2 else 'No active reaction',ha='center',transform=ax.transAxes)
            else:
                options=dict(cmap='viridis',vmin=0,vmax=1) if i==1 else dict(cmap='magma',norm=norm)
                if i==2:
                    positive=values[values>0]
                    options=dict(cmap='inferno',norm=LogNorm(max(float(positive.min()),float(positive.max())*1e-6),float(positive.max())*1.001))
                    values=np.ma.masked_less_equal(values,0.)
                image=ax.pcolormesh(x,ts*1e6,values,shading='nearest',**options)
                fig.colorbar(image,ax=ax)
            ax.set(title=title,xlabel='Circumferential distance [mm]')
        axes[0].set_ylabel('Time from startup [µs]')
        if len(ts)>1:
            axes[0].set_ylim(ts[0]*1e6,ts[-1]*1e6)  # do not extend nearest-sample bins outside saved time
        axes[0].set_xlim(0,r['width']*1e3)
        fig.suptitle(f'{mode_label}: saved rings at z={z[probe]:.3f} mm; field cadence is not native step cadence')
        fig.savefig(destination/'space_time.png',dpi=150)
    finally:
        plt.close(fig)

    fig,axes=plt.subplots(3,2,figsize=(13,10),layout='constrained')
    events=[]
    try:
        stations=np.array([row['pressure_stations'] for row in rows])/1e3
        for index,station in enumerate(r['pressure_stations']):
            axes[0,0].plot(t*1e6,stations[:,index],label=f'{station*1e3:g} mm')
        axes[0,0].set(xlabel='Time [µs]',ylabel='Circumferential mean pressure [kPa]')
        axes[0,0].legend(ncol=3,fontsize=7)
        average=summary['average']
        if average['available']:
            axes[0,1].plot(z,np.array(average['pressure_profile_Pa'])/1e3,label='Model: transient window')
        else:
            axes[0,1].text(.5,.5,'No averaging-window overlap',ha='center',transform=axes[0,1].transAxes)
        reference=config.get('experimental_reference',{})
        # Only overlay the engine references when their stations fit this geometry.
        zr=reference.get('pressure_stations_mm',[])
        from workflow_analysis import run937_reference
        station_means=dict(available=average['available'])
        if average['available']:
            station_means.update(stations_m=r['pressure_stations'],
                mean_Pa=np.interp(r['pressure_stations'],z*.001,average['pressure_profile_Pa']))
        comparison=run937_reference(config,r,dict(run_mode=mode,pressure_stations=station_means))
        if comparison['available']:
            axes[0,1].scatter(comparison['stations_m']*1000,comparison['experimental_mean_Pa']/1000,
                marker='x',c='k',label='Mundt Run 937: long-window mean')
        axes[0,1].set(xlabel='Axial distance [mm]',ylabel='Mean pressure [kPa]')
        if axes[0,1].get_legend_handles_labels()[0]: axes[0,1].legend(fontsize=8)
        if len(rows)>1:
            axes[1,0].plot(t[1:]*1e6,[row['mdot_in']*1e3 for row in rows[1:]],label='Inlet')
            axes[1,0].plot(t[1:]*1e6,[row['mdot_out']*1e3 for row in rows[1:]],label='Outlet')
        axes[1,0].set(xlabel='Time [µs]',ylabel='Native numerical mass flow [g/s]')
        axes[1,0].legend()
        inventory=np.array([row['inventory'] for row in rows]); residual=np.array([row['residual'] for row in rows])
        scale=np.maximum(np.maximum(np.abs(inventory[0]),np.max(np.abs(inventory-inventory[0]),axis=0)),1e-30)
        for index,label in enumerate(['Mass','θ momentum','Axial momentum','Energy','Reacted mass']):
            axes[1,1].semilogy(t*1e6,np.maximum(np.abs(residual[:,index])/scale[index],1e-18),label=label)
        axes[1,1].set(xlabel='Time [µs]',ylabel='Inventory/storage-scaled budget residual')
        axes[1,1].legend(ncol=2,fontsize=8)
        if 'probe_pressure_Pa' in rows[0]:
            pp=np.array([row['probe_pressure_Pa'] for row in rows])
            axes[2,0].plot(t*1e6,pp/1e6,label='Local pressure')
            twin=axes[2,0].twinx()
            twin.plot(t*1e6,[row['probe_progress'] for row in rows],color='tab:orange',alpha=.7)
            twin.set(ylabel='Reaction progress',ylim=(-.05,1.05))
            if len(t)>1:
                events=pressure_arrivals(t,pp,2*calibration['p1'],1.25*calibration['p1']).tolist()
            for arrival in events:
                axes[2,0].axvline(arrival*1e6,color='gray',lw=.6,alpha=.6)
        axes[2,0].set(xlabel='Time [µs]',ylabel='Fixed-probe pressure [MPa]',title='Pressure events need reaction/front inspection')
        axes[2,1].fill_between(t*1e6,[row['exit_cell_axial_mach_min'] for row in rows],
                              [row['exit_cell_axial_mach_max'] for row in rows],alpha=.4,label='Exit axial Mach range')
        # A circumferentially uniform exit has a zero-width band; retain its limits.
        axes[2,1].plot(t*1e6,[row['exit_cell_axial_mach_min'] for row in rows],color='tab:blue',lw=1.)
        axes[2,1].plot(t*1e6,[row['exit_cell_axial_mach_max'] for row in rows],color='tab:blue',lw=1.)
        axes[2,1].axhline(1,color='k',ls='--',lw=.8)
        axes[2,1].axhline(0,color='k',ls=':',lw=.8)
        axes[2,1].set(xlabel='Time [µs]',ylabel='Axial Mach')
        axes[2,1].legend(fontsize=8)
        for ax in axes.flat:
            ax.grid(alpha=.2)
        fig.suptitle(f'{mode_label}: {summary["status"]}; {summary["t"]*1e6:.3f} µs — transient diagnostics, not converged engine performance')
        fig.savefig(destination/'diagnostics.png',dpi=150)
    finally:
        plt.close(fig)
    report=dict(status=summary['status'],run_mode=mode,
                experimental_pressure_overlay=comparison['available'],
                experimental_comparison_reason=comparison.get('reason',comparison.get('qualification')),
                time_s=summary['t'],snapshot_count=len(fields),native_rows=len(rows),
                reaction_rate_available=rate_available,
                pressure_event_times_s=events,pressure_event_count=len(events),
                event_high_Pa=2*calibration['p1'],event_rearm_Pa=1.25*calibration['p1'],
                interpretation='Pressure crossings only, not confirmed detonation passages or a mode count.',
                max_inventory_storage_scaled_residual=float(np.max(np.abs(residual)/scale)))
    (destination/'analysis.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def _render_coupling(report, arrays, destination):
    """Render one inspected prefix; all numerical inputs have already been read."""
    import numpy as np
    from matplotlib.colors import LogNorm
    plt=_pyplot()
    saved=arrays['saved']; fields=saved['fields']; r=saved['inputs']['resolved']
    times=arrays['times']; threshold=report['definitions']['pressure_threshold_Pa']
    pressure=np.stack([f['pressure'] for f in fields])/1e6
    heat=np.array(arrays['heat_fields'])
    pnorm=LogNorm(max(float(pressure.min()),1e-9),max(float(pressure.max()),float(pressure.min())*1.01))
    active=bool(np.any(heat>0))
    hmax=max(float(heat.max()),1.)
    hnorm=LogNorm(hmax*1e-6,hmax*1.001)
    heat_cmap=plt.get_cmap('inferno').copy()
    heat_cmap.set_bad(heat_cmap(0.))
    heat_cmap.set_under(heat_cmap(0.))
    x=(np.arange(r['nx'])+.5)*r['dx']*1e3
    z=(np.arange(r['ny'])+.5)*r['dy']*1e3
    chosen=np.unique([int(np.argmin(abs(times-target))) for target in [20e-6,40e-6,100e-6,times[-1]]])
    fig,axes=plt.subplots(2,len(chosen),figsize=(3.5*len(chosen)+1,6),squeeze=False,layout='constrained')
    try:
        for column,index in enumerate(chosen):
            extent=[0,r['width']*1e3,0,r['length']*1e3]
            pimage=axes[0,column].imshow(pressure[index].T,origin='lower',extent=extent,aspect='auto',norm=pnorm,cmap='magma')
            himage=axes[1,column].imshow(np.ma.masked_less_equal(heat[index].T,0.),origin='lower',extent=extent,aspect='auto',norm=hnorm,cmap=heat_cmap)
            if not active:
                axes[1,column].text(.5,.5,'No active reaction',ha='center',transform=axes[1,column].transAxes)
            if len(x)>1 and len(z)>1:
                p=fields[index]['pressure']; xi=fields[index]['progress']
                levels=[value for value in [threshold,2*threshold] if p.min()<value<p.max()]
                if levels:
                    axes[1,column].contour(x,z,p.T,levels=levels,colors='white',linewidths=.6)
                if xi.min()<.5<xi.max():
                    axes[1,column].contour(x,z,xi.T,levels=[.5],colors='cyan',linewidths=.6)
            axes[0,column].set_title(f'{times[index]*1e6:.2f} µs')
            for row in range(2):
                axes[row,column].set(xlabel='Circumferential distance [mm]',ylabel='Axial distance [mm]' if column==0 else '')
        fig.colorbar(pimage,ax=axes[0].tolist(),label='Pressure [MPa], log')
        fig.colorbar(himage,ax=axes[1].tolist(),label='Chemical-to-thermal conversion [W/m³], log')
        fig.suptitle('Saved full-height fields; white contours: p=2p₁ / 4p₁; cyan: progress 0.5')
        fig.savefig(destination/'reaction_fields.png',dpi=140)
    finally:
        plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(14,5),layout='constrained')
    try:
        if len(times)>1:
            image=axes[0].pcolormesh(times*1e6,z,np.ma.masked_less_equal(arrays['axial_heat'].T,0.),shading='nearest',norm=hnorm,cmap=heat_cmap)
            fig.colorbar(image,ax=axes[0],label='Circumferential mean conversion [W/m³]')
            image=axes[1].pcolormesh(times*1e6,z,arrays['axial_pressure'].T/1e6,shading='nearest',norm=pnorm,cmap='magma')
            fig.colorbar(image,ax=axes[1],label='Circumferential maximum pressure [MPa]')
        else:
            for ax in axes[:2]:
                ax.text(.5,.5,'One saved time only',ha='center',transform=ax.transAxes)
        quantiles=np.array([row['conversion_height_quantiles_m'] for row in report['snapshots']],dtype=float)*1e3
        axes[2].fill_between(times*1e6,quantiles[:,0],quantiles[:,2],alpha=.25,label='10–90% conversion height')
        axes[2].plot(times*1e6,quantiles[:,1],label='Median conversion height')
        fill=saved['inputs']['config']['initialization'].get('fill_height_mm')
        if fill is not None:
            axes[2].axhline(fill,color='k',ls='--',label='Initial fill height')
        for ax in axes:
            ax.set(xlabel='Time [µs]',ylabel='Axial distance [mm]',ylim=(0,r['length']*1e3))
        axes[2].legend(fontsize=8)
        fig.suptitle('Where reaction occurs; conversion height does not identify a flame or detonation front')
        fig.savefig(destination/'axial_evolution.png',dpi=140)
    finally:
        plt.close(fig)

    rings=arrays['rings']
    fig,axes=plt.subplots(len(rings),3,figsize=(14,3.3*len(rings)),squeeze=False,layout='constrained')
    try:
        for row,ring in enumerate(rings):
            for column,(values,title) in enumerate([(ring['pressure']/1e6,'Pressure [MPa]'),
                    (ring['thermal_conversion'],'Chemical-to-thermal conversion [W/m³]'),(ring['progress'],'Reaction progress')]):
                ax=axes[row,column]
                if len(times)>1:
                    options=dict(cmap='viridis',vmin=0,vmax=1) if column==2 else dict(cmap='magma' if column==0 else heat_cmap,norm=pnorm if column==0 else hnorm)
                    shown=np.ma.masked_less_equal(values,0.) if column==1 else values
                    image=ax.pcolormesh(x,times*1e6,shown,shading='nearest',**options)
                    fig.colorbar(image,ax=ax)
                else:
                    ax.text(.5,.5,'One saved time only',ha='center',transform=ax.transAxes)
                if column<2:
                    for track in ring['tracks']:
                        samples=track['samples']
                        xx=np.array([s['x_m'] for s in samples])*1e3
                        tt=np.array([s['time_s'] for s in samples])*1e6
                        segments=np.split(np.arange(len(xx)),np.flatnonzero(abs(np.diff(xx))>r['width']*500)+1)
                        for segment in segments:
                            ax.plot(xx[segment],tt[segment],color='white',lw=.65,marker='.',ms=1.5)
                ax.set(xlabel='Circumferential distance [mm]',ylabel='Time [µs]' if column==0 else '',
                       title=f'z={ring["z_m"]*1e3:.3f} mm — {title}')
        fig.suptitle('White tracks: pressure-peak candidates; a track is not a confirmed detonation')
        fig.savefig(destination/'ring_tracks.png',dpi=140)
    finally:
        plt.close(fig)
    (destination/'coupling.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


def plot_coupling(directory, destination, compare_directory=None, heights_mm=(1.,4.,8.,16.)):
    """Inspect saved fields and optionally compare two declared cases; no CFD calls."""
    import hashlib
    import numpy as np
    from coupling import inspect_run, compare_inputs
    first,first_arrays=inspect_run(directory,heights_mm=heights_mm)
    if compare_directory is not None:
        second,second_arrays=inspect_run(compare_directory,heights_mm=heights_mm)
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    first['plot_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if compare_directory is None:
        _render_coupling(first,first_arrays,destination)
        return first
    second['plot_source_sha256']=first['plot_source_sha256']
    for name,report,arrays in [('baseline',first,first_arrays),('variant',second,second_arrays)]:
        (destination/name).mkdir()
        _render_coupling(report,arrays,destination/name)
    inputs=[arrays['saved']['inputs'] for arrays in [first_arrays,second_arrays]]
    comparison=compare_inputs(*inputs)
    comparison.update(baseline=str(Path(directory).resolve()),variant=str(Path(compare_directory).resolve()),
        interpretation='Controlled inputs must be inspected. Pressure/conversion overlap and short tracks do not establish sustained detonation.',
        cases=[dict(status=report['status'],time_s=report['time_s'],prefix_step=report['prefix_step'],
                    last_snapshot=report['snapshots'][-1],native_chemical_conversion_J=report['native_chemical_conversion_J'],
                    snapshot_trapezoid_conversion_J=report['snapshot_trapezoid_conversion_J']) for report in [first,second]])
    plt=_pyplot()
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    try:
        for label,report in [('Baseline',first),('Variant',second)]:
            rows=report['snapshots']; t=np.array([row['time_s'] for row in rows])*1e6
            axes[0,0].plot(t,[row['pressure_max_Pa']/1e6 for row in rows],label=label)
            axes[0,1].plot(t,[row['thermal_conversion_W']/1e6 for row in rows],label=label)
            axes[1,0].plot(t,[row['conversion_fraction_p_above_threshold'] for row in rows],label=label)
            quantiles=np.array([row['conversion_height_quantiles_m'] for row in rows],dtype=float)*1e3
            line,=axes[1,1].plot(t,quantiles[:,1],label=label)
            axes[1,1].fill_between(t,quantiles[:,0],quantiles[:,2],color=line.get_color(),alpha=.15)
        for ax in axes.flat:
            ax.set_xlabel('Time [µs]'); ax.grid(alpha=.2); ax.legend(fontsize=8)
        axes[0,0].set(ylabel='Domain maximum pressure [MPa]',yscale='log')
        axes[0,1].set_ylabel('Chemical-to-thermal conversion [MW]')
        axes[1,0].set(ylabel='Conversion fraction at p ≥ 2p₁',ylim=(-.02,1.02))
        axes[1,1].set_ylabel('Median and 10–90% conversion heights [mm]')
        energies=comparison['initialization_energy_change_J']
        energy_label='not available' if any(e is None for e in energies) else f'{energies[0]:.3f} / {energies[1]:.3f} J'
        fig.suptitle(f'Saved-run comparison; initialization energy changes: {energy_label}')
        fig.savefig(destination/'comparison.png',dpi=150)
    finally:
        plt.close(fig)
    (destination/'comparison.json').write_text(json.dumps(comparison,indent=2,allow_nan=False)+'\n')
    return comparison


def plot_experiments(directory, destination):
    """Render saved contact/refinement results without advancing the solver."""
    import numpy as np
    directory,destination=Path(directory),Path(destination)
    report=json.loads((directory/'summary.json').read_text())
    cases=report['cases'];destination.mkdir(parents=True,exist_ok=False);plt=_pyplot()
    colors={dx:color for dx,color in zip(sorted({c['dx_m'] for c in cases},reverse=True),['#245ca6','#c76524','#308257','#8b549c'])}
    if report['kind']=='contact':
        fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        try:
            for case in cases:
                folder=directory/case['directory'];inputs=json.loads((folder/'inputs.json').read_text())
                summary=case['summary'];rows=summary['history'];dx=case['dx_m'];color=colors[dx]
                label=f'{dx*1e3:g} mm';style='-' if case['reactive'] else '--'
                if case['reactive']:
                    axes[0,0].plot([r['time_s']*1e6 for r in rows],[r['conversion_J_m2'] for r in rows],color=color,label=label)
                    axes[0,1].plot([r['time_s']*1e6 for r in rows],[r['pressure_max_Pa']/1e3 for r in rows],color=color,label=label)
                with np.load(folder/'fields.npz',allow_pickle=False) as data:
                    x=data['x'];W=data['primitive'][-1];t=data['times'][-1]
                relative=(x-inputs['initial_contact_m']-inputs['velocity_mps']*t)*1e3
                axes[1,0].plot(relative,W[3]/(W[0]*inputs['calibration']['R']),style,color=color,label=label if case['reactive'] else None)
                axes[1,1].plot(relative,W[4],style,color=color)
            axes[0,0].set(xlabel='Time [µs]',ylabel='Converted chemical energy [J/m²]')
            axes[0,1].set(xlabel='Time [µs]',ylabel='Maximum pressure [kPa]')
            axes[1,0].set(xlabel='Distance from exact advected contact [mm]',ylabel='Temperature [K]',xlim=(-5,5))
            axes[1,1].set(xlabel='Distance from exact advected contact [mm]',ylabel='Reaction progress',xlim=(-5,5),ylim=(-.02,1.02))
            for ax in axes.flat:ax.grid(alpha=.2)
            axes[0,0].legend(title='Cell size');axes[1,0].legend(title='Solid: reactive; dashed: frozen',fontsize=8)
            fig.suptitle('Moving hot-product / fresh-gas contact at 20 µs; fixed chemistry and common time cap')
            fig.savefig(destination/'contact_profiles.png',dpi=150)
        finally:plt.close(fig)
        fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
        try:
            active=sorted((c for c in cases if c['reactive']),key=lambda c:c['dx_m'])
            frozen=sorted((c for c in cases if not c['reactive']),key=lambda c:c['dx_m'])
            axes[0].loglog([c['dx_m']*1e3 for c in active],[c['summary']['final']['conversion_J_m2'] for c in active],'o-')
            axes[1].loglog([c['dx_m']*1e3 for c in frozen],[c['summary']['final']['frozen_density_L1_kg_m3'] for c in frozen],'o-')
            axes[0].set(ylabel='Reactive conversion at 20 µs [J/m²]')
            axes[1].set(ylabel='Frozen density L1 error [kg/m³]')
            for ax in axes:ax.set_xlabel('Cell size [mm]');ax.grid(alpha=.2,which='both')
            fig.suptitle('Contact sensitivity: numerical mixing decreases with refinement')
            fig.savefig(destination/'contact_refinement.png',dpi=150)
        finally:plt.close(fig)
    elif report['kind']=='refinement':
        inputs=json.loads((directory/'inputs.json').read_text());cj=inputs['calibration']['D_CJ']
        fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        rows=[]
        try:
            for case in cases:
                dx=case['dx_m'];label=f'{dx*1e3:g} mm';color=colors[dx]
                with np.load(directory/case['directory']/'fields.npz',allow_pickle=False) as data:
                    x=data['x'];W=data['primitive'][-1];h=data['history']
                mask=(h[:,0]>=65e-6)&(h[:,0]<90e-6)&np.isfinite(h[:,1])
                late=float(np.polyfit(h[mask,0],h[mask,1],1)[0]) if mask.sum()>20 else None
                rows.append(dict(dx_mm=dx*1e3,fit_40_95_mps=case['summary']['speed_mps'],fit_65_90_mps=late,
                                 final_front_separation_mm=case['summary']['final_front_separation_m']*1e3))
                axes[0,1].plot(h[:,0]*1e6,h[:,1]*1e3,color=color,label=label)
                axes[1,0].plot(h[:,0]*1e6,(h[:,1]-h[:,2])*1e3,color=color,label=label)
                axes[1,1].plot((h[-1,1]-x)*1e3,W[4],color=color,label=label)
            axes[0,0].plot([r['dx_mm'] for r in rows],[r['fit_40_95_mps'] for r in rows],'o-',label='40–95 µs fit')
            axes[0,0].plot([r['dx_mm'] for r in rows],[r['fit_65_90_mps'] for r in rows],'s--',label='65–90 µs fit')
            axes[0,0].axhline(cj,color='k',ls=':',label='Fitted surrogate CJ reference')
            axes[0,0].set(xlabel='Cell size [mm]',ylabel='Pressure-front speed [m/s]')
            axes[0,1].set(xlabel='Time [µs]',ylabel='Pressure-front position [mm]')
            axes[1,0].set(xlabel='Time [µs]',ylabel='Pressure-to-50% front distance [mm]',xlim=(40,95))
            axes[1,1].set(xlabel='Distance behind final pressure front [mm]',ylabel='Reaction progress',xlim=(-1,8),ylim=(-.02,1.02))
            for ax in axes.flat:ax.grid(alpha=.2);ax.legend(fontsize=8)
            fig.suptitle('1D fixed-chemistry spatial comparison; transient/window sensitivity remains')
            fig.savefig(destination/'propagation_refinement.png',dpi=150)
        finally:plt.close(fig)
        (destination/'speed_windows.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    else:raise ValueError('unknown saved experiment kind')
    return report


def plot_reference(directory, destination):
    """Render saved physical/surrogate profiles; never load a chemistry package."""
    import numpy as np
    directory,destination=Path(directory),Path(destination)
    report=json.loads((directory/'summary.json').read_text())
    with np.load(directory/'profiles.npz',allow_pickle=False) as f:data={k:f[k].copy() for k in f.files}
    destination.mkdir(parents=True,exist_ok=False);plt=_pyplot()
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    try:
        for prefix,label,color in [('', 'Physical GRI-Mech ZND','#245ca6'),('surrogate_','Inherited one-step surrogate','#c76524')]:
            x=data[prefix+'distance_m']*1e3
            for ax,key,scale in [(axes[0,0],'pressure_Pa',1e-6),(axes[0,1],'temperature_K',1.),(axes[1,0],'heat_fraction',1.)]:
                mask=x>0
                ax.semilogx(x[mask],data[prefix+key][mask]*scale,color=color,label=label)
                ax.set(xlabel='Distance behind shock [mm]',xlim=(.001,10))
                ax.grid(alpha=.2,which='both')
        axes[0,0].set_ylabel('Pressure [MPa]');axes[0,1].set_ylabel('Temperature [K]')
        axes[1,0].set_ylabel('Fraction of own equilibrium/model heat release')
        axes[0,0].legend(fontsize=8)
        axes[1,1].plot(data['time_s']*1e6,data['dTdt_K_s']/1e9,label='Physical dT/dt')
        axes[1,1].axvline(report['znd']['induction_time_max_dTdt_s']*1e6,color='#c76524',ls='--',label='Temperature-rise maximum')
        axes[1,1].axvline(report['znd']['peak_thermicity_time_s']*1e6,color='#308257',ls=':',label='Thermicity maximum')
        axes[1,1].set(xlabel='Time behind shock [µs]',ylabel='Temperature rise rate [10⁹ K/s]',xlim=(0,.5))
        axes[1,1].legend(fontsize=8);axes[1,1].grid(alpha=.2)
        fig.suptitle('Run 937 reference audit: detailed chemistry versus fitted, thickened surrogate')
        fig.savefig(destination/'reference_profiles.png',dpi=150)
    finally:plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    try:
        nominal=report['nominal'];samples=report['neighborhood'];surrogate=report['surrogate']
        for column,(name,key,fixed,scale,label) in enumerate([
            ('phi','phi','pressure_Pa',1.,'Equivalence ratio'),
            ('pressure','pressure_Pa','phi',1e-3,'Initial pressure [kPa]')]):
            points=sorted([s for s in samples if np.isclose(s[fixed],nominal[fixed])],key=lambda s:s[key])
            x=[s[key]*scale for s in points]
            axes[0,column].plot(x,[s['CJ_speed_mps'] for s in points],'o-',label='Cantera/SDToolbox reference')
            axes[0,column].axhline(surrogate['D_CJ'],color='#c76524',ls='--',label='Fixed Run 937 surrogate / paper CJ')
            axes[1,column].plot(x,[s['q_equilibrium_Jkg']/1e6 for s in points],'o-',label='Independent GRI-Mech equilibrium')
            axes[1,column].axhline(surrogate['q']/1e6,color='#c76524',ls='--',label='Fixed surrogate q')
            for row in range(2):axes[row,column].set_xlabel(label);axes[row,column].grid(alpha=.2);axes[row,column].legend(fontsize=7)
            axes[0,column].set_ylabel('CJ speed [m/s]');axes[1,column].set_ylabel('Heat release [MJ/kg reactants]')
        fig.suptitle('Small Run 937 reference neighborhood; CEA has not been executed')
        fig.savefig(destination/'reference_neighborhood.png',dpi=150)
    finally:plt.close(fig)
    return report


def plot_formed(directory,destination):
    """Inspect already saved C2 pressure/reaction association and causal margins."""
    import numpy as np
    directory,destination=Path(directory),Path(destination)
    report=json.loads((directory/'summary.json').read_text());inputs=json.loads((directory/'inputs.json').read_text())
    with np.load(directory/'fields.npz',allow_pickle=False) as a:
        x=a['x'].copy();w=a['primitive'].copy();times=a['times'].copy()
    c=inputs['calibration'];h=report['history']
    destination.mkdir(parents=True,exist_ok=False)
    plt=_pyplot();fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    try:
        for i in sorted(set([0,len(times)//2,len(times)-1])):
            front=h[i]['front_m']
            if front is None:continue
            offset=(x-front)*1e3;label=f'{times[i]*1e6:.1f} µs'
            temp=w[i,3]/(c['R']*w[i,0]);rate=c['k']*(1-w[i,4])*np.exp(-c['Ea']/(c['R']*temp))
            axes[0,0].plot(offset,w[i,3]/1e6,label=label)
            axes[0,1].plot(offset,rate/1e6,label=label)
        axes[0,0].set(xlim=(-15,5),xlabel='Distance from pressure-threshold front [mm]',ylabel='Pressure [MPa]')
        axes[0,1].set(xlim=(-15,5),xlabel='Distance from pressure-threshold front [mm]',ylabel='Reaction rate [1/µs]')
        front=np.array([np.nan if r['front_m'] is None else r['front_m'] for r in h])
        axes[1,0].plot(times*1e6,(front-inputs['shock_initial_m']-c['D_CJ']*times)*1e3)
        axes[1,0].set(xlabel='Time [µs]',ylabel='Front departure from CJ travel [mm]')
        for key,label in [('left_causal_margin_m',f"Left, including {inputs['reaction_roi_behind_front_m']*1e3:g} mm reaction region"),('right_causal_margin_m','Right')]:
            axes[1,1].plot(times*1e6,[r[key]*1e3 if r[key] is not None else np.nan for r in h],label=label)
        axes[1,1].axhline(0,color='k',linewidth=.7)
        axes[1,1].set(xlabel='Time [µs]',ylabel='Remote-boundary cone margin [mm]')
        for ax in axes.flat:ax.grid(alpha=.25)
        axes[0,0].legend();axes[1,1].legend(fontsize=8)
        fig.suptitle(f"C2: formed wave, Δx = {inputs['dx_m']*1e3:g} mm, source fraction {inputs['source_cfl']:g}")
        fig.savefig(destination/'formed_control.png',dpi=140)
    finally:plt.close(fig)
    return report


def plot_layer(directory,destination):
    """Saved C3 fields, several layer rows and independent causal diagnostics."""
    import numpy as np
    from matplotlib.colors import LogNorm
    directory,destination=Path(directory),Path(destination)
    report=json.loads((directory/'summary.json').read_text());inputs=json.loads((directory/'inputs.json').read_text())
    with np.load(directory/'fields.npz',allow_pickle=False) as a:
        x=a['x'].copy();z=a['z'].copy();w=a['primitive'][-1].copy();times=a['times'].copy()
    c=inputs['calibration'];history=report['history'];h=inputs['initialization']['layer_height_m']
    rows=inputs['diagnostic_row_indexes'];zs=inputs['diagnostic_row_z_m']
    finalfront=[row['front_m'] for row in history[-1]['rows'] if row['front_m'] is not None]
    reference=max(finalfront) if finalfront else inputs['shock_initial_m']
    near=(x>reference-.04)&(x<reference+.01);low=z<h+.02
    temp=w[3]/(c['R']*w[0]);rate=c['k']*np.maximum(0,1-w[4])*np.exp(-c['Ea']/(c['R']*temp))
    heat=c['q']*w[0]*rate/1e12
    destination.mkdir(parents=True,exist_ok=False)
    plt=_pyplot();fig,axes=plt.subplots(3,2,figsize=(12,10),layout='constrained')
    try:
        X=x[near]*1e3;Z=z[low]*1e3
        im=axes[0,0].pcolormesh(X,Z,w[3][np.ix_(near,low)].T/1e6,shading='auto',cmap='magma')
        fig.colorbar(im,ax=axes[0,0],label='Pressure [MPa]')
        vmax=max(1e-5,float(heat.max()));im=axes[0,1].pcolormesh(X,Z,np.maximum(heat[np.ix_(near,low)].T,1e-7),
            shading='auto',cmap='inferno',norm=LogNorm(vmin=1e-6,vmax=vmax))
        fig.colorbar(im,ax=axes[0,1],label='Heat release [TW/m³]')
        for ax in axes[0]:ax.axhline(h*1e3,color='cyan',ls='--',lw=.8);ax.set(xlabel='x [mm]',ylabel='Height [mm]')
        for j,(idx,height) in enumerate(zip(rows,zs)):
            label=f'z = {height*1e3:.2f} mm'
            axes[1,0].plot(x[near]*1e3,w[3,near,idx]/1e6,label=label)
            axes[1,1].plot(x[near]*1e3,rate[near,idx]/1e6,label=label)
            axes[2,0].plot(times*1e6,[hh['rows'][j]['front_m']*1e3 if hh['rows'][j]['front_m'] is not None else np.nan for hh in history],label=label)
        axes[1,0].set(xlabel='x [mm]',ylabel='Final pressure [MPa]')
        axes[1,1].set(xlabel='x [mm]',ylabel='Final reaction rate [1/µs]')
        axes[2,0].set(xlabel='Time [µs]',ylabel='Pressure-threshold front [mm]')
        for key,label in [('left_causal_margin_m','Left/reaction region'),('right_causal_margin_m','Right'),('top_causal_margin_m','Top/layer')]:
            axes[2,1].plot(times*1e6,[hh[key]*1e3 if hh[key] is not None else np.nan for hh in history],label=label)
        axes[2,1].axhline(0,color='k',lw=.7);axes[2,1].set(xlabel='Time [µs]',ylabel='Remote-boundary cone margin [mm]')
        for ax in axes[1:].flat:ax.grid(alpha=.25)
        axes[1,0].legend(fontsize=8);axes[2,1].legend(fontsize=8)
        alignment='face aligned' if inputs['initialization'].get('interface_aligned',False) else 'uniform grid'
        label='Blast layer' if inputs['initialization'].get('start','formed')=='blast' else 'Formed layer'
        fig.suptitle(f"{label}: h = {h*1e3:g} mm, Δx = {inputs['initialization']['dx_m']*1e3:g} mm, t = {report['time_s']*1e6:.1f} µs ({alignment})")
        fig.savefig(destination/'layer_control.png',dpi=140)
    finally:plt.close(fig)
    return report


def plot_layer_comparison(directories,destination):
    """Compare saved wall-row fields; unequal initial charge is deliberately explicit."""
    import numpy as np
    if len(directories)<2:raise ValueError('at least two saved layer runs required')
    cases=[]
    for directory in map(Path,directories):
        report=json.loads((directory/'summary.json').read_text());inputs=json.loads((directory/'inputs.json').read_text())
        if report['kind']!='layer':raise ValueError('comparison requires saved layer runs')
        c=inputs['calibration']
        if cases and c!=cases[0]['calibration']:raise ValueError('layer comparison requires identical chemistry')
        with np.load(directory/'fields.npz',allow_pickle=False) as a:
            x=a['x'].copy();times=a['times'].copy();w=a['primitive'][:,:,:,0].copy()
        if len(report['history'])!=len(times):raise ValueError('layer fields/history length mismatch')
        T=w[:,3]/(c['R']*w[:,0]);rate=c['k']*np.maximum(0,1-w[:,4])*np.exp(-c['Ea']/(c['R']*T))
        front=np.array([h['rows'][0]['front_m'] if h['rows'][0]['front_m'] is not None else np.nan for h in report['history']])
        # Follow the right-going observation region. A blast also launches a
        # left-going wave, so an unrestricted global peak can select that wave.
        # The fixed lower edge retains the full initial formed tail and does
        # not move forward with a detached reaction peak.
        gaps=[]
        for v,f in zip(rate,front):
            region=(x>=inputs['shock_initial_m']-.03)&(x<=f)
            peak=int(np.argmax(np.where(region,v,-1))) if region.any() else None
            gaps.append(f-x[peak] if peak is not None and v[peak]>0 else np.nan)
        gap=np.asarray(gaps)
        near=np.array([np.max(v[(x>=f-.002-1e-12)&(x<=f+1e-12)]) if np.isfinite(f) else np.nan for v,f in zip(rate,front)])
        init=inputs['initialization'];label=f"{init.get('start','formed')}, h={init['layer_height_m']*1e3:g}, Δx={init['dx_m']*1e3:g} mm"
        cases.append(dict(label=label,calibration=c,times=times,front=front,gap=gap,rate=rate,near=near,
                          x=x,w=w,shock=inputs['shock_initial_m']))
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    plt=_pyplot();fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    try:
        for case in cases:
            label=case['label'];times=case['times']*1e6
            axes[0,0].plot(times,(case['front']-case['shock'])*1e3,label=label)
            axes[0,1].plot(times,case['gap']*1e3,label=label)
            distance=(case['x']-case['front'][-1])*1e3
            axes[1,0].plot(distance,case['w'][-1,3]/1e6,label=label)
            axes[1,1].plot(times,np.where(case['near']>0,case['near'],np.nan),label=label)
        axes[0,0].set(xlabel='Time [µs]',ylabel='Wall pressure-front displacement [mm]')
        axes[0,1].set(xlabel='Time [µs]',ylabel='Wall front − forward-region rate peak [mm]')
        axes[1,0].set(xlabel='Distance from final wall pressure front [mm]',ylabel='Final wall pressure [MPa]',xlim=(-35,5))
        axes[1,1].set(xlabel='Time [µs]',ylabel='Peak rate within 2 mm behind wall front [1/s]',yscale='log')
        axes[0,0].legend(fontsize=8)
        for ax in axes.flat:ax.grid(alpha=.25)
        fig.suptitle('Bounded layer controls: wall-row comparison\nInitial inventories recorded separately; pressure track alone is not a detonation criterion')
        fig.savefig(destination/'layer_comparison.png',dpi=140)
    finally:plt.close(fig)
    return cases


def plot_controlled(directory, destination):
    """C1 strip fields and comparison histories from saved data only."""
    import numpy as np
    directory,destination=Path(directory),Path(destination)
    report=json.loads((directory/'summary.json').read_text())
    if report['kind']=='formed':return plot_formed(directory,destination)
    if report['kind']=='layer':return plot_layer(directory,destination)
    if report['kind']!='strip':raise ValueError('unsupported controlled diagnostic')
    with np.load(directory/'fields.npz',allow_pickle=False) as data:
        x=data['x'].copy();fields=data['primitive'].copy()
    destination.mkdir(parents=True,exist_ok=False)
    plt=_pyplot();fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    try:
        times=np.array([h['time_s'] for h in report['history']])*1e6
        for i,name in enumerate(report['cases']):
            style=['-','--',':','-.'][i]
            axes[0,0].plot(x*1e3,fields[-1,i,3]/1e6,style,label=name)
            axes[0,1].plot(x*1e3,fields[-1,i,4],style,label=name)
            axes[1,0].plot(times,[np.nan if h['front_m'][i] is None else h['front_m'][i]*1e3 for h in report['history']],style,label=name)
            axes[1,1].plot(times,[max(h['max_scaled_difference'][i],1e-18) for h in report['history']],style,label=name)
        axes[0,0].set(xlabel='Propagation coordinate [mm]',ylabel='Final pressure [MPa]')
        axes[0,1].set(xlabel='Propagation coordinate [mm]',ylabel='Final reaction progress')
        axes[1,0].set(xlabel='Time [µs]',ylabel='Pressure-threshold front [mm]')
        axes[1,1].set(xlabel='Time [µs]',ylabel='Scaled field difference (zeros shown at 1e-18)',yscale='log')
        for ax in axes.flat:ax.grid(alpha=.25)
        axes[0,0].legend(fontsize=8)
        fig.suptitle('C1: row and direction controls; overlapping traces are expected')
        fig.savefig(destination/'strip_control.png',dpi=140)
    finally:plt.close(fig)
    return report


def plot_workflow(directory, destination, start, end, frames=12, segment_s=None, inertia=None, compare_runs=None):
    """Streaming saved-field viewer plus native window report; never advances CFD."""
    import html
    import numpy as np
    from matplotlib.colors import Normalize, LogNorm
    from contracts import iter_fields
    from workflow import collect_workflow, compare_saved_runs, write_data
    destination=Path(destination)
    sources=[Path(directory),*(Path(p) for p in (compare_runs or []))]
    if any(destination.resolve().is_relative_to(p.resolve()) for p in sources):
        raise ValueError('workflow output must be outside every saved run')
    if not isinstance(frames,int) or not 1<=frames<=60:
        raise ValueError('preview frame count must lie in [1,60]')
    if destination.exists():
        raise FileExistsError(destination)
    data=collect_workflow(directory,start,end,segment_s,inertia)
    comparison=compare_saved_runs(sources,start,end) if compare_runs else None
    inputs,summary,report=data['inputs'],data['summary'],data['report']
    r=inputs['resolved']; preview=report['preview']; plt=_pyplot()
    destination.mkdir(parents=True,exist_ok=False)
    try:
        steps=preview['selected_step_ids']
        chosen=set(np.asarray(steps)[np.unique(np.rint(np.linspace(0,len(steps)-1,min(frames,len(steps)))).astype(int))]) if steps else set()
        if steps:
            lo,hi=preview['pressure_range_Pa'];pnorm=Normalize(lo/1e6,max(hi,lo*1.001)/1e6)
            maximum=preview['reaction_rate_max_per_s']
            rate_options=dict(norm=LogNorm(maximum*1e-6,maximum*1.001)) if maximum>0 else dict(vmin=0,vmax=1)
        frame_items=[];last=None
        for frame in iter_fields(directory,inputs,summary['steps'],selected_steps=chosen):
            if frame['step'] not in chosen: continue
            fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
            try:
                extent=[0,r['width']*1000,0,r['length']*1000]
                items=[(frame['pressure']/1e6,'Pressure [MPa]',dict(norm=pnorm,cmap='magma')),
                       (frame['progress'],'Reaction progress',dict(vmin=0,vmax=1,cmap='viridis')),
                       (frame['reaction_rate'],'Reaction rate [1/s]',dict(cmap='inferno',**rate_options))]
                for ax,(array,title,options) in zip(axes,items):
                    im=ax.imshow(array.T,origin='lower',extent=extent,aspect='auto',**options)
                    ax.set(xlabel='Circumferential x [mm]',ylabel='Axial z [mm]',title=title)
                    fig.colorbar(im,ax=ax)
                fig.suptitle(f"Reduced 2D — {frame['t']*1e6:.6g} µs — {summary.get('run_mode','engine_intervals')}")
                name=f'frame_{len(frame_items):03d}.png';fig.savefig(destination/name,dpi=110)
                frame_items.append(dict(file=name,time_us=frame['t']*1e6,step=frame['step']))
            finally: plt.close(fig)
            last=frame
        report['preview']['rendered_frames']=frame_items
        if last is not None:
            # Fixed-radius surface and radially repeated ring are displays only.
            ix=np.unique(np.rint(np.linspace(0,r['nx']-1,min(100,r['nx']))).astype(int))
            iz=np.unique(np.rint(np.linspace(0,r['ny']-1,min(60,r['ny']))).astype(int))
            theta=(ix+.5)*r['dx']/r['r_mean']; z=(iz+.5)*r['dy']*1000
            theta=np.r_[theta,theta[0]+2*np.pi]; wrapped_ix=np.r_[ix,ix[0]]
            th,zz=np.meshgrid(theta,z,indexing='ij')
            fig=plt.figure(figsize=(12,5),layout='constrained')
            try:
                ax=fig.add_subplot(1,2,1,projection='3d')
                colors=plt.get_cmap('magma')(pnorm(last['pressure'][np.ix_(wrapped_ix,iz)]/1e6))
                ax.plot_surface(r['r_mean']*1000*np.cos(th),r['r_mean']*1000*np.sin(th),zz,
                    facecolors=colors,shade=False,rcount=len(wrapped_ix),ccount=len(iz))
                ax.set(xlabel='X [mm]',ylabel='Y [mm]',zlabel='z [mm]',title='Pressure on mean-radius surface — 2D display')
                scalar=plt.cm.ScalarMappable(norm=pnorm,cmap='magma');fig.colorbar(scalar,ax=ax,shrink=.55,label='Pressure [MPa]')
                polar=fig.add_subplot(1,2,2,projection='polar')
                edges=np.linspace(0,2*np.pi,r['nx']+1)
                radii=np.array([r['r_mean']-.5*r['gap'],r['r_mean']+.5*r['gap']])*1000
                im=polar.pcolormesh(edges,radii,last['reaction_rate'][:,r['probe_index']][None,:],cmap='inferno',**rate_options)
                polar.set_ylim(0,r['r_outer']*1000)
                polar.set_title('Synthetic head-end ring: radially repeated rate\nNot camera luminosity; no cross-gap physics')
                fig.colorbar(im,ax=polar,shrink=.55,label='Reaction rate [1/s]')
                fig.suptitle(f"Wrapped 2D fields at {last['t']*1e6:g} µs; no radial evolution")
                fig.savefig(destination/'wrapped.png',dpi=120)
            finally: plt.close(fig)

        fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
        try:
            ts=data['ring_times']
            for ax,values,title in zip(axes,[data['ring_pressure']/1e6,data['ring_rate']],['Pressure [MPa]','Reaction rate [1/s]']):
                if len(ts)>=2:
                    x=(np.arange(r['nx'])+.5)*r['dx']*1000
                    opts=dict(norm=pnorm,cmap='magma') if title.startswith('Pressure') else dict(cmap='inferno',**rate_options)
                    im=ax.pcolormesh(x,ts*1e6,values,shading='nearest',**opts)
                    fig.colorbar(im,ax=ax)
                    ax.set_ylim(ts[0]*1e6,ts[-1]*1e6)
                else: ax.text(.5,.5,'Fewer than two saved fields in window',ha='center',transform=ax.transAxes)
                ax.set(xlabel='Circumferential x [mm]',ylabel='Time [µs]',title=title)
            fig.suptitle('Saved ring at z = %.4g mm; field sampling may miss fast fronts' % ((r['probe_index']+.5)*r['dy']*1000))
            fig.savefig(destination/'space_time.png',dpi=120)
        finally: plt.close(fig)

        fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
        try:
            rows=data['rows'];selected=[row for row in rows if start<=row['t']<=end]
            axes[0,0].plot([row['t']*1e6 for row in selected],[row.get('probe_pressure_Pa',np.nan)/1e3 for row in selected])
            axes[0,0].set(xlabel='Time [µs]',ylabel='Local pressure [kPa]')
            spec=report['pressure_spectrum']
            if spec['available']:
                axes[0,1].loglog(spec['frequency_Hz'][1:]/1000,np.maximum(spec['density_Pa2_per_Hz'][1:],1e-300))
                axes[0,1].set_title(f"Δf = {spec['frequency_bin_Hz']/1000:.3g} kHz; pressure peak only" +
                    ('\nFewer than 3 cycles: peak poorly constrained' if spec['peak_cycles_in_window']<3 else ''))
            else: axes[0,1].text(.5,.5,spec['reason'],ha='center',wrap=True,transform=axes[0,1].transAxes)
            axes[0,1].set(xlabel='Frequency [kHz]',ylabel='Hann PSD [Pa²/Hz]')
            valid=[s for s in report['pressure_spectrogram']['segments'] if s['available']]
            if valid:
                densities=np.concatenate([np.log10(np.maximum(s['density_Pa2_per_Hz'][1:],1e-300)) for s in valid])
                snorm=Normalize(float(densities.max())-8,float(densities.max()))
                for s in valid:
                    freq=s['frequency_Hz'][1:]/1000; center=np.mean(s['window_s'])*1e6
                    im=axes[1,0].scatter(np.full(len(freq),center),freq,c=np.log10(np.maximum(s['density_Pa2_per_Hz'][1:],1e-300)),s=8,cmap='magma',norm=snorm)
                fig.colorbar(im,ax=axes[1,0],label='log10 PSD [Pa²/Hz], common scale')
                axes[1,0].set_yscale('log')
            else: axes[1,0].text(.5,.5,'No resolved segment spectra',ha='center',transform=axes[1,0].transAxes)
            axes[1,0].set(xlabel='Segment center [µs]',ylabel='Frequency [kHz]',title='50% overlapping Hann windows; native sampling limits')
            station=report['pressure_stations'];ref=report['experimental_comparison']
            if station['available']:
                axes[1,1].plot(np.array(station['stations_m'])*1000,np.array(station['mean_Pa'])/1000,label='Model window')
            if ref['available']:
                axes[1,1].scatter(ref['stations_m']*1000,ref['experimental_mean_Pa']/1000,label='Mundt long-window reference',marker='x')
            else: axes[1,1].set_title('Experimental overlay unavailable: see report')
            if station['available'] or ref['available']: axes[1,1].legend(fontsize=8)
            axes[1,1].set(xlabel='Axial z [mm]',ylabel='Mean pressure [kPa]')
            fig.suptitle('Transient signal analysis; no automatic wave/mode classification')
            fig.savefig(destination/'signals.png',dpi=120)
        finally: plt.close(fig)

        fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained')
        try:
            selected=[row for row in data['rows'][1:] if start < row['t'] and row['t']-row['dt'] < end]
            tt=np.array([row['t'] for row in selected])*1e6
            axes[0,0].step(tt,[row.get('exit_numerical_force_N',np.nan) for row in selected],where='pre')
            axes[0,0].set(ylabel='Native annulus-exit contribution [N]',title='Not whole-engine thrust')
            torque=report['engine_torque']
            if torque['available']:
                axes[0,1].step(tt,[row.get('wall_engine_torque_Nm',np.nan) for row in selected],where='pre')
                axes[0,1].axhline(torque['mean_Nm'],ls='--',color='k',label='Selected-window mean');axes[0,1].legend()
            else: axes[0,1].text(.5,.5,'No modeled wall torque',ha='center',transform=axes[0,1].transAxes)
            axes[0,1].set(ylabel='Modeled engine torque [N m]',title='Mean-radius constant-Cf closure, when enabled')
            for key,label in [('mdot_in','Inlet'),('mdot_out','Outlet')]:
                axes[1,0].step(tt,[row.get(key,np.nan) for row in selected],where='pre',label=label)
            axes[1,0].legend();axes[1,0].set(ylabel='Native mass flow [kg/s]')
            budget=report['budgets']
            if budget['available']:
                residual=np.array([row['residual'] for row in selected])
                for i,label in enumerate(['Mass','θ momentum','z momentum','Energy','Reacted mass']):
                    axes[1,1].semilogy(tt,np.maximum(abs(residual[:,i])/budget['residual_scale'][i],1e-18),label=label)
                axes[1,1].legend(fontsize=7)
            axes[1,1].set(ylabel='Cumulative residual / window scale',title='Whole-run closure history; window closure in report')
            for ax in axes.flat: ax.set_xlabel('Time [µs]');ax.set_xlim(start*1e6,end*1e6);ax.grid(alpha=.2)
            fig.savefig(destination/'loads.png',dpi=120)
        finally: plt.close(fig)
        roll=report['roll_response']
        if roll['available']:
            fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
            try:
                axes[0].plot(roll['times_s']*1e6,roll['angular_velocity_rad_s']);axes[0].set_ylabel('Illustrative roll rate [rad/s]')
                axes[1].plot(roll['times_s']*1e6,roll['angle_rad']);axes[1].set_ylabel('Relative angle [rad]')
                for ax in axes: ax.set_xlabel('Time [µs]')
                fig.suptitle('Specified constant inertia, zero initial roll; no damping/control/stability prediction')
                fig.savefig(destination/'roll.png',dpi=120)
            finally: plt.close(fig)
        write_data(data,destination,comparison)
        images=['signals.png','loads.png','space_time.png']+(['wrapped.png'] if last is not None else [])+(['roll.png'] if roll['available'] else [])
        body=''.join(f'<figure><img src="{name}" alt="{name}" loading="lazy"></figure>' for name in images)
        playback=''
        if frame_items:
            playback='''<button id="play">Play / pause</button><input id="frame" type="range" min="0" value="0"><span id="stamp"></span><img id="field" alt="Saved 2D pressure and reaction fields">
<script>const frames=FRAME_DATA;const slider=document.getElementById('frame');slider.max=frames.length-1;
function show(){const f=frames[Number(slider.value)];document.getElementById('field').src=f.file;document.getElementById('stamp').textContent=` ${f.time_us.toPrecision(6)} µs (step ${f.step})`;}
slider.oninput=show;let timer=null;document.getElementById('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;}else{timer=setInterval(()=>{slider.value=(Number(slider.value)+1)%frames.length;show();},500);}};show();</script>'''.replace('FRAME_DATA',json.dumps(frame_items))
        else: playback='<p>No field snapshots within this window. Native history reports remain available.</p>'
        page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reduced 2D RDE report</title>
<style>body{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#172230;background:#fafafa}img{width:100%;height:auto}figure{margin:1.5rem 0}input{width:45%}button{padding:.5rem}aside{padding:1rem;background:#fff0d6}a{color:#1250a0}</style>
<h1>Reduced 2D RDE saved-data report</h1>'''
        page+=f'<p>{html.escape(summary.get("run_mode","engine_intervals"))}; selected window {start*1e6:g}–{end*1e6:g} µs. Committed step {summary["steps"]}.</p>'
        page+='<aside>RDE-001 remains unresolved on main. These outputs do not establish sustained detonation or validated engine performance. Radial momentum, centrifugal pressure split, curvature loss and heat loss are absent. Wrapped/head-end views are synthetic 2D displays.</aside>'
        page+='<p><a href="report.md">Report</a> · <a href="report.json">JSON and provenance</a> · <a href="history.csv">History CSV</a>'
        if comparison: page+=' · <a href="comparison.csv">Sensitivity comparison CSV</a>'
        page+='</p><p>Playback uses equal display intervals; actual saved timestamps are shown. Re-run this read-only command into a new output directory to refresh a running case.</p>'+playback+body+'</html>'
        (destination/'index.html').write_text(page)
        (destination/'COMPLETE').write_text('Saved-data workflow completed. Physical validation remains separate.\n')
    except Exception:
        (destination/'INCOMPLETE').write_text('Workflow output failed; do not treat this directory as complete. Use a new output path after correcting the error.\n')
        raise
    return report


def watch_workflow(directory, destination, start=0., end=None, frames=4, refresh_seconds=30., max_updates=None):
    """Refresh only when a new checkpoint is committed; Ctrl-C stops the viewer.

    Each rendering has a new immutable subdirectory. Root HTML refreshes its
    iframe; no network service, job scheduler or CFD process is created.
    """
    import math
    import time
    from window_report import load_native_prefix
    if not math.isfinite(refresh_seconds) or refresh_seconds<1:
        raise ValueError('refresh interval must be finite and at least one second')
    if not math.isfinite(start) or start<0 or (end is not None and (not math.isfinite(end) or end<=start)):
        raise ValueError('invalid watch time window')
    if not isinstance(frames,int) or not 1<=frames<=60:
        raise ValueError('preview frame count must lie in [1,60]')
    if max_updates is not None and (not isinstance(max_updates,int) or max_updates<1):
        raise ValueError('max_updates must be a positive integer')
    destination=Path(destination)
    if destination.resolve().is_relative_to(Path(directory).resolve()):
        raise ValueError('watch output must be outside the saved run')
    destination.mkdir(parents=True,exist_ok=False)
    previous=None; updates=0; read_failures=0
    terminal={'completed_limit','failed','interrupted'}
    while True:
        try:
            _,summary,_,_=load_native_prefix(directory)
            read_failures=0
        except (ValueError,OSError) as error:
            # A changing checkpoint/summary pair is expected during active output.
            # Surface the reason; do not repeatedly render an unverified prefix.
            read_failures+=1
            if read_failures>=3:
                raise ValueError(f'no coherent checkpoint after three reads: {error}') from error
            print(f'Waiting for a coherent checkpoint: {error}',flush=True)
            time.sleep(refresh_seconds)
            continue
        finish=summary['t'] if end is None else min(end,summary['t'])
        identity=(summary['steps'],summary['status'])
        if finish>start and identity!=previous:
            name=f'update_{updates:04d}_step_{summary["steps"]:09d}'
            plot_workflow(directory,destination/name,start,finish,frames=frames)
            page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="{refresh_seconds:g}"><title>RDE checkpoint preview</title><p>Read-only checkpoint preview: step {summary['steps']}, {summary['t']*1e6:g} µs; status {summary['status']}. CFD is not controlled by this page.</p><iframe title="Latest verified report" src="{name}/index.html" style="width:100%;height:90vh;border:0"></iframe></html>'''
            temporary=destination/'.index.tmp';temporary.write_text(page);temporary.replace(destination/'index.html')
            updates+=1;previous=identity
            print(f'Preview {updates}: committed step {summary["steps"]}, {finish*1e6:g} µs',flush=True)
        if (summary['status'] in terminal or (end is not None and summary['t']>=end)
                or (max_updates is not None and updates>=max_updates)):
            if not updates:
                raise ValueError('run stopped without a committed positive-duration window after start')
            return dict(updates=updates,status=summary['status'],last_step=summary['steps'])
        time.sleep(refresh_seconds)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--layer-comparison',type=Path,nargs='+',help='two or more saved layer controls, identical chemistry')
    source.add_argument('--controlled',type=Path,help='saved controlled 2D diagnostic')
    source.add_argument('--experiments',type=Path,help='saved contact or 1D refinement suite')
    source.add_argument('--reference',type=Path,help='saved physical/surrogate reference')
    source.add_argument('--calibration',type=Path,help='saved calibration JSON')
    source.add_argument('--workflow',type=Path,help='complete read-only native-window report and streaming field viewer')
    source.add_argument('--run',type=Path,help='saved engine run directory')
    source.add_argument('--tube',type=Path,help='saved 1D experiment directory')
    source.add_argument('--coupling',type=Path,help='saved engine run for full-height reaction and candidate-track diagnostics')
    parser.add_argument('--compare-run',type=Path,help='second saved run; requires --coupling')
    parser.add_argument('--heights-mm',type=float,nargs='+',default=[1.,4.,8.,16.],help='ring heights for --coupling')
    parser.add_argument('--follow',action='store_true',help='refresh the workflow preview at new committed checkpoints')
    parser.add_argument('--refresh-seconds',type=float,default=30.,help='minimum polling interval for --follow')
    parser.add_argument('--max-updates',type=int,help='optional cap on --follow rendered updates')
    parser.add_argument('--start-us',type=float,help='workflow window start')
    parser.add_argument('--end-us',type=float,help='workflow window end')
    parser.add_argument('--frames',type=int,default=12,help='workflow preview frames, 1–60')
    parser.add_argument('--segment-us',type=float,help='workflow spectrogram segment duration')
    parser.add_argument('--inertia-kg-m2',type=float,help='optional constant inertia for illustrative roll response')
    parser.add_argument('--compare-runs',type=Path,nargs='+',help='additional saved runs for same-window sensitivity table')
    parser.add_argument('--out',type=Path,required=True,help='new PNG for calibration; new directory for run/tube plots')
    args=parser.parse_args(argv)
    if not args.follow and (args.max_updates is not None or args.refresh_seconds!=30.):
        parser.error('--max-updates/--refresh-seconds require --follow')
    if args.workflow:
        if args.compare_run:
            parser.error('--compare-run requires --coupling; use --compare-runs for workflow')
        if args.start_us is None or (args.end_us is None and not args.follow):
            parser.error('--workflow requires --start-us and --end-us (end may be omitted with --follow)')
        try:
            if args.follow:
                if args.inertia_kg_m2 is not None or args.segment_us is not None or args.compare_runs:
                    parser.error('--follow uses default signal windows and no inertia/comparison; use a final static report for these')
                watch_workflow(args.workflow,args.out,args.start_us*1e-6,
                    None if args.end_us is None else args.end_us*1e-6,args.frames,args.refresh_seconds,args.max_updates)
                return
            plot_workflow(args.workflow,args.out,args.start_us*1e-6,args.end_us*1e-6,
                args.frames,None if args.segment_us is None else args.segment_us*1e-6,
                args.inertia_kg_m2,args.compare_runs)
        except (ValueError,TypeError,KeyError,OSError) as error:
            parser.exit(2,f'Workflow stopped: {error}\n')
        return
    if args.follow or args.max_updates is not None:
        parser.error('--follow and --max-updates require --workflow --follow')
    if any(v is not None for v in (args.start_us,args.end_us,args.segment_us,args.inertia_kg_m2,args.compare_runs)):
        parser.error('window/spectrum/inertia/comparison options require --workflow')
    if args.out.exists():
        parser.error('output exists; choose a new destination')
    if args.compare_run and not args.coupling:
        parser.error('--compare-run requires --coupling')
    if args.layer_comparison:
        plot_layer_comparison(args.layer_comparison,args.out)
    elif args.controlled:
        plot_controlled(args.controlled,args.out)
    elif args.experiments:
        plot_experiments(args.experiments,args.out)
    elif args.reference:
        plot_reference(args.reference,args.out)
    elif args.coupling:
        plot_coupling(args.coupling,args.out,args.compare_run,args.heights_mm)
    elif args.run:
        plot_run(args.run,args.out)
    elif args.tube:
        plot_tube(args.tube,args.out)
    else:
        from calibrate import znd_profile
        with args.calibration.open() as stream:
            calibration=json.load(stream)
        plot_znd(znd_profile(calibration),calibration,args.out)
    print(args.out)


if __name__=='__main__':
    main()
