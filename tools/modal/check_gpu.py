"""Bounded single-GPU access probe; no solver/throughput claim or import-time job."""
import modal

app = modal.App('prox-rde-3d-gpu-check', include_source=False)


@app.function(
    image=modal.Image.debian_slim(python_version='3.12'),
    serialized=True,
    cpu=(2.0, 2.0), memory=(2048, 2048), gpu='H100!',
    timeout=30, startup_timeout=120, retries=0, max_containers=1,
)
def check_gpu():
    import ctypes
    import json
    import subprocess
    from datetime import datetime, timezone

    driver = ctypes.CDLL('libcuda.so.1')
    assert driver.cuInit(0) == 0
    count = ctypes.c_int()
    assert driver.cuDeviceGetCount(ctypes.byref(count)) == 0
    assert count.value == 1, f'Expected one CUDA device, got {count.value}'
    major, minor = ctypes.c_int(), ctypes.c_int()
    assert driver.cuDeviceComputeCapability(ctypes.byref(major), ctypes.byref(minor), 0) == 0
    assert (major.value, minor.value) == (9, 0)
    info = subprocess.run([
        'nvidia-smi', '--query-gpu=name,memory.total,driver_version,compute_cap',
        '--format=csv,noheader,nounits',
    ], check=True, capture_output=True, text=True, timeout=10)
    return json.dumps({
        'status': 'gpu_allocation_and_driver_passed',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'requested_gpu': 'H100!', 'requested_gpu_count': 1,
        'requested_physical_cpu_cores': 2, 'requested_memory_mib': 2048,
        'cuda_device_count': count.value,
        'compute_capability': [major.value, minor.value],
        'nvidia_smi_columns': ['name', 'memory_total_mib', 'driver_version', 'compute_capability'],
        'nvidia_smi': info.stdout.strip(),
        'scope': 'Allocation and CUDA driver only; no CFD/kernel throughput or multi-GPU quota verified',
    }, indent=2)
