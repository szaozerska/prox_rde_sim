"""Optional native CVODE/cuSparse backend; equations and kinetic mechanism are unchanged."""
def build_cvode_direct():
    import subprocess,json,hashlib,time
    from pathlib import Path
    root=Path('/opt/PeleC');out=Path('/opt/cvode-direct-build');out.mkdir();start=time.monotonic()
    build=root/'build-mpi-direct'
    commands=[['cmake','-S',str(root),'-B',str(build),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
        '-DPELE_ENABLE_CUDA=ON','-DCMAKE_CUDA_ARCHITECTURES=90','-DPELE_DIM=3','-DPELE_PRECISION=DOUBLE',
        '-DPELE_ENABLE_MPI=ON','-DPELE_ENABLE_OPENMP=OFF','-DPELE_ENABLE_PARTICLES=OFF','-DPELE_ENABLE_TINY_PROFILE=ON',
        '-DCMAKE_CXX_FLAGS=-DPELE_CVODE_FORCE_YCORDER','-DCMAKE_CUDA_FLAGS=-DPELE_CVODE_FORCE_YCORDER'],
        ['cmake','--build',str(build),'--target','PeleC-RDEStartup','-j','24']]
    for i,cmd in enumerate(commands):
        with (out/f'build-{i}.log').open('w') as log:
            r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=3300)
        if r.returncode:
            print((out/f'build-{i}.log').read_text()[-12000:],flush=True);raise RuntimeError('Direct CVODE backend build failed')
    record=json.loads(Path('/opt/startup-build/manifest.json').read_text())
    exe=build/'Exec/RegTests/RDEStartup/PeleC-RDEStartup'
    record.update(commands=commands,wall_seconds=time.monotonic()-start,
        binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
        linear_solver='Native CVODE cuSparse batched QR with analytic mechanism Jacobian; YC ordering',
        validation_status='Build only; do not adopt without matched native-field comparison')
    (out/'manifest.json').write_text(json.dumps(record,indent=2)+'\n')
