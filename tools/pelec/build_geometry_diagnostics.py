"""Add read-only native surface diagnostics to a copied upstream Sod case."""
def build_geometry_diagnostics():
    import hashlib,json,shutil,subprocess,time
    from pathlib import Path
    root=Path('/opt/PeleC');case=root/'Exec/RegTests/GeometryDiagnostics'
    shutil.copytree(root/'Exec/RegTests/Sod',case)
    prob=case/'prob.cpp';original=prob.read_text()
    hook='void\nPeleC::problem_post_init()\n{\n}'
    if original.count(hook)!=1:raise RuntimeError('Unexpected pinned Sod diagnostic hook')
    includes='#include <AMReX_BoxIterator.H>\n#include <AMReX_EBFabFactory.H>\n#include <AMReX_MultiCutFab.H>\n#include <iomanip>\n'
    prob.write_text(includes+original.replace(hook,Path('/opt/geometry-diagnostics/post_init.cpp').read_text()))
    cmake=root/'Exec/RegTests/CMakeLists.txt';cmake.write_text(cmake.read_text()+'\nadd_subdirectory(GeometryDiagnostics)\n')
    evidence=Path('/opt/pelec-geometry-build');evidence.mkdir()
    command=['cmake','--build',str(root/'build-gpu'),'--target','PeleC-GeometryDiagnostics','-j','12']
    started=time.monotonic()
    with (evidence/'build.log').open('w') as log:
        result=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
    if result.returncode:
        print((evidence/'build.log').read_text()[-16000:],flush=True)
        raise RuntimeError('Native geometry diagnostic build failed')
    exe=root/'build-gpu/Exec/RegTests/GeometryDiagnostics/PeleC-GeometryDiagnostics'
    (evidence/'manifest.json').write_text(json.dumps(dict(command=command,wall_seconds=time.monotonic()-started,
        case_source_sha256=hashlib.sha256(prob.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
        scope='Read-only post-init surface/port extraction; no changed native numerical physics'),indent=2)+'\n')
