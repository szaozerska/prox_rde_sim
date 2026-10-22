"""Pure reference calculations for the inherited one-step surrogate.

This fits a constant-gamma model; it is not a detailed-chemistry validation.
Rendering lives in plot.py. Running the CLI requires an explicit output path.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import yaml
from scipy.integrate import quad
from scipy.optimize import brentq


def heat_mach(M1, Qx, g):
    """Subsonic (strong-branch) M2 from Eq. 1.6 for heat Qx; ZND path after the shock."""
    f = lambda M2: ((M2 / M1) ** 2 * ((1 + g * M1 * M1) / (1 + g * M2 * M2)) ** 2
                    * (1 + 0.5 * (g - 1) * M2 * M2) - (1 + 0.5 * (g - 1) * M1 * M1) - Qx)
    # f is increasing in M2 on (0,1]; at Qx = Q (CJ) the root is exactly 1
    if f(1.0) <= 0:
        return 1.0
    return brentq(f, 1e-6, 1.0)



def dcj(gamma, q, R, T1):
    cp = gamma*R/(gamma-1.0)
    Q = q/(cp*T1)
    x = 1.0 + (gamma+1.0)*Q
    return math.sqrt(x + math.sqrt(x*x-1.0))*math.sqrt(gamma*R*T1)


def state(xi, calibration):
    """Return T/T1, p/p1, Mach and shock-frame speed on the surrogate ZND path."""
    if not 0 <= xi <= 1:
        raise ValueError("reaction progress must lie in [0, 1]")
    c = calibration
    g, M1 = c['gamma'], c['M_CJ']
    M2 = heat_mach(M1, xi*c['Q'], g)
    T = (M2/M1)**2 * ((1+g*M1*M1)/(1+g*M2*M2))**2
    pressure = (1+g*M1*M1)/(1+g*M2*M2)
    return T, pressure, M2, M2*math.sqrt(g*c['R']*T*c['T1'])


def dx_dxi(xi, k, calibration):
    if not 0 <= xi < 1 or k <= 0:
        raise ValueError("finite reaction distance requires 0 <= xi < 1 and k > 0")
    T, _, _, u = state(xi, calibration)
    return u/(k*(1-xi)*math.exp(-calibration['Ea']/(calibration['R']*T*calibration['T1'])))


def calibrate(config):
    """Return parameters without mutating inputs, writing files, or rendering."""
    op, ch = config['operating_point'], config['chemistry']
    phi = op['phi']
    x_ch4 = phi/(phi+2.0)
    MW = x_ch4*16.043 + (1-x_ch4)*31.999
    R, T1 = 8314.46/MW, op['T_plenum_K']
    m = op['mass_flux']
    p1 = (-531.2+2.965*m+526.6*phi+0.0009336*m*m-1.418*m*phi-54.73*phi*phi)*1e3
    q = op['q_MJkg']*1e6
    if not np.all(np.isfinite([phi,R,T1,p1,q,ch['L_half_mm'],ch['Ea_over_RT1']])) or min(phi,T1,p1,q,ch['L_half_mm']) <= 0 or ch['Ea_over_RT1'] < 0:
        raise ValueError("invalid surrogate calibration inputs")
    g = brentq(lambda gg: dcj(gg,q,R,T1)-op['D_CJ'], 1.05, 1.6)
    cp = g*R/(g-1)
    a1 = math.sqrt(g*R*T1)
    c = dict(R=R, MW=MW, gamma=g, cp=cp, Q=q/(cp*T1), q=q, T1=T1, p1=p1,
             a1=a1, M_CJ=op['D_CJ']/a1, D_CJ=op['D_CJ'], Ea=ch['Ea_over_RT1']*R*T1,
             Ea_over_RT1=ch['Ea_over_RT1'])
    c['k'] = quad(dx_dxi,0,0.5,args=(1.0,c),limit=200)[0]/(ch['L_half_mm']*1e-3)
    c['L_half'] = quad(dx_dxi,0,0.5,args=(c['k'],c),limit=200)[0]
    Tvn,pvn,Mvn,uvn = state(0,c)
    Tcj,pcj,_,_ = state(1,c)
    c['VN'] = dict(p=pvn*p1,T=Tvn*T1,M=Mvn,u_shock_frame=uvn)
    c['CJ'] = dict(p=pcj*p1,T=Tcj*T1)
    # Inherited plot-read estimate, not a newly computed physical reference.
    c['lambda_real'], c['induction_real'] = 0.8e-3, 0.8e-3/29.0
    c['reference_note'] = 'lambda_real is an inherited plot estimate; induction_real is its factor-29 proxy, not a ZND calculation.'
    return c


def znd_profile(calibration, samples=300):
    if samples < 2:
        raise ValueError("at least two samples required")
    xis = np.linspace(0,0.999,samples)
    states = np.array([state(x,calibration) for x in xis])
    distances = np.array([quad(dx_dxi,0,x,args=(calibration['k'],calibration),limit=200)[0] for x in xis])
    return dict(progress=xis, distance=distances, temperature=states[:,0]*calibration['T1'],
                pressure=states[:,1]*calibration['p1'], mach=states[:,2])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, default=Path(__file__).with_name('config.yaml'))
    parser.add_argument('--out', type=Path, required=True, help='new JSON output; existing files are never overwritten')
    args = parser.parse_args(argv)
    with args.case.open() as stream:
        result = calibrate(yaml.safe_load(stream))
    with args.out.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')
    print(args.out)


if __name__ == '__main__':
    main()
