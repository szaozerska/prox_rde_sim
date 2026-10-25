"""Compile native upstream equations with the attributed compact mechanism."""
def build_prototype():
    import shutil,subprocess,json,time,hashlib
    from pathlib import Path
    root=Path('/opt/PeleC');start=time.monotonic();ev=Path('/opt/prototype-build');ev.mkdir()
    mech=root/'Submodules/PelePhysics/Mechanisms/FFCMy12';shutil.copytree('/opt/compact-mechanism',mech)
    case=root/'Exec/RegTests/RDEPrototype';shutil.copytree('/opt/prototype-case',case)
    (case/'CMakeLists.txt').write_text((root/'Exec/RegTests/zeroD/CMakeLists.txt').read_text().replace('LiDryer','FFCMy12'))
    register=root/'Exec/RegTests/CMakeLists.txt';register.write_text(register.read_text()+'\nadd_subdirectory(RDEPrototype)\n')
    command=['cmake','--build',str(root/'build-gpu'),'--target','PeleC-RDEPrototype','-j','12']
    with (ev/'build.log').open('w') as log:r=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    if r.returncode:print((ev/'build.log').read_text()[-16000:]);raise RuntimeError('Prototype build failed')
    (ev/'manifest.json').write_text(json.dumps(dict(wall_seconds=time.monotonic()-start,command=command,
        mechanism_sha256=hashlib.sha256((mech/'mechanism.yaml').read_bytes()).hexdigest(),
        binary_sha256=hashlib.sha256((root/'build-gpu/Exec/RegTests/RDEPrototype/PeleC-RDEPrototype').read_bytes()).hexdigest(),
        note='Native PeleC equations. Initial/boundary states and CEPTR-generated chemistry only; no thermo inversion overlay.'),indent=2))
