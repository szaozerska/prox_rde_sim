"""Rendering from supplied/saved data only; never advances the solver.

The first available CLI renders saved surrogate calibration data. The planned
run-directory field/report CLI belongs to the next increment.
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


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibration',type=Path,required=True,help='saved calibration JSON')
    parser.add_argument('--out',type=Path,required=True,help='new PNG destination')
    args=parser.parse_args(argv)
    if args.out.exists():
        parser.error('output exists; choose a new filename')
    from calibrate import znd_profile
    with args.calibration.open() as stream:
        calibration=json.load(stream)
    plot_znd(znd_profile(calibration),calibration,args.out)
    print(args.out)


if __name__ == '__main__':
    main()
