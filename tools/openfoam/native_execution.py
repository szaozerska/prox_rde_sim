"""Shared native execution and evidence capture, imported inside CPU containers."""
def execute_case(payload:bytes,limit:int=600,ranks:int=1):
    import io,tarfile,subprocess,time,hashlib,base64,json,tempfile
    from pathlib import Path
    if not 1<=limit<=7200 or ranks not in (1,2,4,8,16):raise ValueError('Outside authorized bounded CPU envelope')
    root=Path(tempfile.mkdtemp(prefix='foam-case-'))
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:archive.extractall(root,filter='data')
    annulus=(root/'init_annulus.json').exists()
    if annulus:subprocess.run(['chown','-R','2101:2101',str(root)],check=True)
    if not (root/'system/controlDict').is_file():raise ValueError('Missing case')
    start=time.monotonic();records=[]
    commands=[['chemkinToFoam','mechanism.inp','thermo.dat','transport.foam','constant/foam/reactions.foam','constant/foam/thermo.foam'],['blockMesh'],['checkMesh','-allTopology','-allGeometry']]
    if annulus:commands += [['postProcess','-func','writeCellCentres','-time','0'],['python','/opt/cfd-tools/initialize_annulus.py']]
    if ranks>1:commands.append(['decomposePar','-force'])
    commands.append((['mpirun','--allow-run-as-root','-np',str(ranks),'detonationFoam_V2.0','-parallel'] if ranks>1 else ['detonationFoam_V2.0']))
    if ranks>1:commands.append(['reconstructPar'])
    if annulus:commands.append(['python','/opt/cfd-tools/tools/openfoam/analyze_annulus.py',str(root)])
    for i,cmd in enumerate(commands):
        stamp=time.monotonic();name=cmd[0]
        with (root/f'log.{i}.{name}').open('w') as log:
            try:
                r=subprocess.run((['runuser','-u','cfd-runner','--'] if annulus else [])+['bash','-c','cfd_command=("$@"); set --; source /opt/foam-env.sh && exec "${cfd_command[@]}"','bash',*cmd],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=600 if cmd[0]=='reconstructPar' or 'analyze_annulus.py' in ' '.join(cmd) else max(10,limit-(time.monotonic()-start)))
                code=r.returncode
            except subprocess.TimeoutExpired:code=124;log.write('\nTIME LIMIT: incomplete run\n')
        if name=='checkMesh' and code==0 and 'Mesh OK.' not in (root/f'log.{i}.{name}').read_text():code=65
        records.append(dict(command=cmd,returncode=code,wall_seconds=time.monotonic()-stamp))
        if code:break
    manifest=dict(commands=records,wall_seconds=time.monotonic()-start,input_sha256=hashlib.sha256(payload).hexdigest(),ranks=ranks,
        scope='Execution evidence only. Completion, clipping, chemistry and wave checks required.')
    (root/'run.json').write_text(json.dumps(manifest,indent=2))
    times=sorted((p for p in root.iterdir() if p.is_dir() and p.name.replace('.','',1).replace('e-','').isdigit()),key=lambda p:float(p.name))
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as t:
        for p in root.iterdir():
            if p.name.startswith('processor') or p.name=='dynamicCode':continue
            if annulus and (root/'preview.npz').exists() and p in times and p not in (times[0],times[-1]):continue
            t.add(p,arcname='case/'+p.name)
        t.add('/opt/foam-build',arcname='build')
    raw=out.getvalue()
    return dict(manifest=manifest,checks=json.loads((root/'checks.json').read_text()) if (root/'checks.json').exists() else None,case=json.loads((root/'case.json').read_text()) if (root/'case.json').exists() else None,preview_base64=base64.b64encode((root/'preview.npz').read_bytes()).decode() if (root/'preview.npz').exists() else None,artifact_sha256=hashlib.sha256(raw).hexdigest(),artifact_tar_gz_base64=base64.b64encode(raw).decode())
