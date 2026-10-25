"""Prepare declared native controls/engine exploratory runs, never fitted wave motion."""
import argparse,json,math
from pathlib import Path
import numpy as np
import cantera as ct
ROOT=Path(__file__).resolve().parents[2]
MECH=ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'
def prepare(output,mode='reactor',n=64,stop=5e-7,dt=5e-9,feed=2,seed=True,reacting=True,height=.0038,order=1,clean_species=False):
    g=ct.Solution(str(MECH));g.TPX=300,377916.97229176015,'CH4:1.176,O2:2';fresh=g.Y.copy()
    g.TP=1500,377916.97229176015;g.equilibrate('TP');products=g.Y.copy();g.TPX=4000,1e7,'CH4:1.176,O2:2';g.equilibrate('TP');seed_Y=g.Y.copy()
    p0=377916.97229176015;T0=300.;Tprod=1500.
    if mode=='reactor':p0=22.984e6;T0=1968.;n=8;feed=0;seed=False
    shape=[n,n,n];lo=[-3.81,-3.81,0.];hi=[3.81,3.81,7.62];boundary='SlipWall SlipWall UserBC'
    if mode=='reactor':lo=[0,0,0];hi=[.1,.1,.1];boundary='SlipWall SlipWall SlipWall'
    if mode=='cold':seed=False;reacting=False;Tprod=300.;products=fresh.copy()
    config=dict(mode=0 if mode=='reactor' else 2,case_type=mode,stop=stop,dt=dt,n=n,feed=feed,seed=seed,reacting=reacting,
        species_cleanup=bool(clean_species),species=g.species_names,mesh_m=[(hi[i]-lo[i])*.01/n for i in range(3)],height_m=height,
        limitations=['Exploratory coarse reactive Euler; no turbulence, molecular diffusion or heat transfer.',
            'No injector plenums/tube or downstream core expansion. Fixed upstream reservoirs; reverse flow blocked.',
            'Finite initialized +theta charge, not simulated spark-to-detonation transition.',
            'Opposed radial-plane jets at 30 degrees meet at 2.16 mm; finite startup momentum is tangential.',
            'Mouths are cell-centre sampled; report numerical aperture areas and flow before quantitative use.'])
    # Startup state is a finite high-pressure equilibrium-product surrogate, not a sustained source.
    inputs=f'''stop_time = {stop}
max_step = 1000000
geometry.is_periodic = 0 0 0
geometry.coord_sys = 0
geometry.prob_lo = {' '.join(map(str,lo))}
geometry.prob_hi = {' '.join(map(str,hi))}
amr.n_cell = {n} {n} {n}
amr.max_level = 0
amr.blocking_factor = 8
amr.max_grid_size = 32
amr.checkpoint_files_output = 0
amr.plot_files_output = 1
amr.plot_file = plt
amr.plot_int = 1000000
amr.plot_per = {stop/20}
amr.plot_vars = density rho_E Temp
amr.derive_plot_vars = pressure x_velocity y_velocity z_velocity
pelec.plot_massfrac = 1
pelec.plot_rhoy = 0
amr.data_log = datlog
pelec.lo_bc = {boundary}
pelec.hi_bc = {'SlipWall SlipWall SlipWall' if mode in ('reactor','cold') else 'SlipWall SlipWall FOExtrap'}
pelec.do_react = {int(reacting)}
pelec.do_hydro = {int(mode!='reactor')}
pelec.do_mol = 1
pelec.mol_iters = 1
pelec.mol_iorder = {order}
pelec.plm_iorder = {order}
pelec.diffuse_temp = 0
pelec.diffuse_enth = 0
pelec.diffuse_spec = 0
pelec.diffuse_vel = 0
pelec.chem_integrator = ReactorCvode
pelec.fixed_dt = {dt}
pelec.init_shrink = 1
pelec.cfl = 0.3
pelec.dt_cutoff = 1e-20
pelec.eb_clean_massfrac = {int(clean_species)}
pelec.eb_isothermal = 0
pelec.eb_noslip = 0
pelec.redistribution_type = StateRedist
pelec.eb_srd_max_order = 0
pelec.sum_interval = 1
pelec.v = 1
amr.v = 1
prob.mode = {config['mode']}
prob.feed = {feed}
prob.seed = {int(seed)}
prob.p0 = {p0*10}
prob.T0 = {T0}
prob.Tprod = {Tprod}
prob.height = {height*100}
prob.Y = {' '.join(format(x,'.17g') for x in fresh)}
prob.Yprod = {' '.join(format(x,'.17g') for x in products)}
prob.Yseed = {' '.join(format(x,'.17g') for x in seed_Y)}
prob.seed_p = 100000000
prob.seed_T = 4000
prob.seed_u = 190000
amrex.abort_on_unused_inputs = 1
amrex.signal_handling = 0
'''
    if reacting:inputs+='cvode.solve_type = GMRES\ncvode.max_order = 5\node.rtol = 1e-10\node.atol = 1e-18\n'
    if mode!='reactor':inputs+='eb2.geom_type = parser\neb2.parser_function = max(sqrt(x*x+y*y)-3.81,3.31-sqrt(x*x+y*y))\n'
    config['inputs']=inputs
    # Independent geometric audit of sampled mouth area; never silently renormalize it.
    if mode!='reactor':
        q=(np.arange(n)+.5)*7.62/n-3.81;xx,yy=np.meshgrid(q,q,indexing='ij');r=np.hypot(xx,yy);th=np.arctan2(yy,xx);period=2*np.pi/72
        arc=3.56*(th-period*np.floor(th/period+.5));offset=.216*np.tan(np.pi/6);area=(7.62/n)**2*1e-4
        config['apertures']={}
        for name,radius,sign in [('fuel',.03935,1),('oxygen',.06225,-1)]:
            mask=(r-3.56+sign*offset)**2*np.cos(np.pi/6)**2+arc**2<radius**2;exact=72*np.pi*(radius*.01)**2/np.cos(np.pi/6)
            config['apertures'][name]=dict(sampled_area_m2=float(mask.sum()*area),nominal_area_m2=exact,relative_area_error=float(mask.sum()*area/exact-1),faces=int(mask.sum()))
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError(target)
    target.write_text(json.dumps(config,indent=2)+'\n')
    return config
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--mode',choices=['reactor','cold','annulus'],default='reactor');p.add_argument('--n',type=int,default=128);p.add_argument('--stop',type=float,default=5e-7);p.add_argument('--dt',type=float,default=5e-9);p.add_argument('--height',type=float,default=.0038);p.add_argument('--feed',type=int,default=2);p.add_argument('--order',type=int,default=1);p.add_argument('--clean-species',action='store_true');a=p.parse_args();prepare(**vars(a))
