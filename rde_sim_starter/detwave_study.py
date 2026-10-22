"""Opt-in bounded engine investigation. Production solver/defaults are unchanged."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import yaml

from analyze import conservation_budget
from calibrate import calibrate
from detwave_initialization import initialize_engine
from run import resolve_case, build_solver, _fingerprint, _write_json, _write_npz
from solver import NG


def setup(dx_mm=.125, half_mm=.25, source_cfl=.2, config=None):
    cfg=(yaml.safe_load(Path(__file__).with_name('config.yaml').read_text())
         if config is None else copy.deepcopy(config))
    cfg['chemistry']['L_half_mm']=half_mm
    cfg['numerics'].update(dx_mm=dx_mm,source_cfl=source_cfl)
    if config is None:
        cfg['initialization']=dict(kind='formed',fill_height_mm=3.8,
            product_temperature_K=1500.,charge_length_mm=25.,shock_fraction=.1)
    if cfg['initialization']['kind']!='formed':
        raise ValueError('this investigation requires explicit formed initialization')
    c=calibrate(cfg);r=resolve_case(cfg,c);s=build_solver(r,c,initialize=False)
    initialize_engine(s,r,c)
    return cfg,c,r,s


def fingerprint():
    fp=_fingerprint()
    fp['study']={n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest()
                 for n in ('detwave_study.py','detwave_initialization.py','controlled.py')}
    return fp


def run(directory, dx_mm=.125, half_mm=.25, source_cfl=.2, end_us=None, resume=False, case_path=None):
    directory=Path(directory)
    config=None if case_path is None else yaml.safe_load(Path(case_path).read_text())
    if resume:
        manifest=json.loads((directory/'inputs.json').read_text())
        if manifest['fingerprint']!=fingerprint():
            raise ValueError('resume requires unchanged source/environment')
        dx_mm,half_mm,source_cfl=(manifest[k] for k in ('dx_mm','half_mm','source_cfl'))
        end_us=manifest['end_us']
        config=manifest['config']
    cfg,c,r,s=setup(dx_mm,half_mm,source_cfl,config)
    cap=3/r['f_ref'];end=cap if end_us is None else end_us*1e-6
    if not np.isfinite(end) or not 0<end<=cap+1e-15:
        raise ValueError('study must end within three reference passage intervals')
    initial=s.conserved_totals()
    rho1=c['p1']/(c['R']*c['T1']);volume=r['width']*r['length']
    scale=np.maximum(abs(initial),np.array([rho1,rho1*c['D_CJ'],rho1*c['D_CJ'],
        c['p1']/(c['gamma']-1)+rho1*c['q'],rho1])*volume)
    heights=np.array([.5,1.,2.,3.,4.,6.,10.])*1e-3
    rows=np.minimum((heights/s.dy).astype(int),s.ny-1)
    histories=[];rings=[];times=[];elapsed=0.
    if resume:
        with np.load(directory/'checkpoint.npz') as a:
            s.U[:]=a['U'];s.t=float(a['t']);s.steps=int(a['steps'])
            s.cumulative_boundary[:]=a['boundary'];s.cumulative_source[:]=a['source']
            s.progress_roundoff_max=float(a['roundoff'])
            elapsed=float(a['wall_seconds']);times=a['times'].tolist();rings=list(a['rings'])
            histories=json.loads(str(a['history']))
        s._check_state(s.U,'study resume')
    else:
        directory.mkdir(parents=True,exist_ok=False)
        (directory/'fields').mkdir()
        _write_json(directory/'inputs.json',dict(config=cfg,calibration=c,resolved=r,
            dx_mm=dx_mm,half_mm=half_mm,source_cfl=source_cfl,end_us=end*1e6,
            fingerprint=fingerprint(),actual_ring_heights_m=((rows+.5)*s.dy).tolist(),
            initial_totals_per_m_depth=initial,policy='bounded surrogate study; no automatic detonation verdict'))
    started=time.monotonic();status='running';error=None

    def save(full=False):
        w=s.prim();T=w[3]/(w[0]*s.R)
        rate=s.k*(1-w[4])*np.exp(-s.Ea/(s.R*T))
        power=w[0]*s.q*rate
        budget=conservation_budget(s.conserved_totals(),initial,s.cumulative_boundary,s.cumulative_source,1.,1.)
        residual=float(np.max(abs(budget['residual'])/scale))
        if not np.isfinite(residual) or residual>1e-10:
            raise RuntimeError('invalid native conservation residual')
        rings.append(np.concatenate((w[:,:,rows],rate[:,rows][None,:,:]),axis=0).astype(np.float32))
        times.append(s.t)
        outlet_mach=w[2,:,-1]/np.sqrt(s.g*w[3,:,-1]/w[0,:,-1])
        histories.append(dict(time_s=s.t,steps=s.steps,budget_scaled_residual=residual,
            converted_J=float(s.q*s.cumulative_source[4]*r['gap']),
            fresh_mass_kg=float(np.sum(w[0]*(1-w[4]))*s.dx*s.dy*r['gap']),
            injected_mass_kg=float(s.cumulative_boundary[2,0]*r['gap']),
            chemical_power_W=float(power.sum()*s.dx*s.dy*r['gap']),
            pressure_max_Pa=float(w[3].max()),
            high_pressure_heat_fraction=float(power[w[3]>2*c['p1']].sum()/max(power.sum(),1e-30)),
            outlet_subsonic_fraction=float(np.mean(outlet_mach<1)),
            boundary=s.cumulative_boundary.tolist(),source=s.cumulative_source.tolist()))
        if full:
            _write_npz(directory/'fields'/f't_{s.t*1e6:010.4f}us.npz',time=s.t,
                primitive=w.astype(np.float32),rate=rate.astype(np.float32))
        checkpoint()

    def checkpoint():
        wall=elapsed+time.monotonic()-started
        _write_npz(directory/'checkpoint.npz',U=s.U,t=s.t,steps=s.steps,
            boundary=s.cumulative_boundary,source=s.cumulative_source,
            roundoff=s.progress_roundoff_max,wall_seconds=wall,times=times,
            rings=np.asarray(rings),history=json.dumps(histories))
        _write_json(directory/'progress.json',dict(status=status,error=error,time_us=s.t*1e6,
            end_us=end*1e6,steps=s.steps,wall_seconds=wall,
            estimated_total_seconds=wall*end/s.t if s.t else None,
            invalid_state_count=s.invalid_state_count,history=histories))
        print(f'{directory.name}: {s.t*1e6:.3f}/{end*1e6:.3f} us, {s.steps} steps, {wall:.1f} s',flush=True)

    try:
        if not resume:save(full=True)
        tick=int(round(s.t/1e-6))+1
        while s.t<end-1e-16:
            target=min(end,tick*1e-6)
            while s.t<target-1e-16:s.step(dt_max=target-s.t)
            save(full=(tick%10==0 or s.t>=end-1e-16));tick+=1
        status='completed'
    except BaseException as caught:
        status='failed';error=repr(caught)
        checkpoint()
        raise
    finally:
        _write_json(directory/'summary.json',dict(status=status,error=error,time_s=s.t,
            wall_seconds=elapsed+time.monotonic()-started,steps=s.steps,
            invalid_state_count=s.invalid_state_count,history=histories,
            initial_conserved_per_m_depth=initial,final_conserved_per_m_depth=s.conserved_totals(),
            cumulative_boundary=s.cumulative_boundary,cumulative_source=s.cumulative_source))
    checkpoint()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True);p.add_argument('--dx-mm',type=float,default=.125)
    p.add_argument('--half-mm',type=float,default=.25)
    p.add_argument('--source-cfl',type=float,default=.2)
    p.add_argument('--end-us',type=float);p.add_argument('--resume',action='store_true')
    p.add_argument('--case',type=Path,help='explicit geometry/operating-point study case')
    a=p.parse_args()
    if a.resume and a.case:p.error('--resume uses saved inputs; do not supply --case')
    run(a.out,a.dx_mm,a.half_mm,a.source_cfl,a.end_us,a.resume,a.case)


if __name__=='__main__':main()
