"""Use upstream CEPTR in its isolated Linux environment with NumPy 1.26."""
from pathlib import Path
import modal,json
ROOT=Path(__file__).resolve().parents[2]
image=(modal.Image.debian_slim(python_version='3.12').pip_install('cantera==3.1.0','numpy==1.26.4','sympy==1.14.0','symengine==0.13.0','Pint==0.23','networkx==2.8.8','pandas==2.2.3','toml==0.10.2','pyarrow==15.0.2','matplotlib==3.9.4','scipy==1.15.2','clang-format==20.1.5')
    .add_local_dir(ROOT/'.tooling/PeleC/Submodules/PelePhysics/Support/ceptr','/opt/ceptr',copy=True)
    .add_local_file(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml','/opt/mech/mechanism.yaml',copy=True))
app=modal.App('prox-rde-chemistry-generation',include_source=False)
@app.function(image=image,serialized=True,cpu=2,memory=8192,timeout=600)
def generate():
    import subprocess,os
    from pathlib import Path
    env=dict(os.environ,PYTHONPATH='/opt/ceptr')
    r=subprocess.run(['python','-m','ceptr','-f','/opt/mech/mechanism.yaml'],env=env,capture_output=True,text=True,timeout=480)
    if r.returncode:raise RuntimeError(r.stdout[-3000:]+r.stderr[-6000:])
    return dict(files={p.name:p.read_text() for p in Path('/opt/mech').glob('mechanism.*')},log=r.stdout+r.stderr)
@app.local_entrypoint()
def main():
    result=generate.remote()
    out=ROOT/'rde3d/mechanisms/FFCMy12'
    for name,content in result['files'].items():
        if name!='mechanism.yaml':(out/name).write_text(content)
    (out/'generation.log').write_text(result['log'])
    print('Generated',list(result['files']))
