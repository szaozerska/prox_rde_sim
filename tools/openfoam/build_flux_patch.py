"""Build an explicitly marked transport-flux diagnostic variant."""
def patch_flux():
    import subprocess,hashlib,json
    from pathlib import Path
    root=Path('/opt/detonation-src/applications/solvers/detonationFoam_V2.0')
    source=root/'solverTypeEuler/rhoYEqn_Euler.H';before=source.read_text()
    needle='        phi,\n        mesh.divScheme';replacement='        rhoPhi,\n        mesh.divScheme'
    if before.count(needle)!=1:raise RuntimeError('Unexpected pinned species equation')
    after=before.replace(needle,replacement);source.write_text(after)
    evidence=Path('/opt/foam-build')
    (evidence/'flux_patch.json').write_text(json.dumps(dict(before_sha256=hashlib.sha256(before.encode()).hexdigest(),after_sha256=hashlib.sha256(after.encode()).hexdigest(),change='Construct species convection with rhoPhi, the mass flux actually used in fvmDiv. Experimental repair, not unmodified upstream.'),indent=2))
    with (evidence/'flux_patch_build.log').open('w') as log:
        r=subprocess.run(['bash','-c','source /opt/foam-env.sh && wmake -j 8'],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    if r.returncode:raise RuntimeError((evidence/'flux_patch_build.log').read_text()[-6000:])
