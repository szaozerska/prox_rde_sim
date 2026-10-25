"""Compare native propagation histories and wave structure with the independent ZND."""
import json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collect_diagnostic_evidence import windows

def main(folder,output):
    root=Path(folder);ref=json.loads((root/'long_reference/reference.json').read_text());z=np.load(root/'long_reference/znd.npz');cj=ref['CJ']['CJ_speed_mps']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(14,4.3),layout='constrained');ax,ap,aq=axes
    ax.axhline(cj,color='black',ls='--',lw=1,label='CJ reference')
    select=z['distance_m']<=150e-6
    xr=np.r_[-z['distance_m'][select][::-1],0,50e-6]*1e6
    ap.plot(xr,np.r_[z['pressure_Pa'][select][::-1],ref['CJ']['pressure_Pa'],ref['CJ']['pressure_Pa']]/1e6,color='black',ls='--',label='Independent ZND')
    aq.plot(xr,np.r_[z['heat_fraction'][select][::-1],0,0],color='black',ls='--')
    for backend,name,label,color in [('cpu','long_16um_2us','CPU 16 µm','#d97706'),('cpu','long_8um_2us','CPU 8 µm','#2563eb'),('gpu','long_16um_2us','GPU 16 µm','#169873')]:
        p=root/(backend+'_planar_results')/(name+'_native/case')
        if not (p/'wave_checks.json').exists():continue
        c=json.loads((p/'wave_checks.json').read_text());data=np.load(p/'wave_profiles.npz');fits=windows(c);t=[];speeds=[]
        for f in fits:
            if all(v is not None for v in f['speed_mps']):t.append((f['start_s']+f['end_s'])*.5e6);speeds.append(f['speed_mps'])
        speeds=np.array(speeds);ax.plot(t,speeds[:,1],marker='o',color=color,label=label);ax.fill_between(t,speeds.min(axis=1),speeds.max(axis=1),color=color,alpha=.2)
        x=data['x_m'];x=x[-1] if x.ndim==2 else x;x=(x-c['history'][-1]['shock_locations_m'][1])*1e6
        ap.plot(x,data['pressure_Pa'][-1]/1e6,color=color,label=label);aq.plot(x,data['heat_fraction'][-1],color=color)
    ax.set(xlabel='Speed-fit window midpoint (µs)',ylabel='Mean front speed (m/s)',title='Startup excess relaxes');ax.legend(fontsize=8)
    ap.set(xlim=(-150,50),xlabel='Position relative to pressure front (µm)',ylabel='Pressure (MPa)',title='Wave structure at 2 µs');ap.legend(fontsize=8)
    aq.set(xlim=(-150,50),ylim=(-.05,1.08),xlabel='Position relative to pressure front (µm)',ylabel='Chemical heat-release fraction',title='Reaction zone remains unresolved');aq.axhline(.5,color='.7',lw=.7)
    for a in axes:a.grid(alpha=.15)
    fig.suptitle('Native planar diagnostics: plausible late speed does not validate reaction structure',fontsize=13)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(output,dpi=160);plt.close(fig)
if __name__=='__main__':main(*sys.argv[1:])
