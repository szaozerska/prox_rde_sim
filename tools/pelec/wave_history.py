"""Fail-closed every-step state extrema for the fixed-step native wave control."""
import math
import re
FIELDS=('density','Temp','pressure','massfrac','sumYminus1')
PATTERN=re.compile(r'TIME = (\S+)\s+(density|Temp|pressure|massfrac|sumYminus1)\s+MIN = (\S+)\s+MAX = (\S+)')

def audit_history(log,target_time,dt,temperature_bounds=(299.,5000.)):
    rows={name:[] for name in FIELDS}
    for match in PATTERN.finditer(log):
        time,name,low,high=match.groups();rows[name].append((float(time),float(low),float(high)))
    expected=round(target_time/dt)+1
    complete=all(len(values)==expected for values in rows.values())
    finite=all(math.isfinite(v) for values in rows.values() for row in values for v in row)
    increasing=all(all(b[0]>a[0] for a,b in zip(values,values[1:])) for values in rows.values())
    times=complete and all(all(math.isclose(row[0],i*dt,rel_tol=1e-7,abs_tol=1e-18) for i,row in enumerate(values)) for values in rows.values())
    if not (complete and finite and increasing and times):
        return dict(passed=False,complete=complete,finite=finite,increasing=increasing,times=times,
            counts={k:len(v) for k,v in rows.items()},expected_count=expected)
    extrema={name:[min(v[1] for v in values),max(v[2] for v in values)] for name,values in rows.items()}
    checks=dict(positive_density_pressure=min(extrema[k][0] for k in ('density','pressure'))>0,
        temperature_interval=temperature_bounds[0]<=extrema['Temp'][0] and extrema['Temp'][1]<=temperature_bounds[1],
        species_nonnegative=extrema['massfrac'][0]>=-1e-12,
        species_sum=max(map(abs,extrema['sumYminus1']))<=1e-10)
    return dict(passed=all(checks.values()),checks=checks,extrema=extrema,expected_count=expected,
        scope='Every native logged step, including initial state; native text precision retained. Complements full-precision saved field checks.')
