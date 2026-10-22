"""A/B diagnostic: upstream mechanism's supported tighter EOS inversion mode."""

def build_convergence():
    import hashlib
    import json
    import subprocess
    import time
    from pathlib import Path
    root=Path('/opt/PeleC');evidence=Path('/opt/pelec-controls-build')
    started=time.monotonic();commands=[];hashes={}
    for backend in ('cpu','gpu'):
        build=root/f'build-{backend}'
        configure=['cmake','-S',str(root),'-B',str(build),
                   '-DCMAKE_CXX_FLAGS=-DCONVERGENCE']
        if backend=='gpu':
            configure+=['-DCMAKE_CUDA_FLAGS=-DCONVERGENCE']
        for name,command in [('configure',configure),
                             ('build',['cmake','--build',str(build),'--target','PeleC-zeroD','-j','12'])]:
            commands.append(command)
            logpath=evidence/f'strict-eos-{backend}-{name}.log'
            print(f'Starting strict EOS {backend} {name}',flush=True)
            with logpath.open('w') as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
            if result.returncode:
                print(logpath.read_text()[-10000:],flush=True)
                raise RuntimeError(f'Strict EOS {backend} {name} failed')
        binary=build/'Exec/RegTests/zeroD/PeleC-zeroD'
        hashes[backend]=hashlib.sha256(binary.read_bytes()).hexdigest()
    (evidence/'strict-eos.json').write_text(json.dumps({
        'purpose':'A/B diagnostic of EOS inversion tolerance; original-rate chemistry and native numerical source unchanged',
        'macro':'CONVERGENCE','temperature_inversion_tolerance_K':1e-12,
        'commands':commands,'binary_sha256':hashes,
        'wall_seconds':time.monotonic()-started},indent=2)+'\n')
