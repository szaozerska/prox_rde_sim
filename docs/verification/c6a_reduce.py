"""Read-only C6a checkpoint/history audit; no solver import or flow advancement."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np


def reduce(directory):
    directory=Path(directory)
    inputs=json.loads((directory/'inputs.json').read_text())
    summary=json.loads((directory/'summary.json').read_text())
    history=[json.loads(line) for line in (directory/'history.jsonl').read_text().splitlines()]
    r=inputs['resolved'];c=inputs['calibration']
    with np.load(directory/'checkpoint.npz',allow_pickle=False) as saved:
        U=saved['U'];initial=saved['initial_totals']*r['gap']
        boundary=saved['cumulative_boundary']*r['gap'];source=saved['cumulative_source']*r['gap']
        metadata=json.loads(str(saved['state_json']))
    inventory=U.sum(axis=(1,2))*r['dx']*r['dy']*r['gap']
    storage=inventory-initial
    residual=storage-(boundary[0]-boundary[1]+boundary[2]-boundary[3]+source)
    rho=U[0];xi=U[4]/rho
    pressure=(c['gamma']-1)*(U[3]-.5*(U[1]**2+U[2]**2)/rho-c['q']*(rho-U[4]))
    history_inventory=np.array([row['inventory'] for row in history])
    scale=np.maximum(np.maximum(abs(initial),np.max(abs(history_inventory-initial),axis=0)),1e-30)
    error=float(np.max(abs(residual)/scale))
    history_error=float(np.max(abs(np.array([row['residual'] for row in history]))/scale))
    times=np.array([row['t'] for row in history])
    assert np.isfinite(U).all() and np.isfinite(pressure).all()
    assert rho.min()>0 and pressure.min()>0 and xi.min()>=-1e-12 and xi.max()<=1+1e-12
    assert error<1e-10 and history_error<1e-10
    np.testing.assert_array_equal(source[:4],0.)
    assert source[4]>0
    np.testing.assert_allclose(inventory,summary['budgets']['inventory'],rtol=1e-13,atol=1e-12)
    np.testing.assert_allclose(initial,r['formed_initialization']['expected_totals'],rtol=1e-11,atol=1e-12)
    assert [h['step'] for h in history]==list(range(summary['steps']+1)) and np.all(np.diff(times)>0)
    assert summary['t']==metadata['t']==history[-1]['t']==r['benchmark_end_s']
    assert summary['status']=='completed_limit' and summary['invalid_state_count']==0
    assert summary['run_mode']=='development_benchmark'
    wall=summary['wall_seconds_this_invocation'];cells=r['nx']*r['ny']
    return dict(inputs=inputs,summary=summary,independent_checkpoint_budget_scaled_error=error,
        max_native_history_budget_scaled_error=history_error,history_count=len(history),
        grid_cells=cells,final_pressure_range_Pa=[float(pressure.min()),float(pressure.max())],
        final_progress_range=[float(xi.min()),float(xi.max())],
        native_output_bytes=sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()),
        seconds_per_accepted_step=wall/summary['steps'],cell_steps_per_second=cells*summary['steps']/wall,
        three_interval_linear_cost_hours=wall/summary['t']*3/r['f_ref']/3600,
        interpretation='2 us functional validity/cost check; extrapolated cost is not a promise; no sustained-wave inference',
        sha256={name:hashlib.sha256((directory/name).read_bytes()).hexdigest()
                for name in ('inputs.json','summary.json','checkpoint.npz','history.jsonl')})


if __name__=='__main__':
    report=reduce(sys.argv[1])
    with Path(sys.argv[2]).open('x') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('inputs','summary','sha256')},indent=2))
