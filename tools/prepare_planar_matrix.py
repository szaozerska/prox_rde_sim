"""Longer-domain, mesh, timestep and nonreacting-contact controls."""
import json,sys,copy
from pathlib import Path
import numpy as np
import cantera as ct
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));from prepare_failure_matrix import replace_input
sys.path.insert(0,str(ROOT/'tools/openfoam'));from prepare_wave import prepare as foam_wave

def main(out):
    out=Path(out).resolve();gpu=[];cpu=[];base=json.loads((ROOT/'tools/pelec/planar_template.json').read_text())
    scenarios=[('short_8um_dt01ns','short_profiles',512,2e-7,1e-10,600,True),('short_4um_dt01ns','short_profiles',1024,2e-7,1e-10,900,True),('short_2um_dt01ns','short_profiles',2048,2e-7,1e-10,900,False),('long_16um_2us','long_profiles',2048,2e-6,8e-10,1500,True),('long_8um_2us','long_profiles',4096,2e-6,4e-10,1800,False)]
    for name,refdir,nx,stop,dt,limit,on_gpu in scenarios:
        ref=out/refdir;w=json.loads((ref/f'case_n{nx}.json').read_text());w.update(final_time_s=stop,plot_interval_s=stop/20,scope='Finite-time formed-wave diagnostic; grid/time/window assessment, not engine validation.')
        if on_gpu:
            c=copy.deepcopy(base);c.update(n=nx,stop=stop,dt=dt,mesh_m=[w['dx_m']]*3,limitations=['Planar regular mesh; no injector or annular geometry.'],wave_case=w,diagnostic=dict(name=name,reference=str(ref)))
            for key,val in [('stop_time',stop),('amr.n_cell',f'{nx} 8 8'),('geometry.prob_hi',f'{w["length_m"]*100} {w["dx_m"]*800} {w["dx_m"]*800}'),('amr.plot_per',stop/20),('pelec.fixed_dt',dt)]:replace_input(c,key,val)
            p=out/(name+'.json');p.write_text(json.dumps(c,indent=2));gpu.append(dict(name=name,case=str(p),profile=str(ref/f'profile_n{nx}.dat'),limit=limit))
        d=out/('foam_'+name);foam_wave(ROOT/'runs3d/foam_compact_reactor_v6',ref,d,nx=nx,dt=dt,stop=stop)
        cpu.append(dict(name=name,case=str(d),limit=limit,ranks=16))
    # An equal-pressure, equal-velocity material interface should simply translate.
    # This isolates transport and mixture thermodynamics without combustion or shocks.
    g=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'));g.TPX=300,377916.97229176015,'CH4:1.176,O2:2';fresh=g.Y.copy();g.TP=1500,g.P;g.equilibrate('TP');burnt=g.Y.copy()
    nx=512;length=.008192;dx=length/nx;x=(np.arange(nx)+.5)*dx;table=[]
    for xi in x:
        g.TPY=(300 if xi<length/2 else 1500),377916.97229176015,(fresh if xi<length/2 else burnt);u=1000
        table.append(np.r_[g.density,g.density*u,g.density*(g.int_energy_mass+.5*u*u),g.density*g.Y])
    table=np.array(table);native=table.copy();native[:,0]*=.001;native[:,1]*=.1;native[:,2]*=10;native[:,3:]*=.001
    profile=out/'contact.dat';np.savetxt(profile,native,fmt='%.17e',header=f'{nx} {len(table[0])} {dx*100}',comments='')
    c=copy.deepcopy(base);c.update(n=nx,stop=1e-6,dt=2e-9,reacting=False,case_type='contact',mesh_m=[dx]*3,limitations=['Nonreacting constant-pressure moving material contact.'],diagnostic=dict(name='moving_contact',pressure_Pa=377916.97229176015,velocity_mps=1000,interface_m=length/2))
    c.pop('wave_case',None)
    for key,val in [('stop_time',1e-6),('geometry.prob_hi',f'{length*100} {dx*800} {dx*800}'),('amr.plot_per',5e-8),('pelec.fixed_dt',2e-9),('pelec.do_react',0)]:replace_input(c,key,val)
    c['inputs']='\n'.join(line for line in c['inputs'].splitlines() if not line.startswith(('cvode.','ode.')))+'\n'
    p=out/'moving_contact.json';p.write_text(json.dumps(c,indent=2));gpu.insert(0,dict(name='moving_contact',case=str(p),profile=str(profile),limit=300))
    for backend,cases in [('gpu',gpu),('cpu',cpu)]:
        (out/(backend+'_planar_manifest.json')).write_text(json.dumps(dict(output=str(out/(backend+'_planar_results')),cases=cases),indent=2))
if __name__=='__main__':main(sys.argv[1])
