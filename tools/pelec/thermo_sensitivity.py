"""Independent hot-thermo sensitivity with GRI reactions unchanged; not a new CFD mechanism."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import cantera as ct
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'rde_sim_starter'))
from reference import _libraries,_cj,_znd


def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    root=ROOT/'.tooling/PeleC/Submodules/PelePhysics/Mechanisms'
    gri_path=root/'grimech30/mechanism.yaml';ffcm_path=root/'FFCM1_Red/mechanism.yaml'
    gri=ct.Solution(str(gri_path));ffcm=ct.Solution(str(ffcm_path))
    alternatives={s.name:s for s in ffcm.species()}
    replaced=[];species=[]
    for original in gri.species():
        if original.name in alternatives:
            replacement=alternatives[original.name]
            if original.composition!=replacement.composition:raise ValueError('Elemental identity changed')
            original.thermo=replacement.thermo
            replaced.append(original.name)
        species.append(original)
    gas=ct.Solution(thermo='ideal-gas',kinetics='gas',species=species,reactions=gri.reactions())
    gas.write_yaml(args.output/'gri_reactions_alternative_thermo.yaml',precision=17)
    # Reload exactly the serialized sensitivity input used by SDToolbox.
    alternative_path=args.output/'gri_reactions_alternative_thermo.yaml'
    gas=ct.Solution(str(alternative_path))
    if gas.n_reactions!=gri.n_reactions or gas.species_names!=gri.species_names:
        raise ValueError('Kinetic scheme or species identity changed')
    roundtrip_differences=[]
    def compare_input(a,b,path):
        if isinstance(a,dict):
            if set(a)!=set(b):raise ValueError('Reaction keys changed: '+path)
            for key in a:compare_input(a[key],b[key],path+'/'+key)
        elif isinstance(a,(list,tuple)):
            if len(a)!=len(b):raise ValueError('Reaction array changed: '+path)
            for i,(x,y) in enumerate(zip(a,b)):compare_input(x,y,path+'/'+str(i))
        elif isinstance(a,(int,float)) and not isinstance(a,bool):
            error=abs(a-b)/max(1.,abs(a),abs(b))
            if error>5e-14:raise ValueError('Rate parameter changed beyond serialization roundoff: '+path)
            if a!=b:roundtrip_differences.append(dict(path=path,before=a,after=b,relative_error=error))
        elif a!=b:raise ValueError('Reaction structure changed: '+path)
    for i,(a,b) in enumerate(zip(gri.reactions(),gas.reactions())):
        compare_input(dict(a.input_data),dict(b.input_data),str(i))
    max_forward_error=0.
    for T in (300.,1001.,1800.,3000.,4000.,5000.):
        for pressure in (101325.,22984274.661736142):
            for condition in ('fresh','products'):
                gri.TPX=T,pressure,'CH4:1.176,O2:2'
                if condition=='products':gri.equilibrate('TP')
                gas.TPY=gri.T,gri.P,gri.Y
                max_forward_error=max(max_forward_error,float(np.max(abs(gas.forward_rate_constants-gri.forward_rate_constants)/np.maximum(abs(gri.forward_rate_constants),1e-250))))
    if max_forward_error>1e-13:raise ValueError('Serialized forward-rate operator changed')
    _,post,znd,thermo,manifest=_libraries()
    references={};ranges={};refinement={}
    for label,path in [('baseline',gri_path),('alternative_thermo',alternative_path)]:
        ref,initial,working,hf=_cj(ct,post,thermo,377916.97229176015,300.,1.176,mechanism=str(path))
        working.TDY=ref['VN']['T'],ref['VN']['rho'],ref['VN']['Y']
        coarse,_=_znd(ct,znd,thermo,ref,initial,working,hf,1e-7,1e-11,2e-9)
        working.TDY=ref['VN']['T'],ref['VN']['rho'],ref['VN']['Y']
        zsummary,profile=_znd(ct,znd,thermo,ref,initial,working,hf,2e-8,2e-12,1e-9)
        refinement[label]={key:abs(zsummary[key]/coarse[key]-1) for key in
            ('induction_time_max_dTdt_s','distance_at_max_dTdt_m')}
        refinement[label]['half_heat_length_relative']=abs(zsummary['heat_fraction_lengths_m']['0.5']/coarse['heat_fraction_lengths_m']['0.5']-1)
        if max(refinement[label].values())>5e-3:raise ValueError('ZND refinement exceeded existing 0.5% criterion')
        save(args.output/f'{label}_znd_coarse.json',coarse)
        references[label]={'CJ':ref,'ZND':zsummary}
        phase=ct.Solution(str(path));outside=[]
        for T,Y in zip(profile['temperature_K'],profile['species_Y'].T):
            outside.append(sum(y for y,s in zip(Y,phase.species()) if T>s.thermo.max_temp or T<s.thermo.min_temp))
        ranges[label]=dict(max_mass_outside_published_fits=float(max(outside)),
            CJ_mass_in_unreplaced_species=float(sum(y for y,s in zip(ref['CJ']['Y'],phase.species_names) if s not in replaced)))
        save(args.output/f'{label}_reference.json',references[label]);np.savez_compressed(args.output/f'{label}_znd.npz',**profile)
        print(label,ref['CJ_speed_mps'],zsummary['induction_time_max_dTdt_s'],flush=True)
    a,b=references['baseline'],references['alternative_thermo']
    differences=dict(CJ_speed_relative=b['CJ']['CJ_speed_mps']/a['CJ']['CJ_speed_mps']-1,
        CJ_temperature_relative=b['CJ']['CJ']['T']/a['CJ']['CJ']['T']-1,
        induction_time_relative=b['ZND']['induction_time_max_dTdt_s']/a['ZND']['induction_time_max_dTdt_s']-1,
        half_heat_length_relative=b['ZND']['heat_fraction_lengths_m']['0.5']/a['ZND']['heat_fraction_lengths_m']['0.5']-1)
    save(args.output/'sensitivity.json',dict(replaced_species=replaced,differences=differences,fit_ranges=ranges,refinement=refinement,
        numerical_refinement_passed=True,
        serialization_parameter_differences=roundtrip_differences,forward_rate_max_relative_difference=max_forward_error,
        input_sha256={str(path.name):hashlib.sha256(path.read_bytes()).hexdigest() for path in [alternative_path]},
        original_gri_sha256=hashlib.sha256(gri_path.read_bytes()).hexdigest(),
        alternate_thermo_source_sha256=hashlib.sha256(ffcm_path.read_bytes()).hexdigest(),sdtoolbox=manifest,
        scope='Independent sensitivity only: GRI forward reactions unchanged, available common-species thermo substituted from existing FFCM1_Red data. Reverse rates change through thermodynamics. Neither a fully validated replacement nor an uncertainty bound; not used by native CFD.'))
    print(json.dumps(differences,indent=2))


if __name__=='__main__':main()
