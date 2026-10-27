"""Audit complete native extrema lines, including failures between plotfiles."""
import math
import re

EXTREMA = re.compile(r'^TIME = (\S+)\s+(\S+)\s+MIN = (\S+)\s+MAX = (\S+)\s*$', re.MULTILINE)


def audit_native_log(text):
    # A file may be read during a write. Never interpret a truncated exponent.
    complete = text if text.endswith('\n') else text.rsplit('\n', 1)[0] if '\n' in text else ''
    fields, violations, closure = {}, [], []
    latest = None
    for t, name, low, high in EXTREMA.findall(complete):
        t, low, high = float(t), float(low), float(high)
        if math.isfinite(t):latest = t if latest is None else max(latest, t)
        entry = fields.setdefault(name, {'samples': 0, 'minimum': None, 'maximum': None, 'nonfinite_samples': 0})
        entry['samples'] += 1
        if not all(math.isfinite(x) for x in (t, low, high)):
            entry['nonfinite_samples'] += 1
            violations.append({'field': name, 'time_s': t if math.isfinite(t) else str(t), 'reason': 'nonfinite extrema', 'min': str(low), 'max': str(high)})
            continue
        entry['minimum'] = low if entry['minimum'] is None else min(entry['minimum'], low)
        entry['maximum'] = high if entry['maximum'] is None else max(entry['maximum'], high)
        if name == 'sumYminus1':
            error = max(abs(low), abs(high)); closure.append((t, error, low, high))
            if error > 1e-6:
                violations.append({'field': name, 'time_s': t, 'reason': 'species closure exceeds emergency bound 1e-6', 'min': low, 'max': high})
        if name == 'massfrac' and low < -.01:
            violations.append({'field': name, 'time_s': t, 'reason': 'negative species exceeds emergency bound -0.01', 'min': low})
    worst = max(closure, key=lambda x: x[1]) if closure else None
    return {'latest_time_s': latest, 'fields': fields, 'emergency_stop_required': bool(violations),
        'violation_count': len(violations), 'first_violations': violations[:20],
        'every_step_species_sum': {'samples': len(closure), 'worst_time_s': worst[0] if worst else None,
            'maximum_absolute_error': worst[1] if worst else None,
            'worst_minimum_sum_minus_one': worst[2] if worst else None,
            'worst_maximum_sum_minus_one': worst[3] if worst else None,
            'note': 'Native log includes all AMR levels; localize discrepancies before classifying active-fluid error.'}}
