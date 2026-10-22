"""Read-only reduction of C5 fields. Output path supplied explicitly."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
root=Path(sys.argv[1]);out=Path(sys.argv[2]);cases=[]
for folder in sorted(root.glob('layer_*'),reverse=True):
    if not (folder/'summary.json').exists():continue
    r=json.loads((folder/'summary.json').read_text());inp=json.loads((folder/'inputs.json').read_text());c=inp['calibration']
    with np.load(folder/'fields.npz') as a:
        x=a['x'];z=a['z'];t=a['times'];w=a['primitive']
    # Keep the final member of a roundoff-separated output pair. Tolerance is
    # a million times below the 1 us output cadence, not a physics smoothing.
    keep=np.r_[np.diff(t)>1e-12,True];times=t[keep]
    histories=[h for h,k in zip(r['history'],keep) if k]
    final=w[-1];temp=final[3]/(c['R']*final[0]);rate=c['k']*np.maximum(0,1-final[4])*np.exp(-c['Ea']/(c['R']*temp))
    rows=[]
    for j,index in enumerate(inp['diagnostic_row_indexes']):
        fits={}
        for start in (4e-6,6e-6,8e-6):
            selected=[h for h in histories if h['time_s']>=start-1e-12 and h['rows'][j]['front_m'] is not None]
            fits[str(start)]=float(np.polyfit([h['time_s'] for h in selected],[h['rows'][j]['front_m'] for h in selected],1)[0]) if len(selected)>=3 else None
        f=histories[-1]['rows'][j]['front_m'];near={}
        for width in (.0005,.002):
            mask=(x>=f-width-1e-12)&(x<=f+1e-12)
            near[str(width)]=float(rate[mask,index].max())
        rows.append(dict(z_m=float(z[index]),final=histories[-1]['rows'][j],late_speed_mps=fits,near_front_max_rate_per_s=near))
    rho0=c['p1']/(c['R']*1500.)
    expected=np.array([rho0,0.,0.,c['p1'],1.])
    scales=np.array([rho0,c['D_CJ'],c['D_CJ'],c['p1'],1.])
    top=np.max(abs(final[:,:,-4:]-expected[:,None,None])/scales[:,None,None],axis=(1,2))
    ahead=x>inp['shock_initial_m']+.01
    mixed=np.flatnonzero((w[0,4,ahead,:].mean(axis=0)>1e-10)&(w[0,4,ahead,:].mean(axis=0)<1-1e-10))
    mixed_data=[dict(z_m=float(z[j]),T_K=float((w[0,3,ahead,j]/(c['R']*w[0,0,ahead,j])).mean()),progress=float(w[0,4,ahead,j].mean())) for j in mixed]
    # Check the saved conservative endpoint against the reported native integral.
    with np.load(folder/'state.npz') as a:U=a['conserved']
    totals=U.sum(axis=(1,2))*inp['initialization']['dx_m']*inp['initialization']['dy_m']
    residual=float(np.max(abs(totals-np.array(r['final_conserved_per_m_depth']))/np.maximum(abs(totals),1.)))
    cases.append(dict(directory=str(folder),inputs=inp,summary=r,unique_snapshot_count=int(keep.sum()),
       roundoff_duplicate_count=int((~keep).sum()),row_measurements=rows,top_scaled_changes=top.tolist(),
       mixed_initial_rows=mixed_data,conservative_endpoint_integral_error=residual,
       sha256={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in ('inputs.json','summary.json','state.npz','fields.npz')}))
report=dict(cases=cases,method='Native row pressure threshold and reaction association; late least-squares speeds with roundoff-duplicate times removed. No resampling, CFD or chemistry fitting.',
            snapshot_deduplication_tolerance_s=1e-12,interpretation='Bounded 10 us response only; no steady engine, critical-height or physical-chemistry validation claim.')
with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
for case in cases:
 print(Path(case['directory']).name,'top',case['top_scaled_changes'],'mixed',case['mixed_initial_rows'])
 print('rows',case['row_measurements'])
