"""NETL's stated initial fields, with explicit assumptions and separate legacy geometry."""
import argparse,json,math
from pathlib import Path
import cantera as ct
import numpy as np
from prepare_prototype import prepare,MECH


def prepare_startup(output,mesh_um=200,stop=2e-4,dt=5e-9,base_n=192,max_level=None,feed=2,reacting=True,seed=True,box=64):
    if mesh_um not in (100,200) or base_n%8 or stop<=0 or dt<=0:raise ValueError('Invalid mesh/time request')
    level=(1 if mesh_um==200 else 2) if max_level is None else max_level
    if level<0 or level>2:raise ValueError('Unsupported AMR level')
    c=prepare(output,mode='annulus',n=base_n,stop=stop,dt=dt,feed=feed,seed=seed,reacting=reacting,height=.005,clean_species=True)
    g=ct.Solution(str(MECH));g.TPX=300,1e6,'CH4:1,O2:2';fresh=g.Y.copy();g.TPX=300,1e5,'O2:1,N2:3.76';air=g.Y.copy()
    # Paper specifies kernel p,T, not a composition change: retain the local fresh mixture.
    def vector(a):return ' '.join(format(x,'.17g') for x in a)
    changes={'amr.plot_int':-1,'amr.plot_vars':'density rho_E Temp heatRelease','amr.max_level':level,'amr.max_grid_size':box,'amr.checkpoint_files_output':1,
        'amr.plot_per':min(5e-6,stop/4),'prob.p0':1e7,'prob.Tprod':300,'prob.Y':vector(fresh),
        'prob.Yprod':vector(air),'prob.Yseed':vector(fresh),'prob.seed_p':4e7,'prob.seed_T':3000,'prob.seed_u':0,
        'ode.rtol':1e-8,'ode.atol':1e-16,'pelec.sum_interval':1}
    lines=[]
    for line in c['inputs'].splitlines():
        key=line.split('=')[0].strip()
        lines.append(f'{key} = {changes[key]}' if key in changes else line)
    lines += ['prob.netl_startup = 1','prob.exit_p = 1000000','prob.seed_angle = '+str(math.radians(2)),
        'prob.seed_theta = '+str(math.pi/2),'prob.plenum_fuel = 13100000','prob.plenum_oxygen = 12000000',
        'amrex.use_gpu_aware_mpi = 0','amr.check_file = chk','amr.check_int = -1',
        'amr.check_per = '+str(min(1e-5,stop)),'amr.grid_log = gridlog',
        'amr.loadbalance_with_workestimates = 1',
        'amr.n_error_buf = 2 2','tagging.eb_refine_type = adaptive','tagging.min_eb_refine_lev = 0',
        'tagging.max_eb_refine_lev = '+str(level),'tagging.max_vfracerr_lev = 0']
    if level:
        lines += ['amr.regrid_int = 8','amr.ref_ratio = '+' '.join(['2']*level)]
        lines += ['tagging.refinement_indicators = inlet',
            'tagging.inlet.in_box_lo = -3.81 -3.81 0','tagging.inlet.in_box_hi = 3.81 3.81 1.0',
            f'tagging.inlet.max_level = {level}',
            'tagging.pressgrad = 1000000',f'tagging.max_pressgrad_lev = {level}',
            'tagging.tempgrad = 300',f'tagging.max_tempgrad_lev = {level}']
    c.update(inputs='\n'.join(lines)+'\n',solver='PeleC',case_type='netl_startup',max_level=level,
        finest_dx_m=.0762/base_n/(2**level),requested_mesh_um=mesh_um,
        grid_label=f'{base_n}³ base + {level} AMR levels; finest {.0762/base_n/(2**level)*1e6:.1f} µm',
        startup={'source':'https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf',
            'fresh_height_m':.005,'fresh_pressure_Pa':1e6,'exit_pressure_Pa':1e5,'kernel_angle_deg':2,
            'kernel_pressure_Pa':4e6,'kernel_temperature_K':3000,'imposed_tangential_velocity_mps':0,
            'assumptions':['300 K initial gas outside kernel','Dry air O2:N2=1:3.76 beyond fresh layer',
                'Kernel retains fresh stoichiometric composition; paper does not specify a composition replacement',
                'Angular sector ends at 90 degrees; azimuthal placement is an explicit choice',
                'Instantaneous initialization, no subsequent ignition source']},
        limitations=['NETL initial-state prescription in our existing annular geometry, not a full reproduction of Fluent LES.',
            'Reactive Euler; no molecular diffusion, LES, heat loss, resolved plenums/channels or downstream core expansion.',
            'Existing reservoir port approximation and extrapolating outlet retained; not NETL mass-flow/pressure boundary conditions.',
            'FFCMy12 chemistry not established identical to NETL skeletal mechanism.',
            'Native species cleanup enabled: report its conservation effects; no forced propagation or direction.'])
    # Port aperture audit must use the locally refined inlet spacing, not the base mesh.
    nf=base_n*2**level;q=(np.arange(nf)+.5)*7.62/nf-3.81
    xx,yy=np.meshgrid(q,q,indexing='ij');r=np.hypot(xx,yy);th=np.arctan2(yy,xx)
    period=2*np.pi/72;arc=3.56*(th-period*np.floor(th/period+.5));offset=.216*np.tan(np.pi/6)
    area=(7.62/nf)**2*1e-4
    for name,radius,sign in [('fuel',.03935,1),('oxygen',.06225,-1)]:
        mask=(r-3.56+sign*offset)**2*np.cos(np.pi/6)**2+arc**2<radius**2
        exact=72*np.pi*(radius*.01)**2/np.cos(np.pi/6)
        c['apertures'][name]=dict(sampled_area_m2=float(mask.sum()*area),nominal_area_m2=exact,
            relative_area_error=float(mask.sum()*area/exact-1),faces=int(mask.sum()))
    c['aperture_audit_mesh_m']=.0762/nf
    Path(output).write_text(json.dumps(c,indent=2)+'\n');return c
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--mesh-um',type=int,default=200)
    p.add_argument('--stop',type=float,default=2e-4);p.add_argument('--dt',type=float,default=5e-9)
    p.add_argument('--base-n',type=int,default=192);p.add_argument('--max-level',type=int);p.add_argument('--box',type=int,default=64)
    a=p.parse_args();prepare_startup(**vars(a))
