"""Saved-data end-on view and gas-convergence check; run from repository root."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() or a.out.resolve().is_relative_to(a.run.resolve()):
        raise ValueError('output must be a new directory outside the native run')
    sys.path.insert(0,str(Path.cwd()/'rde_sim_starter'))
    from contracts import iter_fields
    from window_report import load_native_prefix
    from animate import playback_durations
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from PIL import Image
    inputs,summary,_,prov=load_native_prefix(a.run);r=inputs['resolved'];c=inputs['calibration']
    x=(np.arange(r['nx'])+.5)*r['dx'];z=(np.arange(r['ny'])+.5)*r['dy']
    js=[int(np.argmin(abs(z-h/1000))) for h in [.752,3.76,7.77]]
    center=(x>=.110)&(x<=.160)
    records=[];profiles=[];peak_heat=0.;checks=[];selected={}
    for f in iter_fields(a.run,inputs,summary['steps']):
        heat=f['density'].astype(float)*c['q']*f['reaction_rate'].astype(float)
        projected=heat.sum(axis=1)*r['dy']
        direct=float(heat.sum()*r['dx']*r['dy']*r['gap'])
        projected_total=float(projected.sum()*r['dx']*r['gap'])
        rel=abs(direct-projected_total)/max(abs(direct),1e-30)
        assert rel<1e-12
        checks.append(rel);peak_heat=max(peak_heat,float(projected.max()))
        up=f['u_theta'][:,js].astype(float).T
        item=dict(step=f['step'],time_s=f['t'],
            sha256=hashlib.sha256((a.run/'fields'/f"step_{f['step']:09d}.npz").read_bytes()).hexdigest(),
            central_region_max_abs_u_theta_mps=float(abs(f['u_theta'][center]).max()),
            central_rings=[dict(z_mm=float(z[j]*1000),
                u_theta_min_mps=float(f['u_theta'][center,j].min()),u_theta_max_mps=float(f['u_theta'][center,j].max()),
                p_min_Pa=float(f['pressure'][center,j].min()),p_max_Pa=float(f['pressure'][center,j].max())) for j in js])
        records.append(item);profiles.append((f['t'],f['pressure'][:,js[0]],f['reaction_rate'][:,js[0]],projected,up))
        for target in [10,20,40,80,110]:
            if abs(f['t']*1e6-target)<.01:selected[target]={k:f[k].copy() for k in ['pressure','u_theta','u_z']}
    a.out.mkdir(parents=True)
    norms=[LogNorm(.1,22),LogNorm(1,1e6),LogNorm(peak_heat*1e-4,peak_heat)]
    cmaps=[plt.get_cmap(n).with_extremes(under='black') for n in ['magma','inferno','gray']]
    fig=plt.figure(figsize=(12,5.4),dpi=100)
    fig.subplots_adjust(left=.035,right=.965,top=.77,bottom=.25,wspace=.32)
    stamp=fig.text(.5,.95,'',ha='center',fontsize=16,weight='bold')
    fig.text(.5,.89,'End-on orientation: looking from the outlet toward the injector',ha='center',fontsize=12)
    names=['Pressure at z = 0.752 mm','Reaction at z = 0.752 mm','Heat release integrated along z']
    units=['MPa','1/s (values below 1 are black)','W/m² (not optical brightness)']
    theta=np.linspace(0,2*np.pi,r['nx']+1);rad=np.array([inputs['config']['geometry']['r_inner_mm'],inputs['config']['geometry']['r_outer_mm']])
    meshes=[]
    for k in range(3):
        ax=fig.add_subplot(1,3,k+1,projection='polar');ax.grid(False);ax.set_ylim(0,rad[-1]);ax.set_yticks([])
        ax.set_facecolor('black');ax.spines['polar'].set_visible(False);ax.set_xticks(np.arange(4)*np.pi/2)
        ax.set_xticklabels(['0°','90°','180°','270°']);ax.set_title(names[k],pad=17,fontsize=11)
        mesh=ax.pcolormesh(theta,rad,np.ones((1,r['nx'])),norm=norms[k],cmap=cmaps[k],shading='flat');meshes.append(mesh)
        cb=fig.colorbar(mesh,ax=ax,orientation='horizontal',pad=.16,fraction=.06);cb.set_label(units[k],fontsize=10);cb.ax.tick_params(labelsize=8)
    fig.text(.5,.12,'The annulus has no resolved radial detail. Colors show computed fields, not camera light.',ha='center',fontsize=11)
    fig.text(.5,.065,'Fixed scales • every saved frame • no imposed rotation • endpoint is a time limit, not fuel exhaustion',ha='center',fontsize=10)
    pictures=[]
    for idx,(t,pressure,rate,projected,_) in enumerate(profiles):
        for mesh,v in zip(meshes,[pressure/1e6,np.maximum(rate,1e-30),np.maximum(projected,1e-30)]):mesh.set_array(v[None,:])
        stamp.set_text(f'OUR SAVED SIMULATION  |  t = {t*1e6:.3f} µs')
        fig.canvas.draw();im=Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert('RGB');pictures.append(im)
        if idx in [0,10,20,55,len(profiles)-1]:im.save(a.out/f'end_on_{idx:03d}.png')
    durations=playback_durations([v[0] for v in profiles])
    pictures[0].save(a.out/'end_on.gif',save_all=True,append_images=pictures[1:],duration=durations,disposal=2,optimize=False)
    plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(12,6),layout='constrained')
    velocity_limit=100*np.ceil(max(float(abs(selected[t]['u_theta'][:,js]).max()) for t in [40,110])/100)
    for col,t in enumerate([40,110]):
        f=selected[t]
        im=axs[0,col].pcolormesh(x*1000,z*1000,f['pressure'].T/1e6,norm=LogNorm(.1,22),cmap='magma',shading='nearest')
        ix=np.arange(8,r['nx'],20);iz=np.array([1,7,15,30,60,100,130]);X,Z=np.meshgrid(x[ix]*1000,z[iz]*1000,indexing='ij')
        qu=axs[0,col].quiver(X,Z,f['u_theta'][np.ix_(ix,iz)],f['u_z'][np.ix_(ix,iz)],color='cyan',angles='xy',scale_units='xy',scale=100,width=.003)
        axs[0,col].quiverkey(qu,.76,.94,1000,'gas: 1000 m/s',labelpos='W',coordinates='axes',color='cyan',labelcolor='white')
        axs[0,col].set(title=f'{t} µs: pressure + gas velocity',xlabel='Circumferential x [mm]',ylabel='Axial z [mm]',aspect='equal')
        for j in js:axs[1,col].plot(x*1000,f['u_theta'][:,j],label=f'z={z[j]*1000:.3f} mm')
        for ax in axs[:,col]:ax.axvspan(110,160,facecolor='gray',alpha=.17)
        axs[1,col].axhline(0,color='.5',lw=.5);axs[1,col].set(xlim=(0,r['width']*1000),ylim=(-velocity_limit,velocity_limit),xlabel='Circumferential x [mm]',ylabel='Gas u_theta [m/s]');axs[1,col].legend(fontsize=8)
    fig.colorbar(im,ax=axs[0,:],label='Pressure [MPa]')
    fig.suptitle('Gas velocity at 40 and 110 us | arrows do not track fronts | gray band: x = 110–160 mm')
    fig.savefig(a.out/'gas_motion.png',dpi=150);plt.close(fig)
    with Image.open(a.out/'end_on.gif') as gif:
        assert gif.n_frames==len(records)
        assert 'loop' not in gif.info
        saved_durations=[]
        for j in range(gif.n_frames):gif.seek(j);saved_durations.append(gif.info['duration'])
        assert saved_durations==durations
    manifest=dict(provenance=prov,frames=records,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        radial_extent_mm=rad.tolist(),ring_z_mm=float(z[js[0]]*1000),
        projected_heat_definition='sum(rho*q*reaction_rate*dz) [W/m²], chemical power per cross-sectional area, not radiation',
        peak_projected_heat_W_m2=peak_heat,central_region_x_mm=[110,160],
        maximum_projection_integral_relative_error=max(checks),durations_ms=durations,
        qualifications=['No radial dimension resolved; colors are constant across the displayed gap.',
            'No synthetic camera model, optical emission chemistry or line-of-sight absorption.',
            'Arrows are instantaneous gas velocities, not front tracks; components use axis data units.',
            'A central strip cannot exclude all other injector, product-layer or boundary interactions.'])
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(f'Created {len(records)}-frame end-on GIF; projection and encoded timing checks passed.')


if __name__=='__main__':main()
