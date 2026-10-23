"""Build a profile initializer on the already verified GRI native solver image."""
def build_wave():
    import hashlib,json,shutil,subprocess,time
    from pathlib import Path
    root=Path('/opt/PeleC');evidence=Path('/opt/pelec-wave-build');evidence.mkdir()
    case=root/'Exec/RegTests/FormedWave';shutil.copytree(root/'Exec/RegTests/MethaneZeroD',case)
    for name in ('prob.H','prob.cpp','prob_parm.H'):shutil.copyfile(Path('/opt/wave-case')/name,case/name)
    register=root/'Exec/RegTests/CMakeLists.txt'
    register.write_text(register.read_text()+'\nadd_subdirectory(FormedWave)\n')
    command=['cmake','--build',str(root/'build-gpu'),'--target','PeleC-FormedWave','-j','12']
    started=time.monotonic()
    with (evidence/'build.log').open('w') as log:
        result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    if result.returncode:
        print((evidence/'build.log').read_text()[-18000:],flush=True)
        raise RuntimeError('Native formed-wave build failed')
    exe=root/'build-gpu/Exec/RegTests/FormedWave/PeleC-FormedWave'
    (evidence/'manifest.json').write_text(json.dumps(dict(command=command,wall_seconds=time.monotonic()-started,
        binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
        overlay_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in case.glob('prob*')},
        scope='Initialization only; unchanged GRI polynomial-law native evolution and existing explicit inverse-bound overlay'),indent=2)+'\n')
