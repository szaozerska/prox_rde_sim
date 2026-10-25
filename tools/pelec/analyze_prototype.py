"""Audit native outputs and save compact, honestly labelled visualization data."""
import argparse,json
from pathlib import Path
import numpy as np
import cantera as ct
from scipy.ndimage import map_coordinates
from analyze_sod import load_fields
from wave_history import audit_history
ROOT=Path(__file__).resolve().parents[2]
def analyze(run):
    run=Path(run);c=json.loads((run/'case.json').read_text());result=json.loads((run/'result.json').read_text())
    g=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'))
    names=['density','rho_E','Temp','pressure','x_velocity','y_velocity','z_velocity']
    names += ['Y('+s+')' for s in g.species_names]
    if c['mode']==2:names+=['vfrac']
    rows=[];surfaces=[];temperatures=[];methane=[];planes=[];times=[]
    theta=np.linspace(0,2*np.pi,256,endpoint=False);initial=None
    plots=sorted(run.glob('plt[0-9]*'))
    for index,p in enumerate(plots):
        t,f,dx,lo=load_fields(p,tuple(names));vf=f.get('vfrac',np.ones_like(f['density']));fluid=vf>0
        rho=f['density']*1000;volume=np.prod(dx)*1e-6;P=f['pressure']/10;T=f['Temp'];Y=np.stack([f['Y('+s+')'] for s in g.species_names],axis=-1)
        row=dict(time_s=t,mass_kg=float(np.sum(rho*vf)*volume),total_energy_J=float(np.sum(f['rho_E']*vf)*volume*.1),
            methane_kg=float(np.sum(rho*f['Y(CH4)']*vf)*volume),oxygen_kg=float(np.sum(rho*f['Y(O2)']*vf)*volume),
            pressure_Pa=[float(P[fluid].min()),float(P[fluid].max())],temperature_K=[float(T[fluid].min()),float(T[fluid].max())],
            min_species=float(Y[fluid].min()),species_sum_error=float(np.max(abs(Y[fluid].sum(axis=-1)-1))),
            finite=bool(all(np.isfinite(v[fluid]).all() for v in f.values())),fluid_volume_m3=float(vf.sum()*volume))
        if c['mode']==0:
            row.update(mean_T=float(T.mean()),mean_p=float(P.mean()),mean_Y=Y.mean(axis=(0,1,2)).tolist())
        else:
            z=lo[2]+(np.arange(P.shape[2])+.5)*dx[2]
            th,zz=np.meshgrid(theta,z,indexing='ij');radius=3.56
            coords=np.array([(radius*np.cos(th)-lo[0])/dx[0]-.5,(radius*np.sin(th)-lo[1])/dx[1]-.5,(zz-lo[2])/dx[2]-.5])
            surfaces.append(map_coordinates(P,coords,order=1,mode='nearest'));temperatures.append(map_coordinates(T,coords,order=1,mode='nearest'));methane.append(map_coordinates(f['Y(CH4)'],coords,order=1,mode='nearest'))
            k=min(P.shape[2]-1,max(0,int(.2/dx[2])));plane=P[:,:,k].copy();plane[~fluid[:,:,k]]=np.nan;planes.append(plane)
            # Spatial maximum is a diagnostic; it does not prove a coupled detonation.
            low=z<=min(c['height_m']*100,.6);trace=surfaces[-1][:,low].mean(axis=1)
            row['pressure_peak_theta_rad']=float(theta[np.argmax(trace)]);row['near_injector_ring_peak_Pa']=float(trace.max())
        rows.append(row);times.append(t)
        print(f'{p.name}: {t*1e6:.4g} us, Tmax={row["temperature_K"][1]:.1f} K, minY={row["min_species"]:.3g}',flush=True)
    history=audit_history((run/'solver.log').read_text(),c['stop'],c['dt'],temperature_bounds=(200.,5000.))
    checks=dict(completion=result['completed'],finite=all(r['finite'] for r in rows),positive_pressure=all(r['pressure_Pa'][0]>0 for r in rows),
        species_nonnegative=all(r['min_species']>=-1e-10 for r in rows),species_sum=all(r['species_sum_error']<1e-8 for r in rows),
        thermo_range=all(200<=r['temperature_K'][0] and r['temperature_K'][1]<=5000 for r in rows),every_step_extrema=history['passed'])
    report=dict(checks=checks,rows=rows,execution=result,every_step_history=history,physical_validation_passed=False,
        scope='Exploratory native 3D diagnostic. A moving pressure peak is not proof of sustained detonation.')
    if c['mode']==0:
        g.TPX=1968.,22.984e6,'CH4:1.176,O2:2';r=ct.IdealGasReactor(g,energy='on',clone=True);net=ct.ReactorNet([r]);net.rtol=1e-11;net.atol=1e-20
        errT=errY=0
        for row in rows:
            if row['time_s']>0:net.advance(row['time_s'])
            errT=max(errT,abs(row['mean_T']/r.T-1));errY=max(errY,float(np.max(abs(np.array(row['mean_Y'])-r.phase.Y))))
        report['reference_errors']=dict(temperature_relative=errT,species_absolute=errY,
            mass_relative=abs(rows[-1]['mass_kg']/rows[0]['mass_kg']-1),energy_relative=abs(rows[-1]['total_energy_J']/rows[0]['total_energy_J']-1))
        checks.update(reactor_temperature=errT<1e-4,reactor_species=errY<1e-4,closed_mass=report['reference_errors']['mass_relative']<1e-9,closed_energy=report['reference_errors']['energy_relative']<1e-8)
    else:
        np.savez_compressed(run/'preview.npz',time_s=times,theta_rad=theta,z_m=z*.01,pressure_Pa=surfaces,temperature_K=temperatures,methane_Y=methane,base_pressure_Pa=planes)
        report['initial_inventory']=rows[0];report['apertures']=c['apertures']
        if c['case_type']=='cold' and rows[-1]['time_s']>0:
            report['net_accumulated_massflow_kg_s']=(rows[-1]['mass_kg']-rows[0]['mass_kg'])/rows[-1]['time_s']
            report['cold_species_feed_kg_s']={key:(rows[-1][key]-rows[0][key])/rows[-1]['time_s'] for key in ('methane_kg','oxygen_kg')}
    (run/'checks.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();r=analyze(a.run);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','every_step_history','initial_inventory')},indent=2))
