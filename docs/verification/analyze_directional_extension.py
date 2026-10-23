"""Audit the continued directional run and plot saved rings; never runs CFD."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'rde_sim_starter'))
from contracts import iter_fields
from coupling import periodic_peaks, track_candidates
from window_report import load_native_prefix, reduce_window, _json_default


def main():
    directory=ROOT/'rde_sim_starter/runs/directional_startup_extended'
    out=ROOT/'docs/verification/directional_extension'
    if out.exists():
        raise ValueError('refusing existing output')
    inputs, summary, history, provenance=load_native_prefix(directory)
    if summary['status']!='completed_limit':
        raise ValueError('this report requires the completed bounded extension')
    continuation=json.loads((directory/'continuation.json').read_text())
    parent=Path(continuation['parent_run'])
    for name,digest in continuation['preserved_files_sha256'].items():
        assert hashlib.sha256((parent/name).read_bytes()).hexdigest()==digest, name
        if name.startswith('fields/') or name=='inputs.json':
            assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest, name
    with np.load(parent/'checkpoint.npz',allow_pickle=False) as checkpoint:
        original_metadata=json.loads(str(checkpoint['state_json']))
    original_bytes=(parent/'history.jsonl').read_bytes()
    offset=original_metadata['history_bytes']
    original_history=original_bytes[:offset]
    tail=original_bytes[offset:]
    with (directory/'history.jsonl').open('rb') as stream:
        assert stream.read(len(original_history))==original_history
    if tail:
        assert any(p.read_bytes()==tail for p in (directory/'recovery').glob('*/history_after_checkpoint.jsonl'))
    r=inputs['resolved'];c=inputs['calibration']
    x=(np.arange(r['nx'])+.5)*r['dx'];z=(np.arange(r['ny'])+.5)*r['dy']
    rows=[int(np.argmin(abs(z-h))) for h in (.00075,.0038,.008)]
    samples=[];rings_p=[];rings_rate=[];hashes=[]
    for frame in iter_fields(directory,inputs,summary['steps']):
        rings=[]
        for j in rows:
            p=frame['pressure'][:,j];rate=frame['reaction_rate'][:,j]
            peaks=periodic_peaks(p,2*c['p1'],.25*c['p1'],2)
            candidates=[]
            for k in peaks:
                distance=abs((x-x[k]+r['width']/2)%r['width']-r['width']/2)
                candidates.append(dict(x_m=float(x[k]),pressure_MPa=float(p[k]/1e6),
                    nearby_rate_per_s={str(mm):float(rate[distance<=mm*.001].max()) for mm in (2,4,8)}))
            rings.append(dict(z_mm=float(z[j]*1e3),max_pressure_MPa=float(p.max()/1e6),
                max_rate_per_s=float(rate.max()),candidates=candidates))
        samples.append(dict(time_us=frame['t']*1e6,rings=rings,
            domain_max_pressure_MPa=float(frame['pressure'].max()/1e6),
            domain_max_rate_per_s=float(frame['reaction_rate'].max())))
        rings_p.append(frame['pressure'][:,rows].copy());rings_rate.append(frame['reaction_rate'][:,rows].copy())
        file=directory/'fields'/f"step_{frame['step']:09d}.npz"
        hashes.append(dict(step=frame['step'],sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    times=np.array([f['time_us']*1e-6 for f in samples])
    tracks=track_candidates(times,[[p['x_m'] for p in f['rings'][0]['candidates']] for f in samples],
                            r['width'],2*c['D_CJ'],r['dx'])
    window=reduce_window(inputs,summary,history,0.,summary['t'])
    assert summary['invalid_state_count']==0
    assert window['budgets']['closure_within_tolerance']
    report=dict(provenance=provenance,continuation=continuation,summary=summary,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        recovered_parent_tail_bytes=len(tail),preserved_history_prefix_bytes=offset,
        window=window,frames=hashes,samples=samples,lower_ring_pressure_candidate_tracks=tracks,
        candidate_definition=dict(pressure_threshold_Pa=2*c['p1'],prominence_Pa=.25*c['p1'],minimum_cells=2,
            maximum_link_speed_mps=2*c['D_CJ'],ambiguity_distance_m=r['dx']),
        interpretation='Pressure candidates are not detonation detections. Tracks break at ambiguities/dropouts. Nearby reaction windows alone do not validate coupling. Original 40 us prefix and source/environment preserved; no physics change.')
    out.mkdir()
    (out/'metrics.json').write_text(json.dumps(report,default=_json_default,indent=2,allow_nan=False)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    fig,axes=plt.subplots(3,2,figsize=(12,10),sharex=True,sharey=True,layout='constrained')
    for row,j in enumerate(rows):
        for col,(values,norm,label) in enumerate([(rings_p,LogNorm(1e5,22e6),'Pressure [Pa]'),
                                                  (rings_rate,LogNorm(1,1e6),'Reaction rate [1/s]')]):
            im=axes[row,col].pcolormesh(x*1e3,times*1e6,np.maximum(np.array(values)[:,:,row],1e-12),
                                      norm=norm,cmap='inferno',shading='nearest')
            axes[row,col].axhline(40,color='cyan',linestyle='--',linewidth=.7)
            axes[row,col].set(ylabel=f'Time [us]; z={z[j]*1e3:.3f} mm',xlabel='Circumferential x [mm]; periodic')
            fig.colorbar(im,ax=axes[row,col],label=label)
    fig.suptitle('Directional startup continued unchanged | cyan line: original 40 us endpoint')
    fig.savefig(out/'space_time.png',dpi=140);plt.close(fig)
    print(json.dumps(dict(status=summary['status'],end_us=summary['t']*1e6,steps=summary['steps'],
        invalid_states=summary['invalid_state_count'],budget=window['budgets']['max_scaled_residual'],
        first_inventory=history[0]['inventory'],final_inventory=history[-1]['inventory'],
        snapshots=[min(samples,key=lambda f:abs(f['time_us']-t)) for t in (40,80,120,160,summary['t']*1e6)]),indent=2))


if __name__=='__main__':main()
