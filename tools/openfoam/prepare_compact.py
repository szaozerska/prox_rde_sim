"""Matched closed methane reactor; all chemistry is converted from the same YAML."""
import argparse,json,shutil
from pathlib import Path
import cantera as ct
from cantera import yaml2ck
ROOT=Path(__file__).resolve().parents[2]
def header(name,cls='dictionary'):
    return f'FoamFile {{ version 2.0; format ascii; class {cls}; object {name}; }}\n'
def prepare(out,temperature=1968.,pressure=22.984e6,stop=5e-7,dt=1e-9):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for d in ('0','constant/foam','system'):(out/d).mkdir(parents=True,exist_ok=True)
    source=ROOT/'.tooling/build/detonationFoam/tutorials/1D_NH3_O2_cracking_0.3_detonation'
    for f in ('system/fvSchemes','system/fvSolution','constant/momentumTransport','constant/combustionProperties','constant/solverTypeProperties','constant/chemistryProperties','constant/thermophysicalProperties'):
        shutil.copyfile(source/f,out/f)
    p=out/'constant/solverTypeProperties';p.write_text(p.read_text().replace('solverType  NS_Sutherland;','solverType  Euler;'))
    p=out/'constant/chemistryProperties';p.write_text(p.read_text().replace('1e-06','1e-10').replace('1e-03','1e-6').replace('initialChemicalTimeStep 1;','initialChemicalTimeStep 1e-12;'))
    p=out/'constant/thermophysicalProperties';p.write_text(p.read_text().replace('inertSpecie AR;','inertSpecie N2;').replace('#include "$FOAM_CASE/constant/foam/species.foam"','#include "$FOAM_CASE/constant/foam/reactions.foam"'))
    gas=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'));gas.TPX=temperature,pressure,'CH4:1.176,O2:2'
    yaml2ck.convert(gas,mechanism_path=out/'mechanism.inp',thermo_path=out/'thermo.dat',transport_path=out/'transport.dat',overwrite=True)
    reaction_file=out/'mechanism.inp';reaction_file.write_text(reaction_file.read_text().replace('REACTIONS CAL/MOLE MOLE\n','REACTIONS CAL/MOLE MOLES\n'))
    thermo=out/'thermo.dat';lines=thermo.read_text().splitlines();idx=lines.index('THERMO');lines[idx]='THERMO ALL';lines[idx+1]=''.join(f'{x:10.3f}' for x in (200,1000,6000));thermo.write_text('\n'.join(lines)+'\n')
    # OpenFOAM 8 expects a Sutherland dictionary here, despite the CLI label.
    # Fit pure-species Cantera viscosities at 300/1000 K; Euler does not use them.
    transport=[]
    for name in gas.species_names:
        inv=[]
        for temp in (300.,1000.):
            gas.TPX=temp,ct.one_atm,{name:1};inv.append(temp**1.5/gas.viscosity)
        As=700/(inv[1]-inv[0]);Ts=As*inv[0]-300
        transport.append(f'{name} {{ transport {{ As {As:.17g}; Ts {Ts:.17g}; }} }}')
    (out/'transport.foam').write_text('\n'.join(transport)+'\n')
    gas.TPX=temperature,pressure,'CH4:1.176,O2:2'
    (out/'system/blockMeshDict').write_text(header('blockMeshDict')+'''convertToMeters 1;
vertices ((0 0 0) (.001 0 0) (.001 .001 0) (0 .001 0) (0 0 .001) (.001 0 .001) (.001 .001 .001) (0 .001 .001));
blocks (hex (0 1 2 3 4 5 6 7) (2 2 2) simpleGrading (1 1 1)); edges ();
boundary (walls { type wall; faces ((0 4 7 3)(1 2 6 5)(0 1 5 4)(3 7 6 2)(0 3 2 1)(4 5 6 7)); }); mergePatchPairs ();
''')
    (out/'system/controlDict').write_text(header('controlDict')+f'''libs ("libchemistryModel_DLB.so");
application detonationFoam_V2.0; startFrom startTime; startTime 0; stopAt endTime;
endTime {stop}; deltaT {dt}; writeControl runTime; writeInterval {stop/20}; purgeWrite 0; writeFormat ascii; writePrecision 16; timeFormat general; timePrecision 12; runTimeModifiable false; adjustTimeStep false; maxCo 0.2; maxDeltaT {dt};
''')
    (out/'system/decomposeParDict').write_text(header('decomposeParDict')+'numberOfSubdomains 16; method scotch;\n')
    fields=[('p','[1 -1 -2 0 0 0 0]',pressure),('T','[0 0 0 1 0 0 0]',temperature)]+[(s,'[0 0 0 0 0 0 0]',float(y)) for s,y in zip(gas.species_names,gas.Y)]+[('Ydefault','[0 0 0 0 0 0 0]',0)]
    for name,dim,value in fields:
        (out/'0'/name).write_text(header(name,'volScalarField')+f'dimensions {dim}; internalField uniform {value:.17g}; boundaryField {{ walls {{ type zeroGradient; }} }}\n')
    (out/'0/U').write_text(header('U','volVectorField')+'dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0); boundaryField { walls { type slip; } }\n')
    reactor=ct.IdealGasReactor(gas,energy='on',clone=True);net=ct.ReactorNet([reactor]);net.rtol=1e-11;net.atol=1e-20
    history=[]
    for i in range(21):
        t=i*stop/20
        if t:net.advance(t)
        history.append(dict(time_s=t,T=reactor.T,p=reactor.phase.P,Y=reactor.phase.Y.tolist()))
    (out/'reference.json').write_text(json.dumps(dict(species=gas.species_names,history=history,initial_temperature_K=temperature,initial_pressure_Pa=pressure,scope='Homogeneous constant-volume control, not a detonation or engine'),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();prepare(a.output)
