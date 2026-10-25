"""Pinned upstream build; only a problem initializer is added. No solver patches."""
def build(lock):
    import hashlib
    import json
    import shutil
    import subprocess
    import time
    from pathlib import Path
    root = Path('/opt/PeleC')
    evidence = Path('/opt/pelec-2d-build')
    root.mkdir(); evidence.mkdir()
    start = time.monotonic()
    def run(args, timeout=600):
        return subprocess.run(args, cwd=root, check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout).stdout
    run(['git', 'init'])
    run(['git', 'remote', 'add', 'origin', lock['pelec_repository']])
    run(['git', 'fetch', '--depth', '1', 'origin', lock['pelec_commit']])
    run(['git', 'checkout', '--detach', 'FETCH_HEAD'])
    run(['git', 'submodule', 'update', '--init', '--recursive', '--depth', '1'], 900)
    actual = {line.split()[1]: line.split()[0] for line in
              run(['git', 'submodule', 'status', '--recursive']).splitlines()}
    if actual != lock['submodules']:
        raise RuntimeError('Submodule pin mismatch')
    mech = root/'Submodules/PelePhysics/Mechanisms/grimech30'
    for name, expected in lock['mechanism_sha256'].items():
        if hashlib.sha256((mech/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Mechanism hash mismatch: '+name)
    shutil.copytree('/opt/adapter/native', root/'Exec/RegTests/Methane2D')
    register = root/'Exec/RegTests/CMakeLists.txt'
    register.write_text(register.read_text()+'\nadd_subdirectory(Methane2D)\n')
    options = ['cmake', '-S', str(root), '-B', str(root/'build-2d'), '-G', 'Ninja',
               '-DCMAKE_BUILD_TYPE=Release', '-DPELE_DIM=2', '-DPELE_PRECISION=DOUBLE',
               '-DPELE_ENABLE_MPI=OFF', '-DPELE_ENABLE_OPENMP=OFF',
               '-DPELE_ENABLE_CUDA=OFF', '-DPELE_ENABLE_PARTICLES=OFF']
    for name, cmd in [('configure', options), ('build', ['cmake', '--build',
                     str(root/'build-2d'), '--target', 'PeleC-Methane2D', '-j', '8'])]:
        with (evidence/(name+'.log')).open('w') as log:
            result = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=2400)
        if result.returncode:
            print((evidence/(name+'.log')).read_text()[-12000:], flush=True)
            raise RuntimeError(name+' failed')
    exe = root/'build-2d/Exec/RegTests/Methane2D/PeleC-Methane2D'
    manifest = dict(lock, build_options=options,
                    executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                    adapter_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in Path('/opt/adapter/native').iterdir() if p.is_file()},
                    compiler=run(['c++','--version']), packages=run(['dpkg-query','-W']),
                    seconds=time.monotonic()-start, numerical_source_patches=[])
    (evidence/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Pinned native PeleC 2D methane build complete', flush=True)
