"""Plot saved native transport diagnostics; no solver invocation."""
import argparse,json
from pathlib import Path
import numpy as np
import cantera as ct
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    reference=a.runs/'formed_wave_reference_03';g=ct.Solution(str(reference/'native_constants.yaml'))
    ref=json.loads((reference/'reference.json').read_text())['CJ'];g.TPY=300.,ref['pressure_Pa'],ref['initial']['Y']
    oxygen0=g.elemental_mass_fraction('O');weights=np.array([g.n_atoms(i,'O')*g.atomic_weight('O')/g.molecular_weights[i] for i in range(g.n_species)])
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for name,label in [('formed_wave_probe03','8 um, second order'),('formed_wave_halfprobe01','8 um, half dt'),('formed_wave_fineprobe01','4 um, second order'),('formed_wave_firstorder03','8 um, actual first order')]:
        data=np.load(a.runs/name/'wave/wave_profiles.npz');x=data['x_m'][-1]*1000;y=data['species_Y'][-1]
        axes[0,0].plot(x,data['pressure_Pa'][-1]/1e6,label=label)
        axes[0,1].plot(x,data['temperature_K'][-1],label=label)
        axes[1,0].plot(x,y@weights-oxygen0,label=label)
        axes[1,1].plot(x,np.minimum(y.min(axis=1),0),label=label)
    for ax in axes.flat:ax.set(xlim=(.43,.54),xlabel='Axial position [mm]');ax.grid(alpha=.2)
    axes[0,0].set_ylabel('Native pressure [MPa]');axes[0,0].legend(fontsize=8)
    axes[0,1].set_ylabel('Native temperature [K]')
    axes[1,0].set_ylabel('Local oxygen-element mass-fraction deviation')
    axes[1,1].set_ylabel('Negative species mass-fraction residue');axes[1,1].set_yscale('symlog',linthresh=1e-12)
    fig.suptitle('Native methane transport diagnosis at 2 ns — no sustained-wave claim')
    fig.savefig(a.output,dpi=150)
if __name__=='__main__':main()
