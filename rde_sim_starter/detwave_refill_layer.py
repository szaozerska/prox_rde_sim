"""Final bounded control: can the unchanged surrogate traverse a fresh 1 mm layer?"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
from analyze import conservation_budget
from controlled import formed_layer, formed_profile, row_front_metrics
from physics import reaction_rate
from run import _fingerprint, _write_json, _write_npz
from solver import Solver, max_speed

directory = Path(sys.argv[1])
directory.mkdir(parents=True, exist_ok=False)
manifest = json.loads(Path('runs/detwave_25fi5_compact_hllc/inputs.json').read_text())
c = manifest['calibration']
profile = formed_profile(c)
base, x, z, init = formed_layer(c, profile, .001, dx=.000125,
    length=.1125, shock=.04, buffer=.0325, align_interface=True)
s = Solver(base.nx, base.ny, base.dx, base.dy, tuple(manifest['resolved']['gas']),
           base.bc, source_cfl=.2, flux='hllc')
s.U[:] = base.U
del base
initial = s.conserved_totals()
scale = np.maximum(abs(initial), np.array([1.,4000.,4000.,1e7,1.])*.1125*.0335)
_write_json(directory/'inputs.json', dict(calibration=c, initialization=init,
    end_us=10., flux=s.flux, source_cfl=s.source_cfl, fingerprint=_fingerprint(),
    driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    bounds_mps=[4000.,3000.], policy='No injection, no periodic return, no stronger ignition. '
    'Fully fresh 1mm layer under 1500K products. Same mesh and chemistry as compact engine. '
    'Remote boundaries excluded by measured characteristic bounds; diagnostic, not engine validation.'))
history=[]; observed=np.zeros(2); started=time.monotonic();status='running';error=None
deadline=datetime(2026,10,22,22,0,tzinfo=timezone.utc)

def save():
    w=s.prim().copy()
    rows=[row_front_metrics(w[:,:,j],x,c,.0075) for j in [0,3,7]]
    fronts=[r['front_m'] for r in rows if r['front_m'] is not None]
    budget=conservation_budget(s.conserved_totals(),initial,s.cumulative_boundary,s.cumulative_source,1.,1.)
    h=dict(time_us=s.t*1e6,rows=rows,
        budget_scaled_residual=float(np.max(abs(budget['residual'])/scale)),
        top_margin_m=s.ny*s.dy-.001-3000*s.t,
        left_margin_m=min(fronts)-.0075-4000*s.t if fronts else None,
        right_margin_m=.1125-max(fronts)-4000*s.t if fronts else None)
    history.append(h)
    _write_json(directory/'progress.json',dict(status=status,error=error,time_us=s.t*1e6,
        steps=s.steps,wall_seconds=time.monotonic()-started,invalid_states=s.invalid_state_count,
        observed_speeds_mps=observed.tolist(),history=history))
    _write_npz(directory/'checkpoint.npz',U=s.U,t=s.t,steps=s.steps,
               boundary=s.cumulative_boundary,source=s.cumulative_source)
    if round(s.t*1e6) in [0,5,10] or status!='running':
        rate=reaction_rate(w[4],w[3]/(c['R']*w[0]),c['R'],c['k'],c['Ea'])
        _write_npz(directory/f'field_{s.t*1e6:06.2f}us.npz',primitive=w,rate=rate,x=x,z=z,t=s.t)
    print(f'{status}: {s.t*1e6:.3f} us, {s.steps} steps, {time.monotonic()-started:.1f}s',flush=True)
    return h

try:
    save()
    for tick in range(1,11):
        target=tick*1e-6
        while s.t<target-1e-16:
            if datetime.now(timezone.utc)>=deadline:
                raise TimeoutError('22:00 UTC investigation deadline')
            s.step(dt_max=target-s.t)
            observed=np.maximum(observed,max_speed(s.W,s.g))
            s.prim(); observed=np.maximum(observed,max_speed(s.W,s.g))
            if np.any(observed>np.array([4000.,3000.])):
                raise RuntimeError('predeclared characteristic bound exceeded')
        h=save()
        if any(h[k] is None or h[k]<=0 for k in ['top_margin_m','left_margin_m','right_margin_m']):
            raise RuntimeError('remote boundary may affect measurement region')
    status='completed'
except BaseException as exc:
    status='stopped';error=repr(exc)
finally:
    save()
