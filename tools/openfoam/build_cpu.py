def build_solver(lock):
    import subprocess, hashlib, json, time
    from pathlib import Path
    root=Path('/opt/detonation-src')
    subprocess.run(['git','clone','--depth','1','--branch',lock['branch'],lock['repository'],str(root)],check=True)
    subprocess.run(['git','-C',str(root),'fetch','--depth','1','origin',lock['commit']],check=True)
    subprocess.run(['git','-C',str(root),'checkout','--detach',lock['commit']],check=True)
    case=root/'applications/solvers/detonationFoam_V2.0'
    # Observe upstream clipping without changing its numerical update.
    field=case/'solverTypeEuler/rhoYEqn_Euler.H'; original=field.read_text()
    text=original.replace('volScalarField Yt(0.0*Y[0]);','volScalarField Yt(0.0*Y[0]);\n    scalar preClipMin=0, clippedMass=0;')
    text=text.replace('Yi.max(0.0);', '''preClipMin = min(preClipMin, gMin(Yi.primitiveField()));
            forAll(Yi, celli) clippedMass += max(-Yi[celli], scalar(0))*rho[celli]*mesh.V()[celli];
            Yi.max(0.0);''')
    text=text.replace('Y[inertIndex].max(0.0);', '''scalar inertMin=gMin(Y[inertIndex].primitiveField());
    reduce(clippedMass, sumOp<scalar>());
    Info<< "SPECIES_AUDIT time=" << runTime.value() << " preClipMin=" << preClipMin
        << " clippedMass=" << clippedMass << " inertMin=" << inertMin << endl;
    Y[inertIndex].max(0.0);''')
    if text==original or text.count('SPECIES_AUDIT')!=1:raise RuntimeError('Unexpected source for clipping instrumentation')
    field.write_text(text)
    evidence=Path('/opt/foam-build');evidence.mkdir()
    commands=['wmake -j 8 dynamicMesh2D/dynamicMesh','wmake -j 8 dynamicMesh2D/dynamicFvMesh',
        'wmake -j 8 DLBFoam-1.0-1.0_OF8/src/thermophysicalModels/chemistryModel',
        'wmake -j 8 fluxSchemes_improved','wmake -j 8']
    start=time.monotonic()
    for i,command in enumerate(commands):
        with (evidence/f'build-{i}.log').open('w') as log:
            r=subprocess.run(['bash','-c','source /opt/foam-env.sh && mkdir -p "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN" && '+command],cwd=case,stdout=log,stderr=subprocess.STDOUT,timeout=1500)
        if r.returncode:
            print((evidence/f'build-{i}.log').read_text()[-12000:]);raise RuntimeError('OpenFOAM build failed')
    (evidence/'manifest.json').write_text(json.dumps(dict(source=lock,wall_seconds=time.monotonic()-start,
        original_species_header_sha256=hashlib.sha256(original.encode()).hexdigest(),
        instrumented_species_header_sha256=hashlib.sha256(text.encode()).hexdigest(),
        change='Read-only measurements before existing species clipping; solver update unchanged.'),indent=2))
