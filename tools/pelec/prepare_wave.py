"""Independent formed-ZND initial cell averages; no fitted reaction/heat source."""
import argparse,hashlib,json,sys,shutil
from pathlib import Path
import numpy as np
from native_generated_reference import make_reference
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'rde_sim_starter'))
from reference import _libraries,_cj,_znd

def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--reference',type=Path);p.add_argument('--mechanism',type=Path,default=ROOT/'.tooling/PeleC/Submodules/PelePhysics/Mechanisms/grimech30/mechanism.yaml');p.add_argument('--length',type=float,default=.002048);p.add_argument('--shock',type=float,default=.000512);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    ct,post,znd,thermo,manifest=_libraries()
    mechanism=a.mechanism
    native=a.output/'native_constants.yaml'
    if a.reference:
        reference=json.loads((a.reference/'reference.json').read_text())
        if reference['conventions']['mechanism_sha256']!=hashlib.sha256(mechanism.read_bytes()).hexdigest():
            raise ValueError('Cached reference mechanism mismatch')
        if max(reference['refinement'].values())>5e-3 or reference['ZND']['atol']>1e-14:
            raise ValueError('Cached reference did not pass the tightened integration gate')
        for name in ('native_constants.yaml','reference.json','znd.npz'):shutil.copyfile(a.reference/name,a.output/name)
        ref=reference['CJ'];profile=dict(np.load(a.output/'znd.npz'))
    else:
        gas,conventions=make_reference(mechanism);native=a.output/'native_constants.yaml';gas.write_yaml(native,precision=17)
        ref,initial,working,hf=_cj(ct,post,thermo,377916.97229176015,300.,1.176,mechanism=str(native.resolve()))
        coarse,_=_znd(ct,znd,thermo,ref,initial,working,hf,1e-7,1e-11,2e-9)
        working.TDY=ref['VN']['T'],ref['VN']['rho'],ref['VN']['Y']
        strict,profile=_znd(ct,znd,thermo,ref,initial,working,hf,2e-8,1e-14,1e-9)
        differences={key:abs(strict[key]/coarse[key]-1) for key in ('induction_time_max_dTdt_s','distance_at_max_dTdt_m')}
        differences['half_heat_length_relative']=abs(strict['heat_fraction_lengths_m']['0.5']/coarse['heat_fraction_lengths_m']['0.5']-1)
        if max(differences.values())>5e-3:raise ValueError('Reference refinement failed')
        np.savez_compressed(a.output/'znd.npz',**profile)
        save(a.output/'reference.json',dict(CJ=ref,ZND=strict,coarse_ZND=coarse,refinement=differences,conventions=conventions,sdtoolbox=manifest))
    distance=profile['distance_m'];speed=ref['CJ_speed_mps'];length=a.length;shock=a.shock
    if distance[-1]<shock:raise ValueError('No extrapolation of truncated ZND permitted')
    if profile['species_Y'].min() < -1e-12:raise ValueError('Reference has significant negative species')
    rawY=profile['species_Y'];Y=np.maximum(rawY,0);Y/=Y.sum(axis=0)
    correction=float(np.max(abs(Y-rawY)))
    if correction>1e-10:raise ValueError('Reference roundoff cleanup exceeded limit')
    gas=ct.Solution(str(native));conserved=[];maxchar=0.
    for rho,T,y,u in zip(profile['density_kg_m3'],profile['temperature_K'],Y.T,speed-profile['velocity_mps']):
        gas.TDY=T,rho,y
        conserved.append(np.r_[rho,rho*u,rho*(gas.int_energy_mass+.5*u*u),rho*y])
        maxchar=max(maxchar,abs(u)+gas.sound_speed)
    conserved=np.array(conserved)
    gas.TPY=300.,ref['pressure_Pa'],ref['initial']['Y']
    fresh=np.r_[gas.density,0.,gas.density*gas.int_energy_mass,gas.density*gas.Y]
    # All interpolation and quadrature operates on conserved quantities in SI.
    # Analytic antiderivative of the piecewise-linear conserved profile.
    widths=np.diff(distance)
    slopes=np.diff(conserved,axis=0)/widths[:,None]
    prefix=np.vstack([np.zeros(conserved.shape[1]),np.cumsum(.5*(conserved[:-1]+conserved[1:])*widths[:,None],axis=0)])
    def primitive(points):
        points=np.asarray(points)
        if np.any(points<0) or np.any(points>distance[-1]):raise ValueError('Reference integral cannot extrapolate')
        indices=np.minimum(np.searchsorted(distance,points,side='right')-1,len(distance)-2)
        delta=points-distance[indices]
        return prefix[indices]+conserved[indices]*delta[:,None]+.5*slopes[indices]*delta[:,None]**2
    total_target=primitive(np.array([shock]))[0]+(length-shock)*fresh
    for nx in (256,512):
        dx=length/nx;centers=(np.arange(nx)+.5)*dx
        tables=[]
        for order in (4,8):
            nodes,weights=np.polynomial.legendre.leggauss(order);table=np.zeros((nx,len(fresh)))
            for node,weight in zip(nodes,weights):
                behind=shock-(centers+node*dx/2)
                sample=np.column_stack([np.interp(np.maximum(behind,0),distance,conserved[:,j]) for j in range(len(fresh))])
                sample[behind<0]=fresh
                table+=weight/2*sample
            tables.append(table)
        scale=np.maximum(np.max(abs(tables[1]),axis=0),1e-20)
        quadrature=float(np.max(np.mean(abs(tables[1]-tables[0]),axis=0)/scale))
        lo=np.arange(nx)*dx;hi=lo+dx
        table=(primitive(np.maximum(shock-lo,0))-primitive(np.maximum(shock-hi,0))+
            np.maximum(hi-np.maximum(lo,shock),0)[:,None]*fresh)/dx
        integral_error=float(np.max(abs(table.sum(axis=0)*dx-total_target)/np.maximum(abs(total_target),1e-20)))
        if integral_error>1e-12:raise ValueError('Conserved profile integration failed')
        if table[:,3:].min() < -1e-16:raise ValueError('Negative integrated species')
        np.savez_compressed(a.output/f'initial_n{nx}.npz',x_m=centers,conserved_SI=table)
        # rho: kg/m3 -> g/cm3; momentum: kg/m2/s -> g/cm2/s;
        # energy density: J/m3 -> erg/cm3; species: kg/m3 -> g/cm3.
        native_table=table.copy();native_table[:,0]*=.001;native_table[:,1]*=.1;native_table[:,2]*=10;native_table[:,3:]*=.001
        path=a.output/f'profile_n{nx}.dat'
        np.savetxt(path,native_table,fmt='%.17e',header=f'{nx} {len(fresh)} {dx*100:.17e}',comments='')
        save(a.output/f'case_n{nx}.json',dict(nx=nx,length_m=length,dx_m=dx,shock_initial_m=shock,
            CJ_speed_mps=speed,final_time_s=2e-7,plot_interval_s=1e-8,max_initial_characteristic_mps=maxchar,
            boundary_causal_margin_m=shock-(maxchar-speed)*2e-7,discarded_quadrature_relative_L1=quadrature,
            averaging='Exact integral of the independently computed piecewise-linear conserved profile',integral_relative_error=integral_error,
            reference_species_cleanup_max=correction,species=gas.species_names,
            profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),independent_reference_checked=True,
            scope='Short planar numerical propagation of an initialized selected-mechanism ZND wave; no continuing ignition, engine, or sustained rotating-wave claim'))
    print('Prepared native-constant reference and conservative cell averages',flush=True)
if __name__=='__main__':main()
