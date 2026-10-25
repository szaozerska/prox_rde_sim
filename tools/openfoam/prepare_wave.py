"""Match the independent compact ZND profile in native detonationFoam."""
import argparse,json,shutil,sys
from pathlib import Path
import numpy as np
import cantera as ct
from prepare_compact import header
ROOT=Path(__file__).resolve().parents[2]
def prepare(base,reference,out,nx=512,dt=2e-10,stop=2e-7):
    base=Path(base);reference=Path(reference);out=Path(out);shutil.copytree(base,out)
    case=json.loads((reference/f'case_n{nx}.json').read_text());table=np.load(reference/f'initial_n{nx}.npz')['conserved_SI'];gas=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'))
    rho=table[:,0];velocity=table[:,1]/rho;Y=table[:,3:]/rho[:,None];e=table[:,2]/rho-.5*velocity**2;P=[];T=[]
    for ei,ri,yi in zip(e,rho,Y):gas.UVY=ei,1/ri,yi;P.append(gas.P);T.append(gas.T)
    length=case['length_m'];width=case['dx_m']*8
    (out/'system/blockMeshDict').write_text(header('blockMeshDict')+f'''convertToMeters 1;
vertices ((0 0 0) ({length} 0 0) ({length} {width} 0) (0 {width} 0) (0 0 {width}) ({length} 0 {width}) ({length} {width} {width}) (0 {width} {width}));
blocks (hex (0 1 2 3 4 5 6 7) ({nx} 1 1) simpleGrading (1 1 1)); edges ();
boundary (left {{ type patch; faces ((0 4 7 3)); }} right {{ type patch; faces ((1 2 6 5)); }} sides {{ type empty; faces ((0 1 5 4)(3 7 6 2)(0 3 2 1)(4 5 6 7)); }}); mergePatchPairs ();
''')
    (out/'system/controlDict').write_text(header('controlDict')+f'''libs ("libchemistryModel_DLB.so"); application detonationFoam_V2.0; startFrom startTime; startTime 0; stopAt endTime;
endTime {stop}; deltaT {dt}; writeControl runTime; writeInterval {stop/20}; purgeWrite 0; writeFormat ascii; writePrecision 16; timeFormat general; timePrecision 12; runTimeModifiable false; adjustTimeStep false; maxCo 0.2; maxDeltaT {dt};
''')
    (out/'system/decomposeParDict').write_text(header('decomposeParDict')+'numberOfSubdomains 16; method simple; simpleCoeffs { n (16 1 1); delta 0.001; }\n')
    boundaries='boundaryField { left { type zeroGradient; } right { type zeroGradient; } sides { type empty; } }\n'
    for p in (out/'0').iterdir():p.unlink()
    fields=[('p','[1 -1 -2 0 0 0 0]',P),('T','[0 0 0 1 0 0 0]',T)]+[(s,'[0 0 0 0 0 0 0]',Y[:,i]) for i,s in enumerate(gas.species_names)]
    for name,dim,values in fields:
        (out/'0'/name).write_text(header(name,'volScalarField')+f'dimensions {dim}; internalField nonuniform List<scalar>\n{nx}\n(\n'+'\n'.join(format(v,'.17g') for v in values)+'\n);\n'+boundaries)
    (out/'0/Ydefault').write_text(header('Ydefault','volScalarField')+'dimensions [0 0 0 0 0 0 0]; internalField uniform 0;\n'+boundaries)
    (out/'0/U').write_text(header('U','volVectorField')+f'dimensions [0 1 -1 0 0 0 0]; internalField nonuniform List<vector>\n{nx}\n(\n'+'\n'.join(f'({v:.17g} 0 0)' for v in velocity)+'\n);\n'+boundaries)
    case.update(dt_s=dt,stop_s=stop,transverse_width_m=width,scope='Native planar propagation; independent initialized ZND; no ongoing ignition; 16 MPI ranks.')
    (out/'wave_case.json').write_text(json.dumps(case,indent=2));shutil.copyfile(reference/'reference.json',out/'reference.json')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('reference');p.add_argument('out');a=p.parse_args();prepare(a.base,a.reference,a.out)
