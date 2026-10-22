"""Plot saved ZND and native inversion evidence; never run a solver."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('references',type=Path);parser.add_argument('evidence',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    series={}
    for name,label in [('grimech30','GRI-Mech 3.0'),('FFCM1_Red','FFCM1_Red')]:
        data=np.load(args.references/f'{name}_znd_strict.npz')
        axes[0].plot(data['distance_m']*1e6,data['temperature_K'],label=label)
        indexes=np.unique(np.linspace(0,len(data['distance_m'])-1,300,dtype=int))
        series[name]={'distance_um':(data['distance_m'][indexes]*1e6).tolist(),'temperature_K':data['temperature_K'][indexes].tolist()}
    axes[0].set(xlabel='Distance behind shock (µm)',ylabel='Temperature (K)',xlim=(0,150),
                title='Steady 1D ZND reference: reaction lengths differ')
    for label,style in [('original','o-'),('diagnostic','s--')]:
        evidence=json.loads((args.evidence/f'thermo_{label}_evidence.json').read_text())
        case=next(c for c in evidence['cases'] if c['mechanism']=='grimech30')
        states=[(s['temperature_K'],v[2]-s['temperature_K']) for s,v in zip(case['states'],case['values_cgs']) if s['condition']=='TP_equilibrium']
        axes[1].plot([x[0] for x in states],[x[1] for x in states],style,label=label.capitalize())
    axes[1].axvline(3500,color='gray',ls=':',label='Major GRI fit limit')
    axes[1].set(xlabel='Input temperature (K)',ylabel='Recovered minus input T (K)',
                title='Native GRI inverse consistency; fit validity unchanged')
    for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Methane preflight — numerical/model comparisons, not an RDE result',fontsize=12)
    fig.savefig(args.output,dpi=170)
    args.output.with_suffix('.json').write_text(json.dumps(series,indent=2)+'\n')


if __name__=='__main__':main()
