"""Compare saved native short-wave fields with the independent ZND reference."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference',type=Path);p.add_argument('output',type=Path);p.add_argument('runs',nargs='+',type=Path);a=p.parse_args()
    r=json.loads((a.reference/'reference.json').read_text());z=np.load(a.reference/'znd.npz');speed=r['CJ']['CJ_speed_mps']
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    maxt=0.;shock0=None
    for run in a.runs:
        report=json.loads((run/'wave_checks.json').read_text());case=json.loads((run/'case.json').read_text());result=json.loads((run/'result.json').read_text());d=np.load(run/'wave_profiles.npz')
        t=d['time_s'];front=np.array([row['shock_locations_m'][1] for row in report['history']]);maxt=max(maxt,t[-1]);shock0=case['shock_initial_m']
        label=f"{case['dx_m']*1e6:g} um, dt {result['dt']*1e9:g} ns"
        axes[0,0].plot(t*1e6,(front-shock0)*1000,'o-',ms=3,label=label)
        x=(d['x_m'][-1]-front[-1])*1e6
        for ax,key,scale in [(axes[0,1],'pressure_Pa',1e-6),(axes[1,0],'temperature_K',1.),(axes[1,1],'heat_fraction',1.)]:ax.plot(x,d[key][-1]*scale,label=label)
    axes[0,0].plot(np.array([0,maxt])*1e6,np.array([0,maxt])*speed*1000,'k--',label='CJ reference')
    for ax,key,scale in [(axes[0,1],'pressure_Pa',1e-6),(axes[1,0],'temperature_K',1.),(axes[1,1],'heat_fraction',1.)]:
        ax.plot(-z['distance_m']*1e6,z[key]*scale,'k--',label='Independent ZND')
        ax.set(xlim=(-150,70),xlabel='Position relative to measured pressure front [um]');ax.grid(alpha=.2)
    axes[0,0].set(xlabel='Time [us]',ylabel='Pressure-front displacement [mm]');axes[0,0].legend(fontsize=8);axes[0,0].grid(alpha=.2)
    axes[0,1].set_ylabel('Pressure [MPa]');axes[0,1].legend(fontsize=8)
    axes[1,0].set_ylabel('Temperature [K]');axes[1,1].set_ylabel('Formation-enthalpy heat fraction')
    fig.suptitle('Short native methane wave diagnostic — inspect speed and reaction-zone error')
    fig.savefig(a.output,dpi=150)
if __name__=='__main__':main()
