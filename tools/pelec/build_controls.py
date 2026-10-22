"""Extend the pinned smoke image with upstream CPU and chemistry controls."""

def build_controls():
    import hashlib
    import json
    import subprocess
    import time
    from pathlib import Path
    root=Path('/opt/PeleC')
    evidence=Path('/opt/pelec-controls-build');evidence.mkdir()
    started=time.monotonic()
    commands=[('configure-cpu',['cmake','-S',str(root),'-B',str(root/'build-cpu'),'-G','Ninja',
                '-DCMAKE_BUILD_TYPE=Release','-DPELE_ENABLE_CUDA=OFF','-DPELE_DIM=3',
                '-DPELE_PRECISION=DOUBLE','-DPELE_ENABLE_MPI=OFF','-DPELE_ENABLE_OPENMP=OFF',
                '-DPELE_ENABLE_PARTICLES=OFF','-DPELE_ENABLE_TINY_PROFILE=ON']),
              ('build-cpu',['cmake','--build',str(root/'build-cpu'),'--target',
                            'PeleC-Sod','PeleC-zeroD','-j','12']),
              ('build-gpu-chemistry',['cmake','--build',str(root/'build-gpu'),'--target',
                                      'PeleC-zeroD','-j','12'])]
    for name,command in commands:
        print('Starting '+name,flush=True)
        with (evidence/(name+'.log')).open('w') as log:
            completed=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
        if completed.returncode:
            print((evidence/(name+'.log')).read_text()[-14000:],flush=True)
            raise RuntimeError(f'{name} failed: {completed.returncode}')
        print('Completed '+name,flush=True)
    hashes={}
    for backend in ('cpu','gpu'):
        for case in ('Sod','zeroD'):
            exe=root/f'build-{backend}/Exec/RegTests/{case}/PeleC-{case}'
            hashes[f'{backend}/{case}']=hashlib.sha256(exe.read_bytes()).hexdigest()
    (evidence/'manifest.json').write_text(json.dumps({'commands':commands,
        'binary_sha256':hashes,'build_wall_seconds':time.monotonic()-started},indent=2)+'\n')
