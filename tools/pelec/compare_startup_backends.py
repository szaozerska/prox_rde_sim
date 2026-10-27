"""Compare native fields and integration timings for a matched chemistry-backend test."""
import argparse, json, re, statistics
from pathlib import Path
import numpy as np


def compare(reference, candidate, criteria, output):
    reference, candidate = Path(reference), Path(candidate)
    bounds = json.loads(Path(criteria).read_text())
    for p in (reference, candidate):
        if not json.loads((p/'result.json').read_text())['completed']:
            raise ValueError('Both native integrations must complete')
    configs = [json.loads((p/'case.json').read_text()) for p in (reference,candidate)]
    normalize = lambda c: [s for s in c['inputs'].splitlines() if not s.startswith('cvode.solve_type')]
    if normalize(configs[0]) != normalize(configs[1]):raise ValueError('Unmatched flow/chemistry inputs')
    commands = [json.loads((p/'allocation.json').read_text())['command'] for p in (reference,candidate)]
    restarts = [[s for s in command if s.startswith('amr.restart=')] for command in commands]
    if len(restarts[0]) != 1 or restarts[0] != restarts[1]:
        raise ValueError('Different restart checkpoints')
    arrays=[]
    for p in (reference,candidate):
        with np.load(p/'preview.npz') as data:arrays.append({k:data[k] for k in data.files})
    a,b=arrays
    for k in ('time_s','theta_rad','z_m'):
        if not np.array_equal(a[k],b[k]):raise ValueError('Unmatched native sampling')
    report={}
    for k in ('pressure_Pa','temperature_K','methane_Y','oxygen_Y','heat_release_W_m3'):
        delta=b[k]-a[k]
        report[k]={'max_absolute_difference':float(np.max(np.abs(delta))),
            'relative_l2_difference':float(np.linalg.norm(delta.ravel())/max(np.linalg.norm(a[k].ravel()),1e-30))}
    audits=[json.loads((p/'checks.json').read_text()) for p in (reference,candidate)]
    report['inventory_relative_differences']={k:abs(audits[1]['rows'][-1][k]-audits[0]['rows'][-1][k])/max(abs(audits[0]['rows'][-1][k]),1e-30)
        for k in ('mass_kg','methane_kg','oxygen_kg','total_energy_J')}
    timing=[]
    for p in (reference,candidate):
        times=[float(v) for v in re.findall(r'Coarse TimeStep time: (\S+)',(p/'solver.log').read_text())]
        timing.append({'steps':len(times),'median_seconds':statistics.median(times),'total_seconds':sum(times)})
    report['timing']={'reference':timing[0],'candidate':timing[1],'median_ratio':timing[1]['median_seconds']/timing[0]['median_seconds']}
    report['every_step_species']=[a['every_step_species'] for a in audits]
    checks={
        'pressure':report['pressure_Pa']['relative_l2_difference']<=bounds['max_pressure_relative_l2'],
        'temperature':report['temperature_K']['max_absolute_difference']<=bounds['max_temperature_absolute_difference_K'],
        'major_species':max(report[k]['max_absolute_difference'] for k in ('methane_Y','oxygen_Y'))<=bounds['max_major_species_absolute_difference'],
        'inventories':max(report['inventory_relative_differences'].values())<=bounds['max_inventory_relative_difference'],
        'finite_and_closure':all(a['checks'][k] for a in audits for k in ('finite','species_sum','positive_pressure','thermo_range')),
        'speedup':report['timing']['median_ratio']<=bounds['max_step_time_ratio_for_adoption']}
    report.update(checks=checks,meets_recorded_criteria=all(checks.values()),physical_validation_passed=False,
        scope='Short matched backend comparison; review undershoots and heat release separately. Not engine validation.')
    Path(output).write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('reference','candidate','criteria','output'):p.add_argument(k)
    print(json.dumps(compare(**vars(p.parse_args())),indent=2))
