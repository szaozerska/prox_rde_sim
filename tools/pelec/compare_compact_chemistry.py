"""Independent ignition sensitivity; neither mechanism is treated as truth."""
import json,hashlib,time,tempfile
from pathlib import Path
import cantera as ct
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def main(output):
    cases=[]
    for label,path in [('FFCMy12',ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'),('GRI30',ROOT/'.tooling/PeleC/Submodules/PelePhysics/Mechanisms/grimech30/mechanism.yaml')]:
        for pressure in (377916.97229176015,1.35e6,22.984e6):
            for temperature in (1000.,1500.,1968.):
                gas=ct.Solution(str(path));gas.TPX=temperature,pressure,'CH4:1.176,O2:2';reactor=ct.IdealGasReactor(gas,energy='on',clone=True);net=ct.ReactorNet([reactor]);net.rtol=1e-10;net.atol=1e-18;net.max_time_step=2e-6
                started=time.monotonic();last_t=0.;last_T=temperature;delay=None
                while net.time<.002:
                    net.step()
                    if reactor.T>=temperature+400:
                        delay=last_t+(net.time-last_t)*(temperature+400-last_T)/(reactor.T-last_T);break
                    last_t=net.time;last_T=reactor.T
                row=dict(mechanism=label,pressure_Pa=pressure,T0_K=temperature,ignition_delta400K_s=delay,observation_limit_s=.002,wall_seconds=time.monotonic()-started)
                cases.append(row);print(row,flush=True)
    nominal=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'))
    from cantera import yaml2ck,ck2yaml
    with tempfile.TemporaryDirectory() as directory:
        d=Path(directory)
        yaml2ck.convert(nominal,mechanism_path=d/'chem.inp',thermo_path=d/'thermo.dat',transport_path=d/'transport.dat')
        ck2yaml.convert(str(d/'chem.inp'),str(d/'thermo.dat'),str(d/'transport.dat'),out_name=str(d/'roundtrip.yaml'),quiet=True)
        roundtrip=ct.Solution(str(d/'roundtrip.yaml'))
    err=0.
    for T,P in [(300,1e5),(1000,1.35e6),(1968,22.984e6),(4000,12e6)]:
        for g in (nominal,roundtrip):g.TPX=T,P,'CH4:1.176,O2:2'
        a=nominal.forward_rate_constants;b=roundtrip.forward_rate_constants;err=max(err,float(np.max(abs(a-b)/np.maximum(abs(a),1e-300))))
    Path(output).write_text(json.dumps(dict(cases=cases,chemkin_roundtrip_forward_rate_max_relative=err,
        note='Homogeneous constant-volume ignition to T0+400 K. No ignition before 2 ms is a censored observation, not infinite delay. This is mechanism sensitivity, not validation against measurements.'),indent=2))
if __name__=='__main__':
    import sys;main(sys.argv[1])
