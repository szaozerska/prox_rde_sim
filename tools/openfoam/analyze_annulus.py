"""Read actual reconstructed native 3D fields; no assumed wave propagation."""
import argparse,json,re,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from rde3d.native import read_field

def analyze(root):
    root=Path(root);c=json.loads((root/'init_annulus.json').read_text());n=c['cells']
    xyz=np.asarray(read_field(root/'0/C',n));theta=np.linspace(0,2*np.pi,256,endpoint=False);z=np.unique(np.round(xyz[:,2],10))
    th,zz=np.meshgrid(theta,z,indexing='ij');query=np.stack([.0356*np.cos(th),.0356*np.sin(th),zz],axis=-1)
    distance,index=cKDTree(xyz).query(query.reshape(-1,3));index=index.reshape(th.shape)
    times=[];pressures=[];temperatures=[];methane=[];rows=[]
    dirs=[]
    for d in root.iterdir():
        if d.is_dir():
            try:dirs.append((float(d.name),d))
            except ValueError:pass
    for t,d in sorted(dirs):
        p=np.asarray(read_field(d/'p',n))[:,0];T=np.asarray(read_field(d/'T',n))[:,0]
        U=np.asarray(read_field(d/'U',n));Y=np.stack([np.asarray(read_field(d/s,n))[:,0] for s in c['species']],axis=-1)
        times.append(t);pressures.append(p[index]);temperatures.append(T[index]);methane.append(Y[:,c['species'].index('CH4')][index])
        row=dict(time_s=t,pressure_Pa=[float(p.min()),float(p.max())],temperature_K=[float(T.min()),float(T.max())],min_species=float(Y.min()),species_sum_error=float(abs(Y.sum(axis=1)-1).max()),max_speed_m_s=float(np.linalg.norm(U,axis=1).max()))
        worst=np.unravel_index(np.argmax(abs(Y.sum(axis=1)-1)),(n,))[0]
        row['worst_sum_position_m']=xyz[worst].tolist();row['worst_sum_species']={s:float(v) for s,v in zip(c['species'],Y[worst])}
        rows.append(row);print(row,flush=True)
    logs='\n'.join(p.read_text() for p in root.glob('log.*') if p.name.endswith('mpirun') or 'detonationFoam' in p.name)
    pat=r'SPECIES_AUDIT time=(\S+) preClipMin=(\S+) clippedMass=(\S+) inertMin=(\S+)'
    audit=[tuple(map(float,m)) for m in re.findall(pat,logs)]
    clips=dict(samples=len(audit),worst_preclip_Y=min((a[1] for a in audit),default=None),sum_clipped_mass_kg=sum(a[2] for a in audit),max_step_clipped_mass_kg=max((a[2] for a in audit),default=None),worst_inert_Y=min((a[3] for a in audit),default=None))
    complete=bool(times and abs(times[-1]-c['stop'])<1e-12)
    checks=dict(completion=complete,positive_pressure=all(r['pressure_Pa'][0]>0 for r in rows),thermo_range=all(200<=r['temperature_K'][0] and r['temperature_K'][1]<=5000 for r in rows),species_nonnegative=all(r['min_species']>=-1e-10 for r in rows),species_sum=all(r['species_sum_error']<1e-8 for r in rows),no_significant_preclip_negative=bool(audit and clips['worst_preclip_Y']>=-1e-10))
    report=dict(checks=checks,rows=rows,clipping=clips,physical_validation_passed=False,scope='Exploratory reactive Euler native 3D fields. No sustained-detonation or experimental validation claim.',sampling_max_distance_m=float(distance.max()))
    (root/'checks.json').write_text(json.dumps(report,indent=2));np.savez_compressed(root/'preview.npz',time_s=times,theta_rad=theta,z_m=z,pressure_Pa=pressures,temperature_K=temperatures,methane_Y=methane)
    c['grid_label']=f'{c["ntheta"]} × {c["nr"]} × {c["nz"]} body-fitted grid';(root/'case.json').write_text(json.dumps(c,indent=2))
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run');a=p.parse_args();analyze(a.run)
