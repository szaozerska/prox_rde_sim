"""Saved-field diagnostics for inspecting pressure/reaction association.

These operators find pressure-peak candidates, not shocks or detonation modes.
No solver import, state modification, calibration, or simulation occurs here.
"""
import hashlib
from pathlib import Path
import numpy as np
from scipy.signal import find_peaks
from analyze import load_saved_run


def periodic_peaks(values, threshold, prominence, minimum_cells=2):
    """Peak cell indices on a periodic ring; plateaus get one representative."""
    values=np.asarray(values,dtype=float)
    if values.ndim!=1 or values.size<3 or not np.isfinite(values).all():
        raise ValueError('a finite ring with at least three cells is required')
    if not np.isfinite([threshold,prominence]).all() or threshold<0 or prominence<=0:
        raise ValueError('nonnegative threshold and positive prominence required')
    if not isinstance(minimum_cells,(int,np.integer)) or not 1<=minimum_cells<=values.size:
        raise ValueError('minimum_cells must be an integer within the ring size')
    n=len(values)
    peaks,_=find_peaks(np.tile(values,3),height=threshold,prominence=prominence)
    peaks=peaks[(peaks>=n)&(peaks<2*n)]-n
    # Apply spacing on the ring itself. Tiled distance pruning can make opposite
    # tie choices in adjacent copies and retain two too-close seam candidates.
    kept=[]
    for index in np.lexsort((peaks,-values[peaks])):
        peak=int(peaks[index])
        if all(abs((peak-other+n/2)%n-n/2)>=minimum_cells for other in kept):
            kept.append(peak)
    return np.asarray(sorted(kept),dtype=int)


def periodic_delta(destination, origin, width):
    return (np.asarray(destination)-np.asarray(origin)+width/2)%width-width/2


def track_candidates(times, positions, width, maximum_speed, ambiguity_distance):
    """Link unambiguous mutual-nearest candidates in adjacent saved frames.

    Missing detections, ambiguous matches, and a possible half-circumference
    displacement break tracks. No interpolation through a collision or dropout.
    Unwrapped distances use the mean-circumference convention of the input ring.
    """
    times=np.asarray(times,dtype=float)
    if times.ndim!=1 or len(times)!=len(positions) or not len(times) or not np.isfinite(times).all() or np.any(np.diff(times)<=0):
        raise ValueError('matching frames and finite increasing times required')
    if not np.isfinite([width,maximum_speed,ambiguity_distance]).all() or min(width,maximum_speed)<=0 or ambiguity_distance<0:
        raise ValueError('positive width/speed and nonnegative ambiguity distance required')
    tracks=[]; previous=np.empty(0); previous_ids=[]; alias_intervals=0
    for frame,(time,locations) in enumerate(zip(times,positions)):
        current=np.asarray(locations,dtype=float)
        if current.ndim!=1 or not np.isfinite(current).all() or np.any(current<0) or np.any(current>=width):
            raise ValueError('candidate locations must lie in [0, circumference)')
        links={}
        if frame and len(previous) and len(current):
            dt=time-times[frame-1]
            if maximum_speed*dt>=width/2:
                alias_intervals+=1
            else:
                displacement=periodic_delta(current[None,:],previous[:,None],width)
                distances=np.abs(displacement)
                distances[distances>maximum_speed*dt]=np.inf
                def unique_nearest(row):
                    order=np.argsort(row)
                    if not len(order) or not np.isfinite(row[order[0]]):
                        return None
                    if len(order)>1 and row[order[1]]-row[order[0]]<=ambiguity_distance:
                        return None
                    return int(order[0])
                forward=[unique_nearest(row) for row in distances]
                backward=[unique_nearest(row) for row in distances.T]
                for old,new in enumerate(forward):
                    if new is not None and backward[new]==old:
                        links[new]=(previous_ids[old],float(displacement[old,new]))
        current_ids=[]
        for index,location in enumerate(current):
            if index in links:
                track_id,delta=links[index]
                previous_sample=tracks[track_id]['samples'][-1]
                unwrapped=previous_sample['unwrapped_x_m']+delta
                speed=delta/(time-previous_sample['time_s'])
            else:
                track_id=len(tracks); tracks.append(dict(id=track_id,samples=[]))
                unwrapped=float(location); speed=None
            tracks[track_id]['samples'].append(dict(frame=frame,time_s=float(time),x_m=float(location),
                                                    unwrapped_x_m=unwrapped,interval_speed_mps=speed))
            current_ids.append(track_id)
        previous,previous_ids=current,current_ids
    for track in tracks:
        samples=track['samples']
        track['fit_speed_mps']=(float(np.polyfit([s['time_s'] for s in samples],
                                               [s['unwrapped_x_m'] for s in samples],1)[0])
                                if len(samples)>=3 else None)
    return dict(tracks=tracks,cadence_ambiguous_intervals=alias_intervals)


