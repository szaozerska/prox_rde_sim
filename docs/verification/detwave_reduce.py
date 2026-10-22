"""Read-only reduction of bounded study checkpoints; no automatic wave verdict.

Usage: python docs/verification/detwave_reduce.py RUN_DIRECTORY NEW_JSON
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'rde_sim_starter'))
from coupling import periodic_peaks, periodic_delta, track_candidates


def reduce(directory):
    directory=Path(directory);manifest=json.loads((directory/'inputs.json').read_text())
    c=manifest['calibration'];r=manifest['resolved'];width=r['width'];dx=r['dx']
    with np.load(directory/'checkpoint.npz',allow_pickle=False) as a:
        times=a['times'].copy();rings=a['rings'].copy()
        history=json.loads(str(a['history']));end=float(a['t']);steps=int(a['steps'])
    x=(np.arange(r['nx'])+.5)*dx;result=[]
    for row,height in enumerate(manifest['actual_ring_heights_m']):
        positions=[];candidates=[]
        for frame in rings:
            p=frame[3,:,row];rate=frame[5,:,row]
            peaks=periodic_peaks(p,2*c['p1'],.25*c['p1'],max(2,round(c['L_half']/dx)))
            reaction=periodic_peaks(rate,1000.,100.,2)
            positions.append(x[peaks]);entries=[]
            for peak in peaks:
                offset=periodic_delta(x[reaction],x[peak],width)
                region=abs(periodic_delta(x,x[peak],width))<=.002
                entries.append(dict(x_m=float(x[peak]),pressure_Pa=float(p[peak]),
                    rate_within_2mm_per_s=float(rate[region].max()),
                    nearest_rate_peak_offset_m=float(offset[np.argmin(abs(offset))]) if len(offset) else None))
            candidates.append(entries)
        tracked=track_candidates(times,positions,width,4000.,2*dx)
        for track in tracked['tracks']:
            samples=track['samples'];start=samples[0];last=samples[-1]
            track['net_circumferences']=(last['unwrapped_x_m']-start['unwrapped_x_m'])/width
            for sample in samples:
                frame=sample['frame'];ix=int(np.argmin(abs(periodic_delta(positions[frame],sample['x_m'],width))))
                sample.update(candidates[frame][ix])
                speed=sample['interval_speed_mps']
                if speed is not None:
                    ahead=(sample['x_m']+np.sign(speed)*.003)%width
                    cell=min(int(ahead/dx),r['nx']-1);w=rings[frame,:,cell,row]
                    sample['ahead_3mm_progress']=float(w[4])
                    sample['ahead_3mm_temperature_K']=float(w[3]/(w[0]*c['R']))
                    sample['apparent_relative_Mach']=float(abs(speed-w[1])/np.sqrt(c['gamma']*w[3]/w[0]))
        result.append(dict(height_m=height,pressure_max_Pa=rings[:,3,:,row].max(axis=1).tolist(),
            rate_max_per_s=rings[:,5,:,row].max(axis=1).tolist(),**tracked))
    return dict(directory=str(directory.resolve()),time_s=end,steps=steps,
        inputs_sha256=hashlib.sha256((directory/'inputs.json').read_bytes()).hexdigest(),
        diagnostic_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        times_s=times.tolist(),history=history,
        max_budget_scaled_residual=max(h['budget_scaled_residual'] for h in history),
        rings=result,interpretation='Pressure peaks are candidates, not confirmed shock fronts. '
        'A track may break or switch physical structures; inspect fields. No automatic detonation verdict. '
        'Nearby rates use a fixed 2 mm radius; relative Mach samples 3 mm ahead, which may not be undisturbed gas.')


if __name__=='__main__':
    output=Path(sys.argv[2])
    with output.open('x') as f:json.dump(reduce(sys.argv[1]),f,indent=2,allow_nan=False);f.write('\n')
