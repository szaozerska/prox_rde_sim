"""Explicitly uploaded, public-source-only native build function."""
def build_solver(lock):
    import hashlib
    import json
    import subprocess
    import time
    from pathlib import Path

    started = time.monotonic()
    root = Path('/opt/PeleC')
    root.mkdir()
    def run(args, cwd=root, timeout=600):
        return subprocess.run(args, cwd=cwd, check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout).stdout
    run(['git', 'init'])
    run(['git', 'remote', 'add', 'origin', lock['pelec_repository']])
    run(['git', 'fetch', '--depth', '1', 'origin', lock['pelec_commit']])
    run(['git', 'checkout', '--detach', 'FETCH_HEAD'])
    run(['git', 'submodule', 'update', '--init', '--recursive', '--depth', '1'], timeout=900)
    actual = {line.split()[1]: line.split()[0] for line in
              run(['git', 'submodule', 'status', '--recursive']).splitlines()}
    assert actual == lock['submodules'], (actual, lock['submodules'])
    build = root / 'build-gpu'
    options = ['cmake', '-S', str(root), '-B', str(build), '-G', 'Ninja',
               '-DCMAKE_BUILD_TYPE=Release', '-DPELE_ENABLE_CUDA=ON',
               '-DCMAKE_CUDA_ARCHITECTURES=' + lock['cuda_architectures'],
               '-DPELE_DIM=3', '-DPELE_PRECISION=DOUBLE', '-DPELE_ENABLE_MPI=OFF',
               '-DPELE_ENABLE_OPENMP=OFF', '-DPELE_ENABLE_PARTICLES=OFF',
               '-DPELE_ENABLE_TINY_PROFILE=ON', '-DPELE_ENABLE_FPE_TRAP_FOR_TESTS=ON']
    evidence = Path('/opt/pelec-evidence')
    evidence.mkdir()
    for name, cmd, limit in [('configure.log', options, 300),
                             ('build.log', ['cmake', '--build', str(build), '--target',
                                            'PeleC-Sod', '-j', '12'], 2700)]:
        with (evidence/name).open('w') as log:
            result = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=limit)
        if result.returncode:
            print((evidence/name).read_text()[-16000:], flush=True)
            raise RuntimeError(f'{name} failed: {result.returncode}')
    exe = build/'Exec/RegTests/Sod/PeleC-Sod'
    assert exe.is_file()
    record = dict(lock, build_options=options, build_wall_seconds=time.monotonic()-started,
                  executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                  compiler=run(['g++','--version']), cuda_compiler=run(['nvcc','--version']),
                  cmake=run(['cmake','--version']), packages=run(['dpkg-query','-W']))
    (evidence/'build_manifest.json').write_text(json.dumps(record, indent=2)+'\n')
    print('Pinned PeleC-Sod CUDA build complete', flush=True)

