"""Independent volume, topology and cold-equilibrium checks of native EB fields."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from scipy.ndimage import label
from validation import native_log_errors
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rde3d.geometry import Annulus


def load(plot):
    import yt
    yt.set_log_level(40)
    ds=yt.load(str(plot))
    if ds.index.max_level!=0:raise ValueError('Uniform cold geometry control required')
    grid=ds.covering_grid(0,ds.domain_left_edge,ds.domain_dimensions)
    names=['vfrac','density','rho_E','Temp','rho_AIR','pressure','x_velocity','y_velocity','z_velocity']
    fields={n:np.asarray(grid['boxlib',n]) for n in names}
    return float(ds.current_time),fields,np.asarray(ds.domain_left_edge),np.asarray(ds.domain_width)/ds.domain_dimensions


def analyze(run):
    status=json.loads((run/'result.json').read_text());geometry=Annulus(**status['geometry_m'])
    plots=sorted(run.glob('plt[0-9]*'))
    if len(plots)<2:raise ValueError('Initial and final geometry fields required')
    t0,initial,lo,dx=load(plots[0]);t1,final,lo1,dx1=load(plots[-1])
    if initial['vfrac'].shape!=tuple(status['n_cell']):raise ValueError('Native grid does not match declaration')
    if not np.array_equal(lo,lo1) or not np.array_equal(dx,dx1):raise ValueError('Mesh changed')
    if not np.allclose(dx,dx[0],rtol=0,atol=1e-14):raise ValueError('This EB control requires isotropic cells')
    if not all(np.isfinite(v).all() for data in (initial,final) for v in data.values()):raise ValueError('Nonfinite native fields')
    vf=initial['vfrac'];fluid=vf>0
    if not fluid.any():raise ValueError('No fluid cells')
    cell_cm3=float(np.prod(dx));volume=float(vf.sum()*cell_cm3*1e-6)
    analytic=geometry.measures();volume_error=abs(volume/analytic['volume_m3']-1)
    coords=[lo[i]+(np.arange(vf.shape[i])+.5)*dx[i] for i in range(3)]
    r=np.sqrt(coords[0][:,None,None]**2+coords[1][None,:,None]**2)
    z=coords[2][None,None,:]
    implicit=np.maximum(r-geometry.outer_radius*100,
        np.minimum(geometry.inner_radius*100-r,geometry.core_length*100-z))
    margin=float(np.linalg.norm(dx)/2+1e-12)
    interior=implicit < -margin;solid=implicit > margin
    components=label(fluid)[1]
    slice_area=vf.sum(axis=(0,1))*dx[0]*dx[1]*1e-4
    below=np.clip((geometry.core_length*100-(coords[2]-.5*dx[2]))/dx[2],0,1)
    expected_area=(analytic['injector_m2']*below+analytic['outlet_m2']*(1-below))
    slice_errors=abs(slice_area/expected_area-1)
    area_error=float(max(slice_errors))
    worst_slice=int(np.argmax(slice_errors))
    straight=(below==0)|(below==1)
    integrated_slice_error=float(np.sum(abs(slice_area-expected_area))*dx[2]*.01/analytic['volume_m3'])
    def integral(data,field):return float((data[field]*vf).sum()*cell_cm3)
    budgets={name:abs(integral(final,field)/integral(initial,field)-1)
             for name,field in [('mass','density'),('energy','rho_E'),('species','rho_AIR')]}
    equilibrium={n:float(np.max(abs(final[n][fluid]/initial[n][fluid]-1)))
                 for n in ('density','Temp','pressure','rho_E')}
    speed=max(float(np.max(abs(final[n][fluid])))*.01 for n in ('x_velocity','y_velocity','z_velocity'))
    species_error=float(np.max(abs(final['rho_AIR'][fluid]/final['density'][fluid]-1)))
    kinetic=.5*final['density']*sum(final[n]**2 for n in ('x_velocity','y_velocity','z_velocity'))
    eos_error=float(np.max(abs(.4*(final['rho_E'][fluid]-kinetic[fluid])/final['pressure'][fluid]-1)))
    history=np.genfromtxt(run/'datlog',names=True)
    if len(history)<2 or not np.isfinite(history.tolist()).all():raise ValueError('Incomplete/nonfinite cold history')
    checks=dict(completed=status['completion_passed'],no_solver_errors=not native_log_errors((run/'solver.log').read_text()),
        endpoint_times=abs(t0)<1e-14 and abs(t1-status['target_time'])<1e-14,
        vfrac_bounded=bool(vf.min()>=0 and vf.max()<=1),vfrac_unchanged=np.array_equal(vf,final['vfrac']),
        cut_cells_present=bool(np.any((vf>0)&(vf<1))),one_connected_fluid_region=components==1,
        interior_sign_correct=bool(np.all(abs(vf[interior]-1)<1e-12)),solid_sign_correct=bool(np.all(vf[solid]==0)),
        volume=volume_error<.01,volume_derived_slice_areas=area_error<.01,
        finite_positive_fluid_state=all(bool(np.all(final[n][fluid]>0)) for n in ('density','Temp','pressure')),
        equilibrium=max(equilibrium.values())<1e-9,stationary=speed<1e-8,
        budgets=max(budgets.values())<1e-10,species_sum=species_error<1e-11,gamma_law_eos=eos_error<1e-9,
        all_step_mass_budget=float(max(abs(history['mass']/history['mass'][0]-1)))<1e-10,
        all_step_energy_budget=float(max(abs(history['rho_E']/history['rho_E'][0]-1)))<1e-10)
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(passed=all(checks.values()),checks=checks,n_cell=status['n_cell'],dx_m=(dx*.01).tolist(),
        fluid_volume_m3=volume,analytic_volume_m3=analytic['volume_m3'],volume_relative_error=volume_error,
        max_volume_derived_slice_area_relative_error=area_error,fluid_components=int(components),
        worst_slice_z_m=float(coords[2][worst_slice]*.01),
        worst_slice_core_height_fraction=float(below[worst_slice]),
        straight_section_slice_area_relative_error=float(max(slice_errors[straight])),
        integrated_slice_area_L1_relative_error=integrated_slice_error,
        cut_cells=int(np.sum((vf>0)&(vf<1))),minimum_positive_vfrac=float(vf[fluid].min()),
        relative_budgets=budgets,equilibrium_relative_errors=equilibrium,max_velocity_m_s=speed,
        species_sum_error=species_error,gamma_law_eos_error=eos_error,wall_seconds=status['wall_seconds'],
        scope='Native geometry volumes/topology and closed GammaLaw equilibrium only. Surface normals/areas, directional fluxes, repair budgets, AMR and engine physics are not certified.')
    return result,coords,vf


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);parser.add_argument('--plot',type=Path)
    args=parser.parse_args();report,coords,vf=analyze(args.run)
    (args.run/'geometry_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
        middle=len(coords[1])//2
        axes[0].pcolormesh(coords[2]*10,coords[0]*10,vf[:,middle,:],shading='nearest',vmin=0,vmax=1,cmap='Blues')
        axes[0].set(title=f'Native fluid fraction, y={coords[1][middle]*10:.2f} mm',xlabel='Axial z (mm)',ylabel='x (mm)')
        for ax,z in zip(axes[1:],(3.8,11.4)):
            k=int(np.argmin(abs(coords[2]-z)))
            im=ax.pcolormesh(coords[0]*10,coords[1]*10,vf[:,:,k].T,shading='nearest',vmin=0,vmax=1,cmap='Blues')
            ax.set(title=f'z={coords[2][k]*10:.2f} mm',xlabel='x (mm)',ylabel='y (mm)',aspect='equal')
        fig.colorbar(im,ax=axes[1:],label='Fluid volume fraction')
        fig.suptitle('Native full annulus and core-end expansion — cold geometry control')
        fig.savefig(args.plot,dpi=160)
    print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':main()
