"""Build the pinned native solver with MPI/CUDA and a separate NETL startup case."""
def build_startup():
    import hashlib,json,shutil,subprocess,time
    from pathlib import Path
    root=Path('/opt/PeleC'); evidence=Path('/opt/startup-build');evidence.mkdir()
    start=time.monotonic()
    shutil.copytree('/opt/startup-case',root/'Exec/RegTests/RDEStartup')
    shutil.copytree('/opt/compact-mechanism',root/'Submodules/PelePhysics/Mechanisms/FFCMy12')
    case=root/'Exec/RegTests/RDEStartup'
    (case/'CMakeLists.txt').write_text((root/'Exec/RegTests/zeroD/CMakeLists.txt').read_text().replace('LiDryer','FFCMy12'))
    reg=root/'Exec/RegTests/CMakeLists.txt';reg.write_text(reg.read_text()+'\nadd_subdirectory(RDEStartup)\n')
    build=root/'build-mpi'
    commands=[['cmake','-S',str(root),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
        '-DPELE_ENABLE_CUDA=ON','-DCMAKE_CUDA_ARCHITECTURES=90','-DPELE_DIM=3','-DPELE_PRECISION=DOUBLE',
        '-DPELE_ENABLE_MPI=ON','-DPELE_ENABLE_OPENMP=OFF','-DPELE_ENABLE_PARTICLES=OFF','-DPELE_ENABLE_TINY_PROFILE=ON'],
        ['cmake','--build',str(build),'--target','PeleC-RDEStartup','-j','24']]
    for i,cmd in enumerate(commands):
        with (evidence/f'build-{i}.log').open('w') as log:
            r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=3300)
        if r.returncode:
            print((evidence/f'build-{i}.log').read_text()[-12000:],flush=True)
            raise RuntimeError('MPI startup build failed')
    exe=build/'Exec/RegTests/RDEStartup/PeleC-RDEStartup'
    (evidence/'manifest.json').write_text(json.dumps({'commands':commands,'wall_seconds':time.monotonic()-start,
        'binary_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
        'case_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in case.glob('prob*')},
        'mpi':True,'gpu_aware_mpi':False,'note':'Native equations; NETL initialization with documented geometry/transport limitations.'},indent=2))
