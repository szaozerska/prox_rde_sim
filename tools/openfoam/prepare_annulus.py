"""Exploratory body-fitted 3D annulus, radial impingement and finite +theta charge."""
import argparse,json,math,shutil,sys
from pathlib import Path
import numpy as np
import cantera as ct
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from rde3d.geometry import Annulus,build_mesh,block_mesh_dict
from prepare_compact import header

def inlet(kind):
    cls='rdeInlet'+kind
    common='''
const fvPatchScalarField& pp = this->patch().lookupPatchField<volScalarField, scalar>("p");
scalarField pi(pp.patchInternalField());
const vectorField& points=this->patch().Cf();
'''
    dtype='vectorField' if kind=='U' else 'scalarField'
    common+=f'{dtype} values(this->patchInternalField());\n'
    common+='''forAll(values,i) {
const scalar x=points[i].x(),y=points[i].y(),r=Foam::sqrt(x*x+y*y),theta=Foam::atan2(y,x);
const scalar period=2*constant::mathematical::pi/72;
const scalar arc=.0356*(theta-period*std::floor(theta/period+.5));
const scalar off=.00216*Foam::tan(constant::mathematical::pi/6),dr=r-.0356;
const bool fuel=(dr+off)*(dr+off)*.75+arc*arc < .0003935*.0003935;
const bool oxygen=(dr-off)*(dr-off)*.75+arc*arc < .0006225*.0006225;
const scalar p0=fuel?1399400.:1309500.;
const bool open=(fuel||oxygen)&&pi[i]<p0;
const scalar gamma=fuel?1.303:1.394,cp=fuel?2229.:919.;
const scalar ratio=Foam::max(pi[i]/p0,Foam::pow(2/(gamma+1),gamma/(gamma-1)));
const scalar temperature=300*Foam::pow(ratio,(gamma-1)/gamma);
const scalar speed=Foam::sqrt(Foam::max(scalar(0),2*cp*(300-temperature)));
'''
    if kind=='U':common+='if(open) { scalar ur=(fuel?1:-1)*.5*speed; values[i]=vector(ur*x/r,ur*y/r,.8660254037844386*speed); } else values[i].z()=0;\n'
    elif kind=='P':common+='if(open)values[i]=p0*ratio;\n'
    elif kind=='T':common+='if(open)values[i]=temperature;\n'
    else:common+='if(open)values[i]=(fuel&&this->internalField().name()=="CH4")||(oxygen&&this->internalField().name()=="O2")?1.:0.;\n'
    common+='}\nthis->operator==(values);\n'
    value='(0 0 0)' if kind=='U' else '300' if kind=='T' else '377916.97229176015' if kind=='P' else '0'
    return f'''type codedFixedValue; value uniform {value}; name {cls};
codeOptions
#{{
-I$(LIB_SRC)/meshTools/lnInclude
#}};
codeLibs
#{{
-lfiniteVolume -lmeshTools
#}};
codeInclude
#{{
#include "fvCFD.H"
#include "mathematicalConstants.H"
#include <cmath>
#}};
code
#{{
{common}
#}};
'''
def prepare(base,out,ntheta=288,nr=8,nz=24,stop=1e-6,dt=2e-8):
    out=Path(out);shutil.copytree(base,out)
    g=Annulus(.0381,.0331,.0762,.0762);mesh=build_mesh(g,ntheta,nr,nz)
    angle=-math.pi/ntheta;co=math.cos(angle);si=math.sin(angle)
    def rotate(v):x,y,z=v;return (co*x-si*y,si*x+co*y,z)
    mesh['vertices']=[rotate(v) for v in mesh['vertices']];mesh['arcs']={k:rotate(v) for k,v in mesh['arcs'].items()}
    # Axial grading resolves the fresh layer better while retaining the full length.
    text=block_mesh_dict(mesh).replace('simpleGrading (1 1 1)','simpleGrading (1 1 20)');(out/'system/blockMeshDict').write_text(text)
    (out/'system/controlDict').write_text(header('controlDict')+f'''libs ("libchemistryModel_DLB.so"); application detonationFoam_V2.0; startFrom startTime; startTime 0; stopAt endTime;
endTime {stop}; deltaT {dt}; writeControl runTime; writeInterval {stop/20}; purgeWrite 0; writeFormat ascii; writePrecision 12; timeFormat general; timePrecision 12; runTimeModifiable false; adjustTimeStep false; maxCo 0.2; maxDeltaT {dt};
''')
    (out/'system/decomposeParDict').write_text(header('decomposeParDict')+'numberOfSubdomains 16; method scotch;\n')
    gas=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'));gas.TPX=300,377916.97229176015,'CH4:1.176,O2:2';fresh=gas.Y.copy();gas.TP=1500,377916.97229176015;gas.equilibrate('TP');products=gas.Y.copy();gas.TPX=4000,1e7,'CH4:1.176,O2:2';gas.equilibrate('TP');seed_Y=gas.Y.copy()
    cfg=dict(kind='annulus',solver='detonationFoam',ntheta=ntheta,nr=nr,nz=nz,cells=ntheta*nr*nz,dt=dt,stop=stop,p0=377916.97229176015,T0=300,Tprod=1500,height=.0038,seed_p=1e7,seed_T=4000,seed_u=1900,seed_length=.03,seed_theta=math.pi/2,Y=fresh.tolist(),Yprod=products.tolist(),Yseed=seed_Y.tolist(),species=gas.species_names,
        scope='Exploratory reactive Euler with finite initialized +theta charge; separate opposing radial jets. Coarse mouths are not an injector design prediction; no core expansion or wall heat loss.')
    (out/'init_annulus.json').write_text(json.dumps(cfg,indent=2))
    for f in (out/'0').iterdir():f.unlink()
    fields=[('p','[1 -1 -2 0 0 0 0]',cfg['p0'],'P'),('T','[0 0 0 1 0 0 0]',300.,'T')]+[(s,'[0 0 0 0 0 0 0]',float(v),'Y') for s,v in zip(gas.species_names,fresh)]+[('Ydefault','[0 0 0 0 0 0 0]',0.,'Y')]
    for name,dim,val,kind in fields:
        bc='boundaryField { injector { '+inlet(kind)+' } innerWall { type zeroGradient; } outerWall { type zeroGradient; } outlet { type zeroGradient; } }\n'
        (out/'0'/name).write_text(header(name,'volScalarField')+f'dimensions {dim}; internalField uniform {val:.17g};\n'+bc)
    (out/'0/U').write_text(header('U','volVectorField')+'dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);\nboundaryField { injector { '+inlet('U')+' } innerWall { type slip; } outerWall { type slip; } outlet { type zeroGradient; } }\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('out');p.add_argument('--ntheta',type=int,default=288);p.add_argument('--stop',type=float,default=1e-6);p.add_argument('--dt',type=float,default=2e-8);a=p.parse_args();prepare(**vars(a))
