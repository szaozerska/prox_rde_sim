"""Read-only native-history window reports; imports never run CFD or render.

Partial steps use constant step-average transport and linear inventory interpolation.
The annulus-exit force contribution is not a whole-engine thrust measurement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from analyze import weighted_mean

CONSERVED = ['mass', 'azimuthal_momentum', 'axial_momentum', 'total_energy', 'reacted_mass']


def _array(rows, key, shape):
    """Missing values are unavailable; malformed supplied values are errors."""
    values=[];missing=False
    for row in rows:
        if key not in row or row[key] is None:
            missing=True
            continue
        value=np.asarray(row[key],dtype=float)
        if value.shape!=shape or not np.isfinite(value).all():
            raise ValueError(f'{key}: expected finite values with shape {shape}')
        values.append(value)
    return None if missing else np.asarray(values)


def unavailable(reason):
    return dict(available=False,reason=reason)


def reduce_window(inputs, summary, history, start, end):
    """Reduce a committed native prefix, with all integrals already in SI units."""
    if len(history)<2:
        raise ValueError('a positive-duration committed history is required')
    times=_array(history,'t',())
    dt=_array(history[1:],'dt',())
    steps=[row.get('step') for row in history]
    if (times is None or dt is None or times[0]!=0 or np.any(np.diff(times)<=0)
            or steps!=list(range(len(history)))
            or any(not isinstance(v,int) or isinstance(v,bool) for v in steps)
            or summary['steps']!=steps[-1] or summary['t']!=times[-1]):
        raise ValueError('history must be a consecutive increasing prefix matching summary')
    widths=np.diff(times)
    tolerance=64*np.finfo(float).eps*np.maximum(abs(times[1:]),widths)
    if np.any(dt<=0) or np.any(abs(dt-widths)>tolerance):
        raise ValueError('saved dt does not match consecutive accepted timestamps')
    if not np.isfinite([start,end]).all() or not times[0]<=start<end<=times[-1]:
        raise ValueError('window must be finite, positive and entirely within the committed history')
    duration=end-start
    weights=np.maximum(0.,np.minimum(times[1:],end)-np.maximum(times[:-1],start))
    fraction=weights/widths
    selected=weights>0
    partial=int(np.sum(selected & (fraction<1-64*np.finfo(float).eps)))
    r=inputs['resolved'];width=float(r['width']);gap=float(r['gap']);radius=float(r['r_mean'])
    ambient=float(r['p_back'])
    if not np.isfinite([width,gap,radius,ambient]).all() or min(width,gap,radius)<=0 or ambient<0:
        raise ValueError('positive finite annulus dimensions and nonnegative back pressure required')
    area=width*gap
    boundary=_array(history[1:],'boundary_integral',(4,5))
    source=_array(history[1:],'source_integral',(5,))
    inventory=_array(history,'inventory',(5,))
    B=np.einsum('t,tij->ij',fraction,boundary) if boundary is not None else None
    S=np.einsum('t,ti->i',fraction,source) if source is not None else None
    budget=unavailable('inventory, per-step boundary and source integrals are all required throughout the committed prefix')
    control_force=unavailable('native inventory, boundary and source integrals are required')
    if B is not None and S is not None and inventory is not None:
        first=np.array([np.interp(start,times,component) for component in inventory.T])
        last=np.array([np.interp(end,times,component) for component in inventory.T])
        storage=last-first;net=B[0]-B[1]+B[2]-B[3]+S
        residual=storage-net
        # Avoid declaring roundoff a failure when net momentum is almost zero.
        # sqrt(mass * total energy) has momentum units; no assumed wave speed.
        mass=max(abs(first[0]),abs(last[0]));energy=max(abs(first[3]),abs(last[3]))
        momentum=np.sqrt(mass)*np.sqrt(energy)
        reference=np.array([mass,momentum,momentum,energy,mass])
        scale=np.maximum.reduce([abs(first),abs(last),abs(storage),abs(net),reference,np.full(5,1e-30)])
        error=float(np.max(abs(residual)/scale))
        budget=dict(available=True,conserved_order=CONSERVED,
            conserved_units=['kg','kg m/s','kg m/s','J','kg'],
            start_inventory=first,end_inventory=last,storage=storage,
            boundary_integral=B,source_integral=S,net_influx_and_source=net,residual=residual,
            residual_scale=scale,scale_definition='inventory/transport scale with sqrt(mass * total energy) momentum reference',
            max_scaled_residual=error,closure_tolerance=1e-10,closure_within_tolerance=error<=1e-10,
            angular_storage_kg_m2_s=float(radius*storage[1]),
            angular_net_influx_kg_m2_s=float(radius*net[1]),
            angular_residual_kg_m2_s=float(radius*residual[1]))
        # Reconstruct the same exit contribution from the control-volume identity.
        # Storage is subtracted, never assumed zero. These two force estimates are not additive.
        impulse=B[0,2]-B[1,2]+B[2,2]+S[2]-storage[2]-ambient*area*duration
        control_force=dict(available=True,mean_N=float(impulse/duration),impulse_N_s=float(impulse))
    force=unavailable('native boundary integrals are missing from the committed prefix')
    mass_flow=unavailable('native boundary integrals are missing from the committed prefix')
    isp=unavailable('native exit force and positive net injected propellant mass are required')
    if B is not None:
        impulse=float(B[3,2]-ambient*area*duration)
        force=dict(available=True,mean_N=impulse/duration,impulse_N_s=impulse,
                   ambient_pressure_Pa=ambient,exit_area_m2=area,
                   definition='top-face numerical axial momentum flux minus ambient pressure times exit area')
        mass_flow=dict(available=True,injected_mass_kg=float(B[2,0]),exited_mass_kg=float(B[3,0]),
            mean_inlet_kg_s=float(B[2,0]/duration),mean_outlet_kg_s=float(B[3,0]/duration))
        if B[2,0]>0:
            isp=dict(available=True,value_s=float(impulse/(B[2,0]*9.80665)),g0_m_s2=9.80665,
                definition='annulus-exit effective Isp: exit impulse / (net injected mass in same window * g0); not whole-engine Isp')
        if control_force['available']:
            control_force['native_minus_balance_mean_N']=force['mean_N']-control_force['mean_N']
    cell_force=_array(history[1:],'exit_cell_force_estimate_N',())
    cell_result=unavailable('cell-centre exit estimates were not saved throughout the committed prefix')
    if cell_force is not None:
        cell_result=dict(available=True,mean_N=float(weighted_mean(cell_force,weights)),
            definition='step-end cell-centre estimate; rectangle-rule time average, not the RK numerical face flux')
    stations=r.get('pressure_stations',[])
    pressure=unavailable('pressure stations were not saved')
    if len(stations):
        values=_array(history[1:],'pressure_stations',(len(stations),))
        if values is not None:
            pressure=dict(available=True,stations_m=stations,mean_Pa=weighted_mean(values,weights),
                          definition='step-end circumferential means, weighted by interval overlap')
    conversion=unavailable('native source integrals and a positive finite heat release are required')
    q=inputs.get('calibration',{}).get('q')
    if q is not None and (not np.isfinite(q) or q<=0):raise ValueError('invalid saved heat release')
    if S is not None and q is not None:
        conversion=dict(available=True,chemical_to_thermal_J=float(q*S[4]),
                        definition='q times reacted-mass source; internal conversion, not an extra total-energy source')
    torque=unavailable('no wall-traction model; angular conservation residual is not engine torque')
    if inputs.get('config', {}).get('model', {}).get('walls') in ('constant_cf','annular_closure'):
        if budget['available']:
            angular_impulse = -radius * S[1]
            balance_impulse = radius * (B[0,1]-B[1,1]+B[2,1]-B[3,1]-storage[1])
            torque=dict(available=True, mean_Nm=float(angular_impulse/duration),
                angular_impulse_Nm_s=float(angular_impulse),
                balance_mean_Nm=float(balance_impulse/duration),
                traction_minus_balance_Nm=float((angular_impulse-balance_impulse)/duration),
                wall_cf=inputs['config']['model'].get('wall_cf'),
                radial_assumptions=inputs['config']['model'].get('radial'),
                definition='reaction torque on engine = negative native wall momentum source times mean radius',
                qualification='constant-Cf closure, unvalidated; mean-radius approximation; see radial assumptions for heat exchange; no vehicle stability claim')
        else:
            torque=unavailable('native storage/flux/source needed for the applied wall model')
    wall_exchange=unavailable('separate radial wall integrals were not saved')
    wall_steps=_array(history[1:],'radial_wall_integral',(2,3))
    if wall_steps is not None:
        integrated=np.einsum('t,tij->ij',fraction,wall_steps)
        actual=float(-np.dot([radius-gap/2,radius+gap/2],integrated[:,0])/duration)
        wall_exchange=dict(available=True,inner_outer_integrals=integrated,
            columns=['theta_momentum_kg_m_s','axial_momentum_kg_m_s','energy_to_gas_J'],
            heat_to_gas_J=float(integrated[:,2].sum()),
            actual_radius_traction_moment_Nm=actual,
            actual_minus_mean_radius_moment_Nm=actual-torque['mean_Nm'] if torque['available'] else None,
            qualification='actual-radius traction reconstruction; solver angular inventory uses mean radius, so these moments are not interchangeable')
    return dict(report_schema_version=1,run_status=summary.get('status','unknown'),
        run_mode=summary.get('run_mode','engine_intervals'),
        run_invalid_state_count=summary.get('invalid_state_count'),
        committed_end_s=float(times[-1]),window=dict(start_s=start,end_s=end,duration_s=duration,
            contributing_steps=int(selected.sum()),partially_included_steps=partial,
            operator='native integrals prorated within partial steps; inventory linearly interpolated between accepted states; other samples use step-end rectangles',
            qualification='partial-step closure checks this interpolation, not an independently evolved state'),
        budgets=budget,mass_flow=mass_flow,exit_numerical_force=force,
        exit_force_from_control_volume=control_force,exit_cell_force_estimate=cell_result,
        annulus_exit_effective_isp=isp,pressure_stations=pressure,chemical_conversion=conversion,
        engine_torque=torque, radial_wall_exchange=wall_exchange,
        physical_validation='not established by this report; transient window, no steady-state or sustained-detonation classification')


def load_native_prefix(directory):
    """Read metadata and native history only, never full fields or checkpoint U."""
    directory=Path(directory)
    input_bytes=(directory/'inputs.json').read_bytes()
    summary_bytes=(directory/'summary.json').read_bytes()
    inputs=json.loads(input_bytes);summary=json.loads(summary_bytes)
    if inputs.get('format_version')!=2 or summary.get('format_version')!=2:
        raise ValueError('native runner format_version 2 is required; other backends need an explicit adapter')
    steps=summary['steps']
    if not isinstance(steps,int) or isinstance(steps,bool) or steps<0:
        raise ValueError('invalid summary step count')
    rows=[];prefix=bytearray()
    with (directory/'history.jsonl').open('rb') as stream:
        for _ in range(steps+1):
            line=stream.readline()
            if not line.endswith(b'\n'):raise ValueError('missing complete committed history row')
            rows.append(json.loads(line));prefix.extend(line)
    digest=hashlib.sha256(input_bytes).hexdigest()
    with np.load(directory/'checkpoint.npz',allow_pickle=False) as saved:
        metadata=json.loads(str(saved['state_json']))
    if (metadata.get('format_version')!=2 or metadata['inputs_sha256']!=digest
            or metadata['steps']!=steps or metadata['t']!=summary['t']
            or metadata['history_bytes']!=len(prefix)):
        raise ValueError('checkpoint, inputs, summary and history prefix do not agree')
    if (input_bytes!=(directory/'inputs.json').read_bytes()
            or summary_bytes!=(directory/'summary.json').read_bytes()):
        raise ValueError('run changed during read; retry after a complete checkpoint')
    provenance=dict(directory=str(directory.resolve()),inputs_sha256=digest,
        summary_sha256=hashlib.sha256(summary_bytes).hexdigest(),
        committed_history_sha256=hashlib.sha256(prefix).hexdigest(),
        committed_history_bytes=len(prefix),checkpoint_step=steps,
        report_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        analysis_source_sha256=hashlib.sha256(Path(__file__).with_name('analyze.py').read_bytes()).hexdigest())
    return inputs,summary,rows,provenance


def report_saved_window(directory,start,end):
    inputs,summary,rows,provenance=load_native_prefix(directory)
    return dict(reduce_window(inputs,summary,rows,start,end),provenance=provenance)


def _json_default(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(f'cannot serialize {type(value)}')


def render_markdown(report):
    w=report['window'];lines=['# Saved-window report','',
        f"Window: {w['start_s']*1e6:g}–{w['end_s']*1e6:g} µs; mode: {report['run_mode']}; saved run status: {report['run_status']}.",'',
        'Physical validation: '+report['physical_validation']+'.',
        f"Saved invalid-state count: {report['run_invalid_state_count']}.",'',
        '| Quantity | Result |','|---|---|']
    for title,item,key,unit in [
        ('Mean modeled engine wall torque',report['engine_torque'],'mean_Nm','N m'),
        ('Mean native annulus-exit force',report['exit_numerical_force'],'mean_N','N'),
        ('Mean exit force from control-volume balance',report['exit_force_from_control_volume'],'mean_N','N'),
        ('Mean cell-centre exit estimate',report['exit_cell_force_estimate'],'mean_N','N'),
        ('Mean inlet mass flow',report['mass_flow'],'mean_inlet_kg_s','kg/s'),
        ('Mean outlet mass flow',report['mass_flow'],'mean_outlet_kg_s','kg/s'),
        ('Annulus-exit effective Isp',report['annulus_exit_effective_isp'],'value_s','s'),
        ('Chemical-to-thermal conversion',report['chemical_conversion'],'chemical_to_thermal_J','J'),
        ('Maximum scaled conservation residual',report['budgets'],'max_scaled_residual','')]:
        value=f"{item[key]:.8g} {unit}" if item['available'] else 'Unavailable: '+item['reason']
        lines.append(f'| {title} | {value} |')
    if 'provenance' in report:
        p=report['provenance']
        lines+=['',f"Source: `{p['directory']}`; committed step {p['checkpoint_step']}.",
                f"Input SHA-256: `{p['inputs_sha256']}`."]
    pressure=report['pressure_stations']
    if pressure['available']:
        lines+=['','| Axial station [mm] | Window mean pressure [kPa] |','|---|---:|']
        lines += [f'| {z*1e3:g} | {value/1e3:.8g} |' for z,value in zip(pressure['stations_m'],pressure['mean_Pa'])]
        lines+=['','These are transient station means, not a comparison to experimental long-window averages.']
    b=report['budgets']
    if b['available']:
        lines+=['','| Conserved quantity | Storage change | Net influx + source | Residual |','|---|---:|---:|---:|']
        for i,(name,unit) in enumerate(zip(b['conserved_order'],b['conserved_units'])):
            lines.append(f"| {name} [{unit}] | {b['storage'][i]:.8g} | {b['net_influx_and_source'][i]:.8g} | {b['residual'][i]:.3g} |")
        lines+=['',f"Budget closure within {b['closure_tolerance']:g}: **{b['closure_within_tolerance']}**."]
    lines+=['',f"{w['contributing_steps']} contributing steps; {w['partially_included_steps']} partially included.",
        w['operator']+'.',w['qualification']+'.','',
        'Native and control-volume exit forces describe the same contribution; do not add them. These are not whole-engine thrust estimates.',
        'Effective Isp uses net injected mass over this same window; it is not validated engine performance.',
        ('Engine torque: '+report['engine_torque']['qualification'] if report['engine_torque']['available']
         else 'Engine torque unavailable: '+report['engine_torque']['reason'])+'.','']
    return '\n'.join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--start-us',type=float,required=True)
    parser.add_argument('--end-us',type=float,required=True)
    parser.add_argument('--out',type=Path,required=True,help='new report directory, outside saved run')
    args=parser.parse_args(argv)
    try:
        if args.out.resolve().is_relative_to(args.run.resolve()):
            raise ValueError('report output must be outside the saved run directory')
        report=report_saved_window(args.run,args.start_us*1e-6,args.end_us*1e-6)
        encoded=json.dumps(report,default=_json_default,indent=2,allow_nan=False)+'\n'
        markdown=render_markdown(report)
        args.out.mkdir(parents=True,exist_ok=False)
        (args.out/'report.json').write_text(encoded)
        (args.out/'report.md').write_text(markdown)
    except (ValueError,TypeError,KeyError,OSError) as error:
        parser.exit(2,f'Report stopped: {error}\n')
    print(args.out)


if __name__=='__main__':main()
