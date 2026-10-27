"""Stream native AMR blocks without flattening or deleting source fields."""
import argparse,json,re
from pathlib import Path
import numpy as np


def analyze_plot(plot,case,output):
    import yt
    yt.set_log_level(40)
    ds=yt.load(str(plot));time=float(ds.current_time)
    theta=np.linspace(0,2*np.pi,720,endpoint=False);z=(np.arange(384)+.5)*7.62/384
    th,zz=np.meshgrid(theta,z,indexing='ij')
    points=np.stack([3.56*np.cos(th),3.56*np.sin(th),zz],axis=-1).reshape(-1,3)
    sample={k:np.full(len(points),np.nan) for k in ('pressure','Temp','Y(CH4)','Y(O2)','heatRelease')}
    sample_level=np.full(len(points),-1,dtype=int)
    row={'time_s':time,'mass_kg':0.,'total_energy_J':0.,'methane_kg':0.,'oxygen_kg':0.,
         'min_species':1.,'species_sum_error':0.,'negative_inventory_kg':0.,'finite':True,
         'pressure_Pa':[float('inf'),-float('inf')],'temperature_K':[float('inf'),-float('inf')],
         'fluid_volume_m3':0.,'max_speed_mps':0.,'finest_level':int(ds.index.max_level),
         'leaf_fluid_cells':0,'blocks':len(ds.index.grids)}
    has_heat=('boxlib','heatRelease') in ds.field_list
    for grid in sorted(ds.index.grids,key=lambda g:g.Level):
        vf=np.asarray(grid['boxlib','vfrac']);leaf=grid.child_mask.astype(bool);valid=(vf>0)&leaf
        dx=np.asarray(grid.dds);lo=np.asarray(grid.LeftEdge);hi=np.asarray(grid.RightEdge)
        needed=set(sample)-({'heatRelease'} if not has_heat else set())
        fields={k:np.asarray(grid['boxlib',k]) for k in needed}
        if valid.any():
            rho=np.asarray(grid['boxlib','density'])*1000;vol=np.prod(dx)*1e-6;w=vf*leaf*vol
            row['finite'] &= bool(np.isfinite(rho[valid]).all() and np.isfinite(np.asarray(grid['boxlib','rho_E'])[valid]).all())
            row['mass_kg']+=float(np.sum(rho*w));row['fluid_volume_m3']+=float(np.sum(w))
            row['total_energy_J']+=float(np.sum(np.asarray(grid['boxlib','rho_E'])*w)*.1)
            row['methane_kg']+=float(np.sum(rho*fields['Y(CH4)']*w));row['oxygen_kg']+=float(np.sum(rho*fields['Y(O2)']*w))
            total=np.zeros_like(rho);neg=np.zeros_like(rho)
            for species in case['species']:
                y=np.asarray(grid['boxlib','Y('+species+')']);total+=y;neg+=np.maximum(-y,0)
                row['min_species']=min(row['min_species'],float(y[valid].min()))
                row['finite'] &= bool(np.isfinite(y[valid]).all())
            row['species_sum_error']=max(row['species_sum_error'],float(np.abs(total[valid]-1).max()))
            row['negative_inventory_kg']+=float(np.sum(rho*neg*w))
            for name,key,factor in [('pressure','pressure_Pa',.1),('Temp','temperature_K',1.)]:
                a=fields[name][valid]*factor
                row[key]=[min(row[key][0],float(a.min())),max(row[key][1],float(a.max()))]
                row['finite'] &= bool(np.isfinite(a).all())
            speed2=sum(np.asarray(grid['boxlib',axis+'_velocity'])**2 for axis in 'xyz')
            row['max_speed_mps']=max(row['max_speed_mps'],float(np.sqrt(speed2[valid]).max())*.01)
            row['leaf_fluid_cells']+=int(valid.sum())
        select=np.where(np.all((points>=lo)&(points<hi),axis=1))[0]
        if len(select):
            ijk=np.floor((points[select]-lo)/dx).astype(int);idx=tuple(ijk.T)
            fluid=vf[idx]>0;select=select[fluid];idx=tuple(ijk[fluid].T)
            for name in sample:
                if name in fields:sample[name][select]=fields[name][idx]
            sample_level[select]=grid.Level
        grid.clear_data()
    if (sample_level<0).any():raise ValueError('Cylindrical sample includes uncovered/nonfluid points')
    np.savez_compressed(output,time_s=time,theta_rad=theta,z_m=z*.01,
        pressure_Pa=sample['pressure'].reshape(th.shape)*.1,
        temperature_K=sample['Temp'].reshape(th.shape),methane_Y=sample['Y(CH4)'].reshape(th.shape),
        oxygen_Y=sample['Y(O2)'].reshape(th.shape),heat_release_W_m3=sample['heatRelease'].reshape(th.shape)*.1,
        level=sample_level.reshape(th.shape))
    row['heat_release_available']=has_heat
    output.with_suffix('.json').write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')
    return row


def collect(root,final=False):
    root=Path(root);case=json.loads((root/'case.json').read_text());out=root/'slices';out.mkdir(exist_ok=True)
    plots=sorted(root.glob('plt[0-9]*'));targets=plots if final else plots[:-1]
    for plot in targets:
        target=out/(plot.name+'.npz')
        if target.with_suffix('.json').exists():continue
        row=analyze_plot(plot,case,target);print(plot.name,row['time_s'],row['min_species'],flush=True)
    files=sorted(out.glob('plt*.npz'))
    if not files:return
    records=[json.loads(p.with_suffix('.json').read_text()) for p in files]
    frames=[]
    for p in files:
        with np.load(p) as a:frames.append({k:a[k] for k in a.files})
    keys=('pressure_Pa','temperature_K','methane_Y','oxygen_Y','heat_release_W_m3','level')
    arrays={k:np.stack([f[k] for f in frames]) for k in keys}
    np.savez_compressed(root/'preview.npz',time_s=[r['time_s'] for r in records],
                        theta_rad=frames[0]['theta_rad'],z_m=frames[0]['z_m'],**arrays)
    checks={'finite':all(r['finite'] for r in records),
        'species_nonnegative':all(r['min_species']>=-1e-10 for r in records),
        'species_sum':all(r['species_sum_error']<1e-8 for r in records),
        'positive_pressure':all(r['pressure_Pa'][0]>0 for r in records),
        'thermo_range':all(200<=r['temperature_K'][0] and r['temperature_K'][1]<=5000 for r in records)}
    log=(root/'solver.log').read_text()
    extrema=[(float(t),float(v)) for t,v in re.findall(r'TIME = (\S+)\s+massfrac\s+MIN = (\S+)',log)]
    worst=min(extrema,key=lambda pair:pair[1]) if extrema else None
    checks['every_step_species_nonnegative']=bool(worst and worst[1]>=-1e-10)
    history={'samples':len(extrema),'worst_time_s':worst[0] if worst else None,
             'minimum_mass_fraction':worst[1] if worst else None,
             'note':'Includes coarse-step extrema between saved snapshots; no inference of integrated mass error.'}
    (root/'checks.json').write_text(json.dumps({'rows':records,'checks':checks,'every_step_species':history,'physical_validation_passed':False,
        'sampling':'Native cell nearest-neighbour at each cylindrical sample; finest available AMR block. No temporal interpolation.',
        'scope':'AMR leaf-cell inventories and extrema; open-system inventory change alone is not a conservation defect.'},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--final',action='store_true')
    a=p.parse_args();collect(a.root,a.final)