def thermal_metrics(pressure, density, rate, q, dx, dz, depth, high_pressure, fill_height):
    """Chemical-to-thermal conversion rho*q*omega [W/m³], not extra energy input.

    Axial quantiles assume uniform conversion within each saved cell. The
    high-pressure fraction measures spatial overlap only, not detonation coupling.
    """
    p,r,w=(np.asarray(a,dtype=float) for a in [pressure,density,rate])
    if p.ndim!=2 or r.shape!=p.shape or w.shape!=p.shape or not p.size:
        raise ValueError('matching nonempty 2D fields required')
    if not all(np.isfinite(a).all() for a in [p,r,w]) or np.any(p<=0) or np.any(r<=0) or np.any(w<0):
        raise ValueError('positive finite pressure/density and nonnegative rate required')
    if not np.isfinite([q,dx,dz,depth,high_pressure]).all() or min(q,dx,dz,depth,high_pressure)<=0:
        raise ValueError('positive finite coefficients and geometry required')
    if fill_height is not None and (not np.isfinite(fill_height) or not 0<fill_height<=p.shape[1]*dz):
        raise ValueError('fill height must lie within the axial domain')
    thermal=r*q*w
    axial=thermal.sum(axis=0); total=float(axial.sum()); z=(np.arange(p.shape[1])+.5)*dz
    if total>0:
        quantiles=np.interp([.1,.5,.9],np.r_[0.,np.cumsum(axial)/total],np.arange(len(z)+1)*dz).tolist()
        fraction=float(thermal[p>=high_pressure].sum()/total)
        below=None if fill_height is None else float(thermal[:,z<fill_height].sum()/total)
    else:
        quantiles=[None]*3; fraction=None; below=None
    return dict(pressure_max_Pa=float(p.max()),reaction_rate_max_per_s=float(w.max()),
                thermal_conversion_W=total*dx*dz*depth,conversion_height_quantiles_m=quantiles,
                conversion_fraction_p_above_threshold=fraction,conversion_fraction_below_initial_fill=below),thermal


def config_differences(left, right, prefix=''):
    differences=[]
    if isinstance(left,dict) and isinstance(right,dict):
        for key in sorted(left.keys()|right.keys()):
            path=f'{prefix}.{key}' if prefix else key
            if key not in left or key not in right:
                differences.append(dict(path=path,left=left.get(key),right=right.get(key)))
            else:
                differences.extend(config_differences(left[key],right[key],path))
    elif left!=right:
        differences.append(dict(path=prefix,left=left,right=right))
    return differences


