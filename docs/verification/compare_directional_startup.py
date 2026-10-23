"""Compare native startup protocols through 40 us, without modifying either run.
Run from repo root: .venv/bin/python docs/verification/compare_directional_startup.py
"""
import hashlib
import io
import json
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'rde_sim_starter'))
from contracts import iter_fields
from window_report import load_native_prefix,reduce_window,_json_default
from coupling import periodic_peaks


def main():
    out=ROOT/'docs/verification/directional_startup_comparison'
    if out.exists():raise ValueError('refusing existing report')
    data=[]
    for name,folder in [('Non-directional hot patch','radial_active'),('Directional +theta profile','directional_startup_40us')]:
        path=ROOT/'rde_sim_starter/runs'/folder
        inputs,summary,history,provenance=load_native_prefix(path)
        r=inputs['resolved'];c=inputs['calibration']
        frames=[f for f in iter_fields(path,inputs,summary['steps']) if f['t']<=40e-6+1e-14]
        if not frames or abs(frames[-1]['t']-40e-6)>1e-13:raise ValueError('40 us field required')
        z=(np.arange(r['ny'])+.5)*r['dy'];x=(np.arange(r['nx'])+.5)*r['dx']
        js=[int(np.argmin(abs(z-h*.001))) for h in (.75,3.8,8.)]
        metrics=[];hashes=[]
        for f in frames:
            rings=[]
            for j in js:
                p=f['pressure'][:,j];rate=f['reaction_rate'][:,j]
                peaks=[]
                for k in periodic_peaks(p,2*c['p1'],.25*c['p1'],2):
                    d=abs((x-x[k]+r['width']/2)%r['width']-r['width']/2)
                    peaks.append(dict(x_mm=float(x[k]*1e3),pressure_MPa=float(p[k]/1e6),
                        nearby_rate_per_s={str(mm):float(rate[d<=mm*.001].max()) for mm in (2,4,8)}))
                rings.append(dict(z_mm=float(z[j]*1e3),max_rate_per_s=float(rate.max()),peaks=peaks))
            metrics.append(dict(time_us=f['t']*1e6,rings=rings))
            file=path/'fields'/f"step_{f['step']:09d}.npz"
            hashes.append(dict(step=f['step'],sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        initial=history[0]['inventory']
        record=dict(name=name,provenance=provenance,summary=summary,config=inputs['config'],
            frame_hashes=hashes,metrics=metrics,initial_totals=initial,
            initial_fresh_mass_kg=initial[0]-initial[4],
            initialization_energy_change_J=r.get('initialization_energy_change_J'),
            formed_initialization=r.get('formed_initialization'),
            window=reduce_window(inputs,summary,history,0.,min(40e-6,frames[-1]['t'],summary['t'])))
        data.append(dict(record=record,frames=frames,r=r,js=js,x=x,z=z))
    a,b=[d['record']['config'] for d in data]
    assert {k:v for k,v in a.items() if k!='initialization'}=={k:v for k,v in b.items() if k!='initialization'}
    np.testing.assert_allclose([f['t'] for f in data[0]['frames']],[f['t'] for f in data[1]['frames']],rtol=0,atol=1e-13)
    out.mkdir()
    report=dict(runs=[d['record'] for d in data],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        interpretation='Startup-protocol comparison; initial inventories/shape differ. Pressure peaks are candidates, not a detonation classifier. 40 us cannot establish sustained rotation.',
        conserved_order=['mass kg','theta momentum kg m/s','z momentum kg m/s','total energy J','reacted mass kg'])
    (out/'metrics.json').write_text(json.dumps(report,indent=2,allow_nan=False,default=_json_default)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from PIL import Image
    fig,axs=plt.subplots(2,2,figsize=(12,7),sharex=True,sharey=True,layout='constrained')
    for col,d in enumerate(data):
        t=np.array([f['t'] for f in d['frames']])*1e6;j=d['js'][0]
        for row,(key,norm,label) in enumerate([('pressure',LogNorm(1e5,22e6),'Pressure [Pa]'),('reaction_rate',LogNorm(1,1e6),'Reaction rate [1/s]')]):
            values=np.array([f[key][:,j] for f in d['frames']])
            im=axs[row,col].pcolormesh(d['x']*1e3,t,np.maximum(values,1e-8),norm=norm,cmap='inferno',shading='nearest')
            fig.colorbar(im,ax=axs[row,col],label=label)
            axs[row,col].set(xlabel='Circumferential x [mm]; periodic',ylabel='Time [us]',ylim=(0,40))
        axs[0,col].set_title(d['record']['name'])
    fig.suptitle('Matched chemistry, mesh, feed, walls | z = 0.752 mm | unequal startup inventories')
    fig.savefig(out/'space_time.png',dpi=140);plt.close(fig)
    fig,axs=plt.subplots(3,2,figsize=(12,8),sharex=True,layout='constrained')
    for d in data:
        f=d['frames'][-1]
        for row,j in enumerate(d['js']):
            axs[row,0].plot(d['x']*1e3,f['pressure'][:,j]/1e6,label=d['record']['name'])
            axs[row,1].semilogy(d['x']*1e3,np.maximum(f['reaction_rate'][:,j],1e-6),label=d['record']['name'])
            axs[row,0].set_ylabel(f"p [MPa]\nz={d['z'][j]*1e3:.3f} mm")
            axs[row,1].set(ylabel='Reaction rate [1/s]',ylim=(1e-4,1e6))
    axs[0,0].legend();fig.suptitle('40 us: pressure and reaction must be assessed together')
    for ax in axs[-1]:ax.set_xlabel('Circumferential x [mm]')
    fig.savefig(out/'profiles_40us.png',dpi=140);plt.close(fig)
    images=[]
    for n in range(len(data[0]['frames'])):
        fig,axs=plt.subplots(2,2,figsize=(11,5),sharex=True,sharey=True,layout='constrained')
        for col,d in enumerate(data):
            f=d['frames'][n]
            for row,(key,norm,label) in enumerate([('pressure',LogNorm(1e5,22e6),'Pressure [Pa]'),('reaction_rate',LogNorm(1,1e6),'Reaction rate [1/s]')]):
                im=axs[row,col].pcolormesh(d['x']*1e3,d['z']*1e3,np.maximum(f[key].T,1e-8),norm=norm,cmap='inferno',shading='nearest')
                fig.colorbar(im,ax=axs[row,col],label=label)
                axs[row,col].set(ylabel='Axial z [mm]',ylim=(0,20),xlabel='Circumferential x [mm]; periodic')
            axs[0,col].set_title(d['record']['name'])
        fig.suptitle(f"Startup comparison | t={data[0]['frames'][n]['t']*1e6:.1f} us | lower 20 mm | fixed scales")
        buf=io.BytesIO();fig.savefig(buf,format='png',dpi=95);plt.close(fig);buf.seek(0)
        images.append(Image.open(buf).convert('RGB'))
    images[0].save(out/'comparison.gif',save_all=True,append_images=images[1:],duration=[200]*(len(images)-1)+[1500])
    print(out)

if __name__=='__main__':main()
