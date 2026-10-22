"""Bounded native GRI reactor build with an explicit diagnostic EOS overlay."""
def build_methane():
    import hashlib
    import json
    import shutil
    import subprocess
    import time
    from pathlib import Path
    root=Path('/opt/PeleC'); evidence=Path('/opt/pelec-methane-build'); evidence.mkdir()
    started=time.monotonic()
    case=root/'Exec/RegTests/MethaneZeroD'
    shutil.copytree(root/'Exec/RegTests/zeroD',case)
    for name in ('prob.cpp','prob_parm.H'):
        shutil.copyfile(Path('/opt/methane-case')/name,case/name)
    cmake=case/'CMakeLists.txt'
    original=cmake.read_text()
    if original.count('LiDryer') != 1: raise RuntimeError('Unexpected zeroD CMake source')
    cmake.write_text(original.replace('LiDryer','grimech30'))
    register=root/'Exec/RegTests/CMakeLists.txt'
    register.write_text(register.read_text()+'\nadd_subdirectory(MethaneZeroD)\n')
    header=root/'Submodules/PelePhysics/Mechanisms/grimech30/mechanism.H'
    original=header.read_text()
    before='amrex::Real tmax = 3000.0; // min upper bound for thermo def'
    after='amrex::Real tmax = 5000.0; // explicit polynomial-consistency diagnostic; NOT extended data validity'
    if original.count(before) != 2: raise RuntimeError('Unexpected pinned GRI inverse source')
    original_hash=hashlib.sha256(header.read_bytes()).hexdigest()
    header.write_text(original.replace(before,after))
    patch=dict(before=before,after=after,replacements=2,original_header_sha256=original_hash,
               patched_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
               scope='Temperature inversion consistency only; fits/rates unchanged; outside-fit physical validity unresolved')
    (evidence/'patch.json').write_text(json.dumps(patch,indent=2)+'\n')
    commands=[];hashes={}
    for backend in ('cpu','gpu'):
        command=['cmake','--build',str(root/f'build-{backend}'),'--target','PeleC-MethaneZeroD','-j','12']
        commands.append(command)
        print('Building methane '+backend,flush=True)
        with (evidence/f'build-{backend}.log').open('w') as log:
            result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
        if result.returncode:
            print((evidence/f'build-{backend}.log').read_text()[-16000:],flush=True)
            raise RuntimeError(f'{backend} methane build failed')
        exe=root/f'build-{backend}/Exec/RegTests/MethaneZeroD/PeleC-MethaneZeroD'
        hashes[backend]=hashlib.sha256(exe.read_bytes()).hexdigest()
    (evidence/'manifest.json').write_text(json.dumps(dict(commands=commands,binary_sha256=hashes,
        overlay_sha256={name:hashlib.sha256((case/name).read_bytes()).hexdigest() for name in ('prob.cpp','prob_parm.H','prob.H','CMakeLists.txt')},
        wall_seconds=time.monotonic()-started,patch=patch,
        scope='Numerical methane reactor controls only; no engine/design validation'),indent=2)+'\n')