def inspect_run(directory, heights_mm=(1.,4.,8.,16.), pressure_factor=2., prominence_factor=.25,
                rate_threshold=1000., maximum_speed=None):
    """Read a committed saved prefix and return serializable findings plus plot data."""
    directory=Path(directory)
    data=load_saved_run(directory)
    inputs,summary,fields=(data[key] for key in ['inputs','summary','fields'])
    r=inputs['resolved']; c=inputs['calibration']
    heights=np.asarray(heights_mm,dtype=float)*1e-3
    if heights.ndim!=1 or not heights.size or not np.isfinite(heights).all() or np.any(heights<0) or np.any(heights>=r['length']):
        raise ValueError('requested ring heights must lie inside the domain')
    if not np.isfinite([pressure_factor,prominence_factor,rate_threshold]).all() or min(pressure_factor,prominence_factor,rate_threshold)<=0:
        raise ValueError('positive finite diagnostic thresholds required')
    indices=np.unique(np.minimum((heights/r['dy']).astype(int),r['ny']-1))
    times=np.array([float(f['t']) for f in fields])
    if np.any(np.diff(times)<=0) or any(f['pressure'].shape!=(r['nx'],r['ny']) for f in fields):
        raise ValueError('saved field times/shapes are inconsistent')
    if any('reaction_rate' not in f for f in fields):
        raise ValueError('reaction-rate snapshots are required; missing data are not zero reaction')
    high=pressure_factor*c['p1']; prominence=prominence_factor*c['p1']
    speed=2*c['D_CJ'] if maximum_speed is None else maximum_speed
    fill=inputs['config']['initialization'].get('fill_height_mm')
    fill=None if fill is None else fill*1e-3
    records=[]; axial_heat=[]; axial_pressure=[]; heat_fields=[]
    for time,f in zip(times,fields):
        metrics,heat=thermal_metrics(f['pressure'],f['density'],f['reaction_rate'],c['q'],
                                     r['dx'],r['dy'],r['gap'],high,fill)
        records.append(dict(time_s=float(time),**metrics))
        heat_fields.append(heat); axial_heat.append(heat.mean(axis=0)); axial_pressure.append(f['pressure'].max(axis=0))
    rings=[]
    separation_cells=max(1,min(r['nx'],int(np.ceil(c['L_half']/r['dx']))))
    for index in indices:
        p=np.stack([f['pressure'][:,index] for f in fields])
        progress=np.stack([f['progress'][:,index] for f in fields])
        rates=np.stack([f['reaction_rate'][:,index] for f in fields])
        heat=np.stack([f[:,index] for f in heat_fields])
        frames=[]; positions=[]
        for frame in range(len(times)):
            peaks=periodic_peaks(p[frame],high,prominence,separation_cells)
            reaction=periodic_peaks(rates[frame],rate_threshold,rate_threshold*.1,separation_cells)
            locations=(peaks+.5)*r['dx']; reaction_locations=(reaction+.5)*r['dx']
            candidates=[]
            for peak,location in zip(peaks,locations):
                distances=periodic_delta(reaction_locations,location,r['width'])
                nearest=None if not len(distances) else float(distances[np.argmin(np.abs(distances))])
                neighborhood=np.abs(periodic_delta((np.arange(r['nx'])+.5)*r['dx'],location,r['width']))<=2*c['L_half']
                candidates.append(dict(x_m=float(location),pressure_Pa=float(p[frame,peak]),
                    nearest_reaction_peak_offset_m=nearest,nearby_rate_max_per_s=float(rates[frame,neighborhood].max())))
            frames.append(candidates); positions.append(locations)
        tracks=track_candidates(times,positions,r['width'],speed,2*r['dx'])
        rings.append(dict(z_m=float((index+.5)*r['dy']),index=int(index),candidates=frames,
                          **tracks,pressure=p,progress=progress,thermal_conversion=heat))
    native_conversion=c['q']*summary['budgets']['source_integral'][4]
    sampled_conversion=float(np.trapezoid([row['thermal_conversion_W'] for row in records],times)) if len(times)>1 else None
    report=dict(directory=str(directory.resolve()),status=summary['status'],prefix_step=summary['steps'],time_s=summary['t'],
        snapshot_count=len(fields),inputs_sha256=hashlib.sha256((directory/'inputs.json').read_bytes()).hexdigest(),
        numerical_implementation=inputs['implementation'],diagnostics_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        definitions=dict(thermal_conversion='rho*q*reaction_rate, W/m^3; internal chemical-to-thermal conversion, not an added total-energy source',
            pressure_threshold_Pa=high,pressure_prominence_Pa=prominence,rate_peak_threshold_per_s=rate_threshold,
            rate_peak_prominence_per_s=rate_threshold*.1,minimum_peak_spacing_cells=separation_cells,
            maximum_tracking_speed_mps=float(speed),ambiguity_distance_m=2*r['dx'],
            nearby_rate_radius_m=2*c['L_half'],height_quantile_method='uniform conversion within each axial cell',
            reaction_offset='nearest qualifying reaction-rate peak minus pressure-peak position; signed shortest periodic distance, not a measured reaction-zone length',
            interpretation='Pressure-peak tracks and spatial overlap are diagnostics, not confirmed shocks, detonation passages, wave counts, or engine validation.'),
        snapshots=records,native_chemical_conversion_J=native_conversion,snapshot_trapezoid_conversion_J=sampled_conversion,
        confirmed_detonation_passages=None,
        rings=[{k:v for k,v in ring.items() if k not in ['pressure','progress','thermal_conversion']} for ring in rings])
    arrays=dict(saved=data,times=times,rings=rings,heat_fields=heat_fields,axial_heat=np.array(axial_heat),axial_pressure=np.array(axial_pressure))
    return report,arrays


def compare_inputs(left, right):
    """Expose every changed case input before interpreting a comparison."""
    return dict(config_differences=config_differences(left['config'],right['config']),
                identical_calibration=left['calibration']==right['calibration'],
                identical_numerical_implementation=left['implementation']==right['implementation'],
                initialization_energy_change_J=[left['resolved'].get('initialization_energy_change_J'),
                                                 right['resolved'].get('initialization_energy_change_J')])
