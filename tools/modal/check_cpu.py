"""Explicit, short CPU-only access check; importing this file launches no job."""
import modal

app = modal.App('prox-rde-3d-cpu-check', include_source=False)


@app.function(
    image=modal.Image.debian_slim(python_version='3.12'),
    serialized=True,
    cpu=(8.0, 8.0),
    memory=(1024, 1024),
    gpu=None,
    timeout=30,
    startup_timeout=120,
    retries=0,
    max_containers=1,
)
def check_cpu():
    import glob
    import json
    import os
    import platform
    from datetime import datetime, timezone
    from pathlib import Path

    model = next((line.split(':', 1)[1].strip()
                  for line in Path('/proc/cpuinfo').read_text().splitlines()
                  if line.startswith('model name')), 'unknown')
    limits = {}
    for name in ('cpu.max', 'memory.max'):
        path = Path('/sys/fs/cgroup') / name
        limits[name] = path.read_text().strip() if path.exists() else 'unavailable'
    checksum = sum(i * i for i in range(1000))
    assert checksum == 332833500
    return json.dumps({
        'status': 'cpu_execution_passed',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'requested_physical_cpu_cores': 8,
        'requested_memory_mib': 1024,
        'gpu_requested': False,
        'cpu_model': model,
        'architecture': platform.machine(),
        'visible_logical_cpus': os.cpu_count(),
        'cgroup_limits': limits,
        'visible_nvidia_device_nodes': glob.glob('/dev/nvidia[0-9]*'),
        'checksum': checksum,
        'scope': 'CPU allocation and execution only; not a CFD/MPI benchmark or quota maximum',
    }, indent=2)
