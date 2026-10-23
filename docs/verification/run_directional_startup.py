"""Launch the directional case and interrupt after a saved 40 us field.

Native checkpoint validation in compare_directional_startup.py is required before
using the 40 us window. Run with the project .venv Python. Existing output rejected.
"""
import os,sys,subprocess,time,signal
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2]
base=root/'rde_sim_starter'; out=base/'runs/directional_startup_40us'
if out.exists(): raise SystemExit('Refusing existing output')
env=dict(os.environ,NUMBA_NUM_THREADS='2')
with (root/'docs/verification/directional_startup_run.txt').open('w') as log:
    p=subprocess.Popen([str(root/'.venv/bin/python'),'-u','run.py','--case','cases/run937_radial_directional.yaml','--out',str(out)],cwd=base,env=env,stdout=log,stderr=subprocess.STDOUT)
    stopped=False;last=-1;start=time.monotonic()
    while p.poll() is None:
        files=sorted((out/'fields').glob('step_*.npz'))
        if files:
            with np.load(files[-1]) as f: t=float(f['t'])
            bucket=int(t*1e6/10+1e-6)
            if bucket>last:
                print(f'Accepted field: {t*1e6:.3f} us; elapsed {time.monotonic()-start:.0f} s',flush=True);last=bucket
            if t>=40e-6-1e-14 and not stopped:
                p.send_signal(signal.SIGINT);stopped=True
        time.sleep(2)
    print(f'Exit {p.returncode}; requested bounded interrupt={stopped}',flush=True)
    if not stopped or p.returncode not in (0,130): raise SystemExit('Unexpected run termination; inspect native failure evidence')
