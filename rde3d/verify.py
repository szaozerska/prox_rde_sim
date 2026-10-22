"""Explicit bounded native installation/mesh checks, separate from unit tests."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil

from .native import inspect_completion, read_field, run_command


def replace_entry(path, key, value):
    path = Path(path)
    text, count = re.subn(r'(?m)^\s*'+re.escape(key)+r'\s+[^;]+;', f'{key} {value};', path.read_text())
    if count != 1:
        raise ValueError(f'expected exactly one {key} in {path}, got {count}')
    path.write_text(text)


def tutorial(source, out):
    """Coarse 2 ns NH3 tutorial smoke, not a detonation validation run."""
    source, out = Path(source), Path(out)
    shutil.copytree(source, out)  # refuses existing destinations
    block = out/'system/blockMeshDict'
    text = block.read_text()
    if text.count('(20000 1 1)') != 1:
        raise ValueError('pinned tutorial grid changed')
    text = text.replace('(20000 1 1)', '(400 1 1)')
    # The supplied single-row mesh leaves y active. Declare both transverse
    # directions empty for this one-dimensional installation control.
    for patch in ('bottom', 'top'):
        text, count = re.subn(r'(' + patch + r'\s*\{\s*type\s+)wall;', r'\1empty;', text)
        if count != 1:
            raise ValueError('pinned tutorial boundary changed')
    block.write_text(text)
    # Upstream 0/ contains a previously advanced 20,000-cell profile. Rebuild a
    # fresh uniform mixture from its far-upstream state, then apply setFields.
    # This is an installation smoke, not a conservative profile/refinement study.
    for field in (out/'0').iterdir():
        values = read_field(field, 20000)[-1]
        if field.name == 'U':
            values = (0., 0., 0.)
        value = ' '.join(format(v, '.15g') for v in values)
        if len(values) == 3:
            value = '('+value+')'
        text, count = re.subn(r'\binternalField\s+.*?;', 'internalField uniform '+value+';',
                              field.read_text(), flags=re.S)
        if count != 1:
            raise ValueError('pinned initial-field format changed')
        for patch in ('bottom', 'top'):
            text, count = re.subn(r'(' + patch + r'\s*\{\s*type\s+)\w+;', r'\1empty;', text)
            if count != 1:
                raise ValueError('pinned initial boundary changed')
        field.write_text(text)
    control = out/'system/controlDict'
    for key, value in [('endTime', '2e-9'), ('deltaT', '1e-10'), ('writeInterval', '2e-9'),
                       ('adjustTimeStep', 'no'), ('maxDeltaT', '1e-10')]:
        replace_entry(control, key, value)
    # This optional library is requested upstream but absent from its build tree.
    text = control.read_text()
    if text.count('"libODE_DLB.so"') != 1:
        raise ValueError('pinned optional-library declaration changed')
    control.write_text(text.replace('"libODE_DLB.so"', '// libODE_DLB.so absent upstream; using linked OpenFOAM ODE library'))
    replace_entry(out/'constant/solverTypeProperties', 'SW_position_limit', '1.0')
    metadata = dict(purpose='installation_only', source=str(source), cells=400,
                    end_time_s=2e-9, fixed_dt_s=1e-10,
                    modifications=['400 axial cells instead of 20000', '2 ns end time',
                                   'fixed dt and final-only output', 'shock cutoff beyond domain',
                                   'omit nonexistent optional libODE_DLB.so',
                                   'both transverse directions empty',
                                   'fresh uniform mixture from upstream end state; zero velocity; setFields hot patch'])
    (out/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    result = {'status': 'failed', 'claim': 'installation_only'}
    try:
        for command in [['blockMesh'], ['checkMesh', '-allTopology', '-allGeometry'], ['setFields'], ['detonationFoam_V2.0']]:
            run_command(out, command)
            if command[0] == 'checkMesh' and 'Mesh OK.' not in (out/'log.checkMesh').read_text():
                raise ValueError('native tutorial mesh quality failed')
        result = inspect_tutorial(out)
    finally:
        (out/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def inspect_tutorial(out):
    """Check saved smoke output without advancing the solver again."""
    out = Path(out)
    text = (out/'constant/foam/species.foam').read_text()
    match = re.search(r'species\s+(\d+)\s*\((.*?)\)', text, re.S)
    if not match or len(match[2].split()) != int(match[1]):
        raise ValueError('malformed species list')
    species = match[2].split()
    _, fields = inspect_completion(out, 2e-9, 400, ('p', 'T', 'U', 'rho', *species))
    if 'End' not in (out/'log.detonationFoam_V2.0').read_text():
        raise ValueError('normal solver end marker missing')
    minimum = min(v[0] for name in species for v in fields[name])
    sum_error = max(abs(sum(fields[name][i][0] for name in species)-1) for i in range(400))
    if minimum < -1e-12 or sum_error > 1e-9:
        raise ValueError('invalid final species fractions')
    tmax = max(2000., max(v[0] for v in fields['T']))
    umax = max(math.sqrt(sum(v*v for v in row)) for row in fields['U'])
    # Conservative ideal-gas bound: gamma<=5/3 and molecular weight>=1 kg/kmol.
    # Include even the empty transverse faces in the Cartesian acoustic estimate.
    acoustic_bound = (umax + math.sqrt((5/3)*8314.462618*tmax))*1e-10*(400/.1+1/.01+1/.02)
    if acoustic_bound >= .01:
        raise ValueError('smoke acoustic step bound exceeded')
    result = dict(status='passed', claim='installation_only', final_time_s=2e-9,
                  species_min=minimum, species_sum_max_error=sum_error,
                  acoustic_step_bound=acoustic_bound,
                  p_min_Pa=min(v[0] for v in fields['p']), p_max_Pa=max(v[0] for v in fields['p']),
                  T_min_K=min(v[0] for v in fields['T']), T_max_K=max(v[0] for v in fields['T']))
    (out/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='kind', required=True)
    t = sub.add_parser('tutorial')
    t.add_argument('--source', type=Path, required=True)
    t.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = tutorial(args.source, args.out)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
