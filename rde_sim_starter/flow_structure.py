"""Saved-field schlieren, compression and shear diagnostics, not a mode classifier."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from animate import playback_durations, surface_blocks
from contracts import iter_fields
from window_report import load_native_prefix, reduce_window, _json_default

# Display gates, fixed across frames. They are not validated shock/slip-line criteria.
GATES = dict(pressure_jump=.08, compression=.04, contact_pressure_jump=.025,
             contact_entropy_jump=.04, contact_shear=.02, product_progress=.9,
             heat_fraction_of_global_peak=.05)


def gradient(a, dx, dz):
    """Centered periodic theta derivative, one-sided axial endpoint derivatives."""
    a=np.asarray(a,dtype=float)
    if a.ndim != 2 or min(a.shape)<2 or not np.isfinite(a).all():
        raise ValueError('finite 2D field with at least two cells per axis required')
    if not np.isfinite([dx,dz]).all() or min(dx,dz)<=0:
        raise ValueError('positive finite grid spacing required')
    return (np.roll(a,-1,axis=0)-np.roll(a,1,axis=0))/(2*dx), np.gradient(a,dz,axis=1)


def interface_cells(progress):
    """Cells abutting the 0.5 progress contour; periodic only in theta."""
    side=np.asarray(progress)>=.5
    result=side!=np.roll(side,-1,axis=0)
    result[:,:-1] |= side[:,:-1]!=side[:,1:]
    return result


def structure_fields(frame, resolved, calibration, plenum_pressure):
    p,rho,u,v,xi,rate=(np.asarray(frame[k],dtype=float) for k in
        ('pressure','density','u_theta','u_z','progress','reaction_rate'))
    if (any(a.shape!=p.shape or not np.isfinite(a).all() for a in (rho,u,v,xi,rate))
            or np.any(p<=0) or np.any(rho<=0) or np.any(rate<0)):
        raise ValueError('valid matching primitive fields required')
    dx,dz=resolved['dx'],resolved['dy'];h=min(dx,dz);gamma=calibration['gamma']
    if not np.isfinite([gamma,calibration['q'],plenum_pressure]).all() or gamma<=1 or min(calibration['q'],plenum_pressure)<=0:
        raise ValueError('positive thermochemical coefficients and plenum pressure required')
    drx,drz=gradient(rho,dx,dz);dpx,dpz=gradient(np.log(p),dx,dz)
    ux,uz=gradient(u,dx,dz);vx,vz=gradient(v,dx,dz)
    sound=np.sqrt(gamma*p/rho)
    divergence=ux+vz;vorticity=vx-uz
    # Dimensionless entropy difference s/cv; reference constants vanish on differentiation.
    entropy=np.log(p/calibration['p1'])-gamma*np.log(rho/(calibration['p1']/(calibration['R']*calibration['T1'])))
    sx,sz=gradient(entropy,dx,dz)
    pressure_jump=h*np.hypot(dpx,dpz);entropy_jump=h*np.hypot(sx,sz)
    compression=np.maximum(-divergence,0)*h/sound
    shock=(pressure_jump>=GATES['pressure_jump']) & (compression>=GATES['compression'])
    contact=(xi>=GATES['product_progress']) & (pressure_jump<GATES['contact_pressure_jump']) & (entropy_jump>=GATES['contact_entropy_jump']) & (np.abs(vorticity)*h/sound>=GATES['contact_shear'])
    return dict(density_gradient=np.hypot(drx,drz),pressure_jump=pressure_jump,
        divergence=divergence,vorticity=vorticity,entropy=entropy,entropy_jump=entropy_jump,
        shock_candidate=shock,product_shear_contact_candidate=contact,
        interface=interface_cells(xi),fresh=xi<.1,heat=rho*calibration['q']*rate,
        injector_blocked=p[:,0]>=plenum_pressure)


def composite(fields, gradient_scale, heat_threshold):
    """Fixed transfer function; colors indicate observables, not named wave identities."""
    edge=1-np.exp(-4*fields['density_gradient']/gradient_scale)
    rgb=np.repeat((1-.85*edge)[...,None],3,axis=2)
    for mask,color,alpha in [(fields['fresh'],(.45,.7,1.),.25),
            (fields['heat']>heat_threshold,(1.,.6,0.),.65),
            (fields['shock_candidate'],(.9,.08,.06),.9),
            (fields['product_shear_contact_candidate'],(.75,0.,.8),.9),
            (fields['interface'],(0.,.7,.8),1.)]:
        rgb[mask]=(1-alpha)*rgb[mask]+alpha*np.asarray(color)
    return np.clip(rgb,0,1)


def render_structures(directory,destination,start=0.,end=None,seconds=14.):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm
    from PIL import Image
    source,out=Path(directory),Path(destination)
    if out.resolve().is_relative_to(source.resolve()):raise ValueError('output must be outside native run')
    if out.exists():raise FileExistsError(out)
    inputs,summary,rows,provenance=load_native_prefix(source)
    end=summary['t'] if end is None else end
    reduce_window(inputs,summary,rows,start,end) # verify window, native timeline and budgets
    r,c=inputs['resolved'],inputs['calibration'];p0=inputs['config']['operating_point']['p_plenum_kPa']*1000
    records=[];gmax=0.;heatmax=0.;omax=0.;dmax=0.
    for f in iter_fields(source,inputs,summary['steps']):
        if f['t']>summary['t']:raise ValueError('snapshot exceeds committed time')
        if not start<=f['t']<=end:continue
        a=structure_fields(f,r,c,p0)
        # A fixed global 99th-percentile bound exposes weak waves without frame normalization.
        gmax=max(gmax,float(np.quantile(a['density_gradient'],.99)))
        heatmax=max(heatmax,float(a['heat'].max()));omax=max(omax,float(np.abs(a['vorticity']).max()))
        dmax=max(dmax,float(np.abs(a['divergence']).max()))
        records.append(dict(step=f['step'],time_s=f['t'],
            sha256=hashlib.sha256((source/'fields'/f"step_{f['step']:09d}.npz").read_bytes()).hexdigest(),
            shock_candidate_cells=int(a['shock_candidate'].sum()),
            product_shear_contact_candidate_cells=int(a['product_shear_contact_candidate'].sum()),
            injector_blocked_fraction=float(a['injector_blocked'].mean()),
            max_heat_W_m3=float(a['heat'].max()),max_vorticity_per_s=float(np.abs(a['vorticity']).max())))
    durations=playback_durations([f['time_s'] for f in records],seconds)
    gmax=max(gmax,1e-12);heat_threshold=max(heatmax*GATES['heat_fraction_of_global_peak'],1e-30)
    onorm=SymLogNorm(linthresh=max(omax*.001,1.),vmin=-max(omax,1.),vmax=max(omax,1.))
    dnorm=SymLogNorm(linthresh=max(dmax*.001,1.),vmin=-max(dmax,1.),vmax=max(dmax,1.))
    selected={f['step'] for f in records}
    manifest=dict(schema_version=1,provenance=provenance,frames=records,durations_ms=durations,
        renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        gates=GATES,gradient_scale_kg_m4=gmax,heat_threshold_W_m3=heat_threshold,
        vorticity_limit_per_s=omax,divergence_limit_per_s=dmax,
        definitions=dict(schlieren='1-exp(-4*abs(grad rho)/fixed_scale), numerical gradient image, not optical ray tracing',
            pressure_jump='min(dx,dz)*abs(grad ln(p))',compression='max(-div(u),0)*min(dx,dz)/sound_speed',
            entropy='ln(p/p1)-gamma*ln(rho/rho1) = entropy difference / cv for this fixed-gamma model',
            vorticity='du_z/dx - du_theta/dz',interface='progress=0.5, fresh/product boundary, not paper slip line C',
            blocked='saved instantaneous injector-adjacent pressure >= fixed plenum pressure; not step-integrated flux'),
        qualifications=['Diagnostic thresholds are display gates, not Rankine-Hugoniot or material-surface verification.',
            'Product shear/contact candidates do not distinguish newly formed from older products: no age tracer is saved.',
            'Detonation, oblique shock, secondary shock and slip-line identities are not automatically assigned.',
            'No interpolation, imposed front speed, invented turbulent roll-ups or extra CFD. All saved frames retained.',
            'Wrapped composite uses area-averaged RGB display faces; apparent overlap there is not coupling evidence.',
            'No resolved radial dimension; both animations show the same 2D simulation.'],
        paper_reference='Mundt2023.pdf, Fig.1.1 printed p.1 and Fig.1.10 printed p.13')
    out.mkdir(parents=True,exist_ok=False)
    legend=[('BLACK','Density-gradient edges'),('RED','Compression-front candidates'),('ORANGE','Strong reaction zones'),('CYAN','Fresh/product boundary'),('MAGENTA','Product shear/contact candidates'),('PALE BLUE','Mostly fresh mixture (progress < 0.1)')]
    colors=['.15','#d81d17','#dc8600','#008e9e','#b100bf','#4485bc']
    try:
        for wrapped,name in [(False,'unwrapped.gif'),(True,'wrapped.gif')]:
            fig=plt.figure(figsize=(13,8.8),dpi=90)
            stamp=fig.text(.055,.96,'',fontsize=17,weight='bold')
            fig.text(.055,.925,'Flow structures from saved CFD fields | fixed scales | no assumed sustained wave',fontsize=11)
            for k,((label,detail),color) in enumerate(zip(legend,colors)):
                y=.85-k*.07
                fig.text(.8,y,label,color=color,fontsize=10,weight='bold')
                fig.text(.8,y-.023,detail.replace('Product shear/contact candidates','Product shear/contact\ncandidates').replace('Mostly fresh mixture (progress < 0.1)','Mostly fresh mixture'),fontsize=9,va='top')
            fig.text(.8,.41,'PAPER FIGURE KEY\nA: detonation not established\nB / D: inspect red fronts\nC: inspect shear + contacts\nE: cyan/orange interface\nF: inlet strip: green=open\n    black=blocked\nG: pale-blue fresh gas',fontsize=9,linespacing=1.6,va='top')
            stats=fig.text(.8,.12,'',fontsize=9,linespacing=1.5)
            fig.text(.055,.035,'Slip line C separates new/old products. Cyan is a different boundary; magenta is only a candidate.',fontsize=10)
            artists=[];pictures=[]
            width,length=r['width']*1000,r['length']*1000
            if wrapped:
                axes=[]
                for k in range(2):
                    ax=fig.add_axes([.025+.38*k,.23,.38,.62],projection='3d');axes.append(ax)
                    radius=r['r_mean']*1000
                    ax.view_init(elev=23,azim=-65+180*k)
                    ax.set(xlim=(-radius,radius),ylim=(-radius,radius),zlim=(0,length),
                        xlabel='X [mm]',ylabel='Y [mm]',zlabel='Axial z [mm]',title='Front' if k==0 else 'Opposite side')
                    ax.set_box_aspect((2*radius,2*radius,length));ax.tick_params(labelsize=8)
                fig.text(.07,.16,'Same 2D field wrapped onto mean radius; fixed opposite views expose both sides.',fontsize=10)
                fig.text(.07,.12,'Injector at z=0. Circumferential lines and bands follow the saved flow, not a rotating camera.',fontsize=9)
            else:
                main=fig.add_axes([.055,.48,.69,.39])
                im=main.imshow(np.ones((r['ny'],r['nx'],3)),origin='lower',extent=(0,width,0,length),aspect='auto',interpolation='nearest')
                main.set(xlabel='Circumferential distance [mm] (periodic ends join)',ylabel='Axial z [mm]')
                main.text(.02,.98,'Numerical schlieren + flow-structure overlays',va='top',transform=main.transAxes,fontsize=10,bbox=dict(fc='white',alpha=.85,ec='none'))
                block=main.imshow(np.zeros((1,r['nx'],4)),origin='lower',extent=(0,width,-3,0),aspect='auto',interpolation='nearest')
                main.set_ylim(-3,length)
                shear=fig.add_axes([.055,.13,.28,.24]);dilat=fig.add_axes([.45,.13,.28,.24])
                om=shear.imshow(np.zeros((r['ny'],r['nx'])),origin='lower',extent=(0,width,0,length),aspect='auto',norm=onorm,cmap='PuOr_r')
                dv=dilat.imshow(np.zeros((r['ny'],r['nx'])),origin='lower',extent=(0,width,0,length),aspect='auto',norm=dnorm,cmap='RdBu_r')
                for ax,title in [(shear,'Shear diagnostic: vorticity'),(dilat,'Compression (-) / expansion (+)')]:
                    ax.set(xlabel='Circumferential distance [mm]',ylabel='Axial z [mm]' if ax is shear else '',title=title)
                    ax.tick_params(labelsize=8)
                fig.colorbar(om,ax=shear,fraction=.035,pad=.025,label='1/s, symmetric log')
                fig.colorbar(dv,ax=dilat,fraction=.035,pad=.025,label='1/s, symmetric log')
            try:
                for n,f in enumerate(iter_fields(source,inputs,summary['steps'],selected_steps=selected)):
                    a=structure_fields(f,r,c,p0);rgb=composite(a,gmax,heat_threshold)
                    stamp.set_text(f"{'Wrapped' if wrapped else 'Unwrapped'} wave structure | t = {f['t']*1e6:.3f} us | {n+1}/{len(records)}")
                    stats.set_text(f"Blocked inlet: {a['injector_blocked'].mean():.1%}\nPeak heat: {a['heat'].max():.2e} W/m3\n"+('END OF SAVED WINDOW' if n==len(records)-1 else 'Time shown is simulation time.'))
                    if wrapped:
                        for old in artists:old.remove()
                        artists=[]
                        xe,ze,red=surface_blocks(rgb[:,:,0]);_,_,green=surface_blocks(rgb[:,:,1]);_,_,blue=surface_blocks(rgb[:,:,2])
                        face=np.stack([red,green,blue],axis=-1)
                        th,zz=np.meshgrid(xe*r['dx']/r['r_mean'],ze*r['dy']*1000,indexing='ij')
                        for ax in axes:
                            artists.append(ax.plot_surface(radius*np.cos(th),radius*np.sin(th),zz,facecolors=face,
                                rstride=1,cstride=1,shade=False,linewidth=0,antialiased=False))
                            # Native blocking cells shown as injector-ring segments, not an invented jet array.
                            for flag,color in [(False,'#299e64'),(True,'black')]:
                                ids=np.flatnonzero(a['injector_blocked']==flag);theta=(ids+.5)*r['dx']/r['r_mean']
                                artists.append(ax.scatter(radius*np.cos(theta),radius*np.sin(theta),np.zeros(len(ids)),s=2,c=color))
                    else:
                        im.set_data(rgb.transpose(1,0,2));om.set_data(a['vorticity'].T);dv.set_data(a['divergence'].T)
                        stripe=np.zeros((1,r['nx'],4));stripe[0,:,:3]=(.16,.62,.39);stripe[:,:,3]=1
                        stripe[0,a['injector_blocked'],:3]=0;block.set_data(stripe)
                    fig.canvas.draw();pixels=np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy()
                    pictures.append(Image.fromarray(pixels).quantize(colors=256))
                    if n in {0,min(10,len(records)-1),min(20,len(records)-1),len(records)//2,len(records)-1}:
                        Image.fromarray(pixels).save(out/f'{Path(name).stem}_{n:03d}.png')
                pictures[0].save(out/name,save_all=True,append_images=pictures[1:],duration=durations,disposal=2,optimize=False)
                with Image.open(out/name) as gif:
                    encoded=[]
                    for n in range(gif.n_frames):gif.seek(n);encoded.append(gif.info['duration'])
                    if encoded!=durations:raise ValueError('GIF encoder changed frame timing/count')
                manifest[name]=dict(frames=len(pictures),sha256=hashlib.sha256((out/name).read_bytes()).hexdigest())
            finally:
                plt.close(fig)
                for pic in pictures:pic.close()
        (out/'manifest.json').write_text(json.dumps(manifest,default=_json_default,indent=2,allow_nan=False)+'\n')
        (out/'COMPLETE').write_text('Saved flow-structure movies complete; features are qualified diagnostics.\n')
    except BaseException:
        (out/'INCOMPLETE').write_text('Incomplete export; use a new output directory.\n');raise
    return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--start-us',type=float,default=0.);p.add_argument('--end-us',type=float)
    p.add_argument('--seconds',type=float,default=14.)
    args=p.parse_args(argv)
    render_structures(args.run,args.out,args.start_us*1e-6,None if args.end_us is None else args.end_us*1e-6,args.seconds)
    print(args.out)


if __name__=='__main__':main()
