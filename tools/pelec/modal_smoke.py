"""Pinned native PeleC GPU build and bounded upstream installation smoke."""
import json
from pathlib import Path
import modal

SOURCE_LOCK = json.loads(Path(__file__).with_name('source_lock.json').read_text())


from build_native import build_solver


image = (modal.Image.from_registry(SOURCE_LOCK['cuda_image'], add_python='3.12')
         .apt_install('git', 'build-essential', 'cmake', 'ninja-build')
         .add_local_file(Path(__file__).with_name('build_native.py'),
                         '/root/build_native.py', copy=True)
         .run_function(build_solver, kwargs={'lock': SOURCE_LOCK}, cpu=16,
                       memory=65536, timeout=3600, include_source=False))
app = modal.App('prox-rde-3d-pelec-smoke', include_source=False)


@app.function(image=image, serialized=True, gpu='H100!', cpu=(4.0, 4.0),
              memory=(8192, 8192), timeout=600, startup_timeout=180,
              retries=0, max_containers=1)
def smoke():
    import base64
    import hashlib
    import io
    import json
    import math
    import subprocess
    import tarfile
    import time
    from datetime import datetime, timezone
    from pathlib import Path

    run = Path('/tmp/pelec-smoke')
    run.mkdir()
    exe = '/opt/PeleC/build-gpu/Exec/RegTests/Sod/PeleC-Sod'
    inputs = Path('/opt/PeleC/Exec/RegTests/Sod/sod-1.inp')
    text = '\n'.join(line for line in inputs.read_text().splitlines()
                     if not line.strip().startswith(('amr.regrid_int', 'amr.ref_ratio'))) + '\n'
    (run/'inputs.inp').write_text(text)
    command = [exe, 'inputs.inp', 'amr.max_level=0', 'max_step=10',
               'stop_time=0.002', 'pelec.fixed_dt=0.001',
               'amr.plot_int=1', 'amr.plot_vars=density Temp',
               'amr.derive_plot_vars=pressure x_velocity y_velocity z_velocity',
               'amrex.abort_on_unused_inputs=1']
    describe = subprocess.run([exe, '--describe'], capture_output=True, text=True,
                              check=False, timeout=30)
    (run/'describe.log').write_text(describe.stdout+describe.stderr)
    device = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
                             '--format=csv,noheader,nounits'], check=True,
                            capture_output=True, text=True, timeout=10).stdout
    started = time.monotonic()
    with (run/'solver.log').open('w') as log:
        try:
            result = subprocess.run(command, cwd=run, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=300)
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            returncode = 124
            log.write('\nSUBPROCESS TIMEOUT: incomplete run\n')
    elapsed = time.monotonic()-started
    plots = sorted(run.glob('plt[0-9]*'))
    final_time = None
    if plots:
        header = (plots[-1]/'Header').read_text().splitlines()
        nfields = int(header[1])
        final_time = float(header[3+nfields])
    passed = returncode == 0 and final_time is not None and math.isclose(
        final_time, 0.002, rel_tol=0.0, abs_tol=1e-14)
    record = {
        'status': 'installation_smoke_passed' if passed else 'installation_smoke_failed',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'command': command, 'returncode': returncode,
        'describe_returncode': describe.returncode,
        'describe_note': 'Observed --describe failure before AMReX initialization; use build manifest and plot job_info; no numerical source patch',
        'target_time': 0.002, 'final_time': final_time,
        'integration_wall_seconds': elapsed, 'device': device.strip(),
        'native_plot_count': len(plots),
        'scope': 'Upstream nonreacting Sod installation smoke only; field accuracy and methane/engine gates pending',
    }
    (run/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode='w:gz') as archive:
        archive.add(run, arcname='run')
        archive.add('/opt/pelec-evidence', arcname='build')
    raw = payload.getvalue()
    return json.dumps(dict(record, artifact_sha256=hashlib.sha256(raw).hexdigest(),
                           artifact_tar_gz_base64=base64.b64encode(raw).decode()))
