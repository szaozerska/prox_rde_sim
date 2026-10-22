"""Summarize saved native methane control checks, without launching simulations."""
import argparse
import json
from pathlib import Path
import numpy as np


def compare(left,right):
    pairs=[]
    for a in left['records']:
        matches=[b for b in right['records'] if abs(a['time']-b['time'])<1e-18]
        if len(matches)>1:raise ValueError('Ambiguous field-time comparison')
        if matches:pairs.append((a,matches[0]))
    if len(pairs)<10:raise ValueError('Insufficient shared field samples')
    return dict(common_field_samples=len(pairs),
        temperature_relative_max_difference=max(abs(a['temperature_K']/b['temperature_K']-1) for a,b in pairs),
        pressure_relative_max_difference=max(abs(a['pressure_Pa']/b['pressure_Pa']-1) for a,b in pairs),
        species_absolute_max_difference=max(float(np.max(abs(np.array(a['Y'])-b['Y']))) for a,b in pairs))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('gpu','cpu','halfdt','tolerance','output'):p.add_argument(name,type=Path)
    args=p.parse_args();reports={};runs={}
    for label in ('gpu','cpu','halfdt','tolerance'):
        path=getattr(args,label)
        report_path=path/'reactor_checks_native_constants_common.json'
        if not report_path.exists():report_path=path/'reactor_checks_native_constants.json'
        reports[label]=json.loads(report_path.read_text())
        runs[label]=json.loads((path/'result.json').read_text())
    comparisons={label:compare(reports['gpu'],reports[label]) for label in ('cpu','halfdt','tolerance')}
    checks={'all_native_field_reference_checks':all(r['passed'] for r in reports.values())}
    for label,result in comparisons.items():
        checks[label+'_within_reference_budget']=(result['temperature_relative_max_difference']<2e-5 and
            result['pressure_relative_max_difference']<2e-5 and result['species_absolute_max_difference']<2e-6)
    result=dict(numerical_control_passed=all(checks.values()),checks=checks,comparisons=comparisons,
        runs={name:{k:runs[name][k] for k in ('backend','dt','rtol','atol','wall_seconds','completion_passed')} for name in runs},
        max_all_step_temperature_error={name:r['max_history_temperature_relative_error'] for name,r in reports.items()},
        scope='Declared generated-GRI polynomial-law closed reactor only. Thermo fit validity, propagation, geometry and sustained-wave predictions remain unverified.',
        runtime_caveat='CPU executable is serial; shared allocation reserves an H100 even for CPU controls. These timings are not a CPU-only cost or 3D-engine throughput comparison.')
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['numerical_control_passed'] else 1)


if __name__=='__main__':main()
