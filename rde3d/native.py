"""Bounded native command execution and strict ASCII-field completion checks."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

CONTEXT = 'colima-rde3d'
IMAGE = 'prox-rde/detonationfoam:4bd2e86'


def read_field(path, cells):
    """Read only scalar/vector internal fields; reject binary/truncated data."""
    text = Path(path).read_text()
    if not re.search(r'\bformat\s+ascii\s*;', text):
        raise ValueError(f'{path}: only ASCII fields are supported')
    number = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'
    match = re.search(r'\binternalField\s+uniform\s+(\([^;]+\)|'+number+r')\s*;', text)
    if match:
        if re.sub(r'[\s()]', '', re.sub(number, '', match[1])):
            raise ValueError(f'{path}: malformed uniform field')
        values = tuple(float(n) for n in re.findall(number, match[1]))
        if len(values) not in (1, 3):
            raise ValueError('unsupported field arity')
        result = [values]*cells
    else:
        match = re.search(r'\binternalField\s+nonuniform\s+List<(scalar|vector)>\s+(\d+)\s*\((.*?)\)\s*;', text, re.S)
        if not match or int(match[2]) != cells:
            raise ValueError(f'{path}: missing/truncated internal field or cell-count mismatch')
        arity = 1 if match[1] == 'scalar' else 3
        values = re.findall(number, match[3])
        # Reject NaN/Inf or other garbage rather than silently extracting remaining numbers.
        remainder = re.sub(number, '', match[3])
        if re.sub(r'[\s()]', '', remainder) or len(values) != arity*cells:
            raise ValueError(f'{path}: malformed or nonfinite field')
        result = [tuple(float(v) for v in values[i:i+arity]) for i in range(0, len(values), arity)]
    if not all(math.isfinite(v) for row in result for v in row):
        raise ValueError(f'{path}: nonfinite field')
    return result


def inspect_completion(case, end_time, cells, required=('p', 'T', 'U')):
    """A successful process alone is not a completed or valid simulation."""
    case = Path(case)
    times = []
    for p in case.iterdir():
        if p.is_dir():
            try:
                value = float(p.name)
                if math.isfinite(value):
                    times.append((value, p))
            except ValueError:
                pass
    if not times or not math.isclose(max(times)[0], end_time, rel_tol=1e-10, abs_tol=1e-15):
        raise ValueError('required final time was not written (early exit, overshoot or missing output)')
    final_time, final = max(times)
    fields = {name: read_field(final/name, cells) for name in required}
    for name in ('p', 'T', 'rho'):
        if name in fields and min(row[0] for row in fields[name]) <= 0:
            raise ValueError(f'nonpositive {name}')
    return final_time, fields


def run_command(case, command, *, timeout=120, image=IMAGE):
    """Run one isolated native command, retaining log/status even on failure.

    Timeouts kill the container as well as the Docker client. Input hashes include
    native dictionaries, mesh and initial state. Only this case is mounted.
    """
    case = Path(case).resolve()
    if not case.is_dir() or not command:
        raise ValueError('existing case and nonempty command required')
    label = command[0]
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', label):
        raise ValueError('command must be an executable name, not shell text')
    log = case/f'log.{label}'
    status = case/f'status.{label}.json'
    if log.exists() or status.exists():
        raise FileExistsError(f'{label} already has evidence in this case')
    image_id = subprocess.check_output(['docker', '--context', CONTEXT, 'image', 'inspect',
                                        image, '--format', '{{.Id}}'], text=True).strip()
    hashes = {str(p.relative_to(case)): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ('0', 'constant', 'system') for p in sorted((case/folder).rglob('*')) if p.is_file()}
    name = 'rde3d-'+uuid.uuid4().hex[:12]
    argv = ['docker', '--context', CONTEXT, 'run', '--rm', '--name', name, '--network', 'none',
            '--cpus', '2', '--memory', '3g', '--pids-limit', '256', '--user', f'{os.getuid()}:{os.getgid()}',
            '--volume', f'{case}:/case', '--workdir', '/case', image_id,
            'timeout', str(timeout), *command]
    record = dict(command=command, image_id=image_id, input_sha256=hashes,
                  wall_timeout_s=timeout, status='running')
    started = time.monotonic()
    status.write_text(json.dumps(record, indent=2)+'\n')
    try:
        with log.open('x') as stream:
            result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout+30)
        record['returncode'] = result.returncode
        record['status'] = 'process_completed' if result.returncode == 0 else 'failed'
        if result.returncode:
            raise RuntimeError(f'{label} failed with {result.returncode}; see {log}')
    except BaseException:
        record['status'] = 'failed'
        subprocess.run(['docker', '--context', CONTEXT, 'rm', '-f', name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        raise
    finally:
        record['wall_time_s'] = time.monotonic()-started
        status.write_text(json.dumps(record, indent=2)+'\n')
    return record
