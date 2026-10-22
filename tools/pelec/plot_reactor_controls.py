"""Plot saved reactor checks; no new chemistry or CFD calculation."""
import argparse
import json
from pathlib import Path
import numpy as np


def plot(base, tight, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    baseline=json.loads((base/'history_native_constants.json').read_text())
    refined=json.loads((tight/'history_native_constants.json').read_text())
    nominal=json.loads((base/'history_nominal.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(11,5.2),layout='constrained')
    for report,label,style in [(baseline,'Native, rtol 1e-10 / atol 1e-20','o'),
                                (refined,'Native, rtol 1e-11 / atol 1e-22','x')]:
        t=np.array(report['time_s'])*1e6
        T=np.array(report['native_temperature_K'])
        truth=np.array(report['reference_temperature_K'])
        axes[0].plot(t,T,style,markersize=3,label=label)
        error=abs(T/truth-1)
        axes[1].semilogy(t,np.maximum(error,1e-15),style+'-',markersize=3,label=label)
    axes[0].plot(np.array(baseline['time_s'])*1e6,baseline['reference_temperature_K'],
                 'k-',linewidth=1,label='Independent reference at saved steps (generated constants)')
    t=np.array(nominal['time_s'])*1e6
    nominal_error=abs(np.array(nominal['native_temperature_K'])/nominal['reference_temperature_K']-1)
    axes[1].semilogy(t,np.maximum(nominal_error,1e-15),':',color='gray',
                     label='Nominal YAML comparison (different constants)')
    axes[1].axhline(2e-5,color='red',linestyle='--',linewidth=1,label='Numerical-control limit')
    axes[0].set(xlim=(80,180),xlabel='Time (microseconds)',ylabel='Temperature (K)')
    axes[1].set(xlim=(80,180),xlabel='Time (microseconds)',ylabel='Absolute relative temperature error',ylim=(1e-10,.03))
    for ax in axes:
        ax.grid(alpha=.2)
    unique={}
    for ax in axes:
        handles,labels=ax.get_legend_handles_labels()
        unique.update(zip(labels,handles))
    fig.legend(unique.values(),unique.keys(),loc='outside lower center',ncol=2,fontsize=8)
    fig.suptitle('Native PeleC / H100 closed hydrogen reactor: ignition controls\nFull runs reach 1 ms; this is not methane or RDE validation',fontsize=11)
    fig.savefig(output,dpi=160);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path);parser.add_argument('tight',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args();plot(args.base,args.tight,args.output)
