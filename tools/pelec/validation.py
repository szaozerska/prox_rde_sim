"""Fail-closed native log checks independent of process exit and final time."""

ERROR_MARKERS = (
    '[ERROR]', 'SUNDIALS_ERROR', 'mxstep steps taken before reaching tout',
    'amrex::Abort', 'SUBPROCESS TIMEOUT',
)


def native_log_errors(log):
    return [marker for marker in ERROR_MARKERS if marker in log]
