"""Read-only assembly of the reduced-2D workflow's reports and comparisons.

Rendering lives in plot.py. Native runs and checkpoints are never modified.
"""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from contracts import iter_fields
from window_report import load_native_prefix, reduce_window, _json_default, render_markdown, unavailable
from workflow_analysis import pressure_spectrum, pressure_spectrogram, run937_reference, roll_response


def collect_workflow(directory, start, end, segment_s=None, inertia=None):
    inputs, summary, rows, provenance = load_native_prefix(directory)
    report = dict(reduce_window(inputs, summary, rows, start, end), provenance=provenance)
    report['experimental_comparison'] = run937_reference(inputs['config'], inputs['resolved'], report)
    radial = inputs['config']['model'].get('radial')
    report['radial_physics'] = dict(radial_momentum=False, radial_velocity=False,
        centrifugal_pressure_split=bool(radial and radial['centrifugal']), curvature_loss=False,
        heat_loss=bool(radial and radial['analogy_factor'] > 0 and (radial['inner']['cf'] > 0 or radial['outer']['cf'] > 0)),
        separate_inner_outer_wall_states=radial is not None, radial_assumptions=radial,
        wall_drag=inputs['config']['model']['walls'],
        qualification='surface (theta,z) model; optional quasi-steady radial equilibrium and wall sources do not resolve radial motion or detachment')
    t = np.asarray([row['t'] for row in rows])
    if all('probe_pressure_Pa' in row for row in rows):
        p = np.asarray([row['probe_pressure_Pa'] for row in rows])
        spectrum = pressure_spectrum(t,p,start,end)
        spectrogram = pressure_spectrogram(t,p,start,end,(end-start)/4 if segment_s is None else segment_s)
    else:
        spectrum = unavailable('native local pressure probe was not saved')
        spectrogram = dict(segments=[], reason=spectrum['reason'])
    report['pressure_spectrum'] = spectrum
    report['pressure_spectrogram'] = spectrogram
    report['roll_response'] = unavailable('provide positive inertia_kg_m2 and an applied wall-friction model')
    if inertia is not None:
        if not np.isfinite(inertia) or inertia <= 0:
            raise ValueError('inertia must be finite and positive')
        if report['engine_torque']['available']:
            duration = np.diff(t)
            overlap = np.maximum(0,np.minimum(t[1:],end)-np.maximum(t[:-1],start))
            selected = overlap > 0
            # Chemical reaction has no momentum source; this backend's sole theta source is drag.
            impulses = -inputs['resolved']['r_mean'] * np.array([row['source_integral'][1] for row in rows[1:]])
            edges = np.r_[start, np.minimum(t[1:][selected],end)]
            report['roll_response'] = dict(available=True, **roll_response(edges,
                impulses[selected]*overlap[selected]/duration[selected],inertia))
    r = inputs['resolved']; ring_t=[]; pressure=[]; rate=[]; steps=[]
    pmin=float('inf');pmax=0.;ratemax=0.
    for frame in iter_fields(directory,inputs,summary['steps']):
        if frame['t'] > summary['t']:
            raise ValueError('snapshot exceeds committed time')
        if not start <= frame['t'] <= end:
            continue
        steps.append(frame['step']);ring_t.append(frame['t'])
        pressure.append(frame['pressure'][:,r['probe_index']].copy())
        rate.append(frame['reaction_rate'][:,r['probe_index']].copy())
        pmin=min(pmin,float(frame['pressure'].min()));pmax=max(pmax,float(frame['pressure'].max()))
        ratemax=max(ratemax,float(frame['reaction_rate'].max()))
    report['preview'] = dict(snapshot_count=len(steps), selected_step_ids=steps,
        field_window_s=[start,end], pressure_range_Pa=[pmin,pmax] if steps else None,
        reaction_rate_max_per_s=ratemax,
        interpretation='saved snapshots only; animation uses uniform playback intervals, timestamps retain actual time')
    report['provenance']['field_reader_source_sha256'] = hashlib.sha256(Path(__file__).with_name('contracts.py').read_bytes()).hexdigest()
    report['provenance']['workflow_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['provenance']['plot_source_sha256'] = hashlib.sha256(Path(__file__).with_name('plot.py').read_bytes()).hexdigest()
    report['provenance']['workflow_analysis_sha256'] = hashlib.sha256(Path(__file__).with_name('workflow_analysis.py').read_bytes()).hexdigest()
    return dict(report=report,inputs=inputs,summary=summary,rows=rows,
        ring_times=np.asarray(ring_t),ring_pressure=np.asarray(pressure),ring_rate=np.asarray(rate))


def _settings(config):
    result={}
    def visit(prefix, value):
        if isinstance(value,dict):
            for key, child in value.items(): visit(prefix+'.'+key,child)
        else: result[prefix]=value
    for key in ('geometry','operating_point','model','chemistry','numerics','initialization'):
        visit(key,config.get(key,{}))
    return result


def compare_saved_runs(directories, start, end):
    """Shared-window sensitivity table; no automatic experiments or refitting."""
    if len(directories)<2 or len({str(Path(p).resolve()) for p in directories})!=len(directories):
        raise ValueError('comparison needs at least two distinct saved runs')
    rows=[]; baseline=None; baseline_implementation=None
    for directory in directories:
        inputs, summary, history, provenance=load_native_prefix(directory)
        report=reduce_window(inputs,summary,history,start,end)
        settings=_settings(inputs['config'])
        implementation=inputs.get('implementation')
        if baseline is None:
            baseline=settings; baseline_implementation=implementation
        differences={key:dict(baseline=baseline.get(key),value=settings.get(key))
            for key in sorted(baseline.keys()|settings.keys()) if baseline.get(key)!=settings.get(key)}
        missing={}
        def metric(name,key):
            item=report[name]
            if not item['available']: missing[name]=item['reason']
            return item.get(key) if item['available'] else None
        rows.append(dict(run=str(Path(directory).resolve()),inputs_sha256=provenance['inputs_sha256'],
            start_s=start,end_s=end,status=summary['status'],run_mode=report['run_mode'],
            implementation_sha256=hashlib.sha256(json.dumps(implementation,sort_keys=True).encode()).hexdigest() if implementation is not None else None,
            recorded_implementation_matches_baseline=implementation is not None and implementation==baseline_implementation,
            invalid_state_count=summary['invalid_state_count'],
            native_exit_force_N=metric('exit_numerical_force','mean_N'),
            wall_torque_Nm=metric('engine_torque','mean_Nm'),
            inlet_kg_s=metric('mass_flow','mean_inlet_kg_s'),
            max_scaled_budget_residual=metric('budgets','max_scaled_residual'),
            changed_settings=differences,one_setting_changed=len(differences)==1,unavailable_metrics=missing))
    return dict(schema_version=1,rows=rows,
        qualification='shared-window transient comparison; changed code/environment or multiple changed settings confound single-parameter attribution; no convergence or experimental-validation claim')


def write_data(data, destination, comparison=None):
    """Write into an already-created new report directory, never a native run."""
    destination=Path(destination);report=data['report']
    (destination/'report.json').write_text(json.dumps(report,default=_json_default,indent=2,allow_nan=False)+'\n')
    extra=['','## Workflow qualifications','',report['radial_physics']['qualification'],
        'Resolved radial momentum and curvature losses are absent. Enabled closures: '
        + ', '.join(f'{key}={report["radial_physics"][key]}' for key in
            ('centrifugal_pressure_split', 'heat_loss', 'separate_inner_outer_wall_states', 'wall_drag')) + '.',
        'Spectral peaks are pressure oscillations, not a detected detonation mode.']
    reference=report['experimental_comparison']
    if reference['available']:
        extra += ['',reference['qualification'],'','| z [mm] | Model window [kPa] | Experiment [kPa] | Difference [%] |','|---|---|---|---|']
        extra += [f'| {z*1e3:g} | {m/1e3:.6g} | {e/1e3:.6g} | {d:.4g} |' for z,m,e,d in zip(
            reference['stations_m'],reference['model_window_mean_Pa'],reference['experimental_mean_Pa'],reference['discrepancy_percent'])]
    else: extra += ['','Experimental pressure comparison unavailable: '+reference['reason']]
    extra += ['','See `index.html` for saved field playback, views and numerical plots. No simulation runs in the viewer.']
    (destination/'report.md').write_text(render_markdown(report)+'\n'.join(extra)+'\n')
    with (destination/'history.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['time_s','step','local_pressure_Pa','native_exit_force_N','modeled_wall_torque_Nm'])
        start,end=report['window']['start_s'],report['window']['end_s']
        for row in data['rows']:
            if start<=row['t']<=end:
                writer.writerow([row['t'],row['step'],row.get('probe_pressure_Pa'),row.get('exit_numerical_force_N'),row.get('wall_engine_torque_Nm')])
    if comparison is not None:
        (destination/'comparison.json').write_text(json.dumps(comparison,default=_json_default,indent=2,allow_nan=False)+'\n')
        with (destination/'comparison.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(comparison['rows'][0]));writer.writeheader()
            for row in comparison['rows']:
                writer.writerow(dict(row,changed_settings=json.dumps(row['changed_settings'],sort_keys=True),
                    unavailable_metrics=json.dumps(row['unavailable_metrics'],sort_keys=True)))
