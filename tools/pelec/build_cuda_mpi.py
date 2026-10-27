"""Build ABI-compatible Open MPI 4.1 with CUDA-aware communication."""
def build_cuda_mpi():
    import hashlib,json,subprocess,tarfile,time,urllib.request
    from pathlib import Path
    url='https://download.open-mpi.org/release/open-mpi/v4.1/openmpi-4.1.8.tar.bz2'
    expected='466f68e3132a1dc02710cc2011fafced8336d98359fa2dae4dddcfd5719f12a9'
    root=Path('/opt/cuda-mpi-build');root.mkdir();start=time.monotonic()
    raw=urllib.request.urlopen(url,timeout=120).read()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Open MPI release checksum mismatch')
    archive=root/'source.tar.bz2';archive.write_bytes(raw)
    with tarfile.open(archive) as t:t.extractall(root,filter='data')
    src=root/'openmpi-4.1.8'
    commands=[['./configure','--prefix=/opt/cuda-mpi','--with-cuda=/usr/local/cuda',
        '--disable-mpi-fortran','--disable-oshmem','--without-ucx','--without-verbs'],
        ['make','-j','24'],['make','install']]
    for i,command in enumerate(commands):
        with (root/f'build-{i}.log').open('w') as log:
            r=subprocess.run(command,cwd=src,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        if r.returncode:
            print((root/f'build-{i}.log').read_text()[-10000:]);raise RuntimeError('CUDA-aware MPI build failed')
    info=subprocess.run(['/opt/cuda-mpi/bin/ompi_info','--parsable','--all'],capture_output=True,text=True,check=True).stdout
    cuda=[line for line in info.splitlines() if 'mpi_built_with_cuda_support:value' in line]
    if not cuda or not any('true' in line for line in cuda):raise RuntimeError('MPI did not enable CUDA support')
    (root/'manifest.json').write_text(json.dumps({'url':url,'sha256':expected,'commands':commands,
        'cuda_support':cuda,'wall_seconds':time.monotonic()-start},indent=2))
