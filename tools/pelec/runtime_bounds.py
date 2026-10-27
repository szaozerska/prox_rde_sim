"""Bound a segment by both requested wall time and the campaign's absolute cutoff."""
from datetime import datetime, timezone


def bounded_runtime_seconds(requested, cutoff=None, now=None):
    if not 10 <= requested <= 14400:
        raise ValueError('Invalid bounded allocation')
    if cutoff is None:
        return requested
    deadline = datetime.fromisoformat(cutoff)
    if deadline.tzinfo is None:
        raise ValueError('Campaign cutoff must include a timezone')
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None:
        raise ValueError('Current time must include a timezone')
    remaining = (deadline - now).total_seconds()
    # Allow a checkpoint request before the hard limit, including queue delay.
    if remaining <= 180:
        raise ValueError('Too close to campaign cutoff to start another segment')
    return min(requested, remaining)
