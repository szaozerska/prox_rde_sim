"""Check actual native wall-flux geometry, not inferred normals from rendered data."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from rde3d.geometry import Annulus


def analyze(run):
    status=json.loads((run/'result.json').read_text())
    volume=json.loads((run/'geometry_checks.json').read_text())
    ports=json.loads((run/'native_ports.json').read_text())
    data=np.genfromtxt(run/'native_surface.csv',delimiter=',',names=True)
    if len(data)<1 or not np.isfinite(data.tolist()).all():raise ValueError('Missing/nonfinite native surface data')
    geometry=Annulus(**status['geometry_m']);analytic=geometry.measures()
    xyz=np.column_stack([data[n] for n in ('x_cm','y_cm','z_cm')])*.01
    # EB.cpp stores (open high face - open low face)/area: inward to fluid.
    # MOL.cpp uses -p*stored_normal. Convert once to physical outward normals.
    native_normal=np.column_stack([data[n] for n in ('nx','ny','nz')])
    normal=-native_normal;area=data['area_cm2']*1e-4
    indices=np.column_stack([data[n] for n in ('i','j','k')])
    r=np.linalg.norm(xyz[:,:2],axis=1)
    radial=(normal[:,0]*xyz[:,0]+normal[:,1]*xyz[:,1])/r
    outer=r>(geometry.inner_radius+geometry.outer_radius)/2
    inner=~outer
    width=max(volume['dx_m'])
    inner_flat=inner&(xyz[:,2]<geometry.core_length-1.5*width)
    core_flat=inner&(r<geometry.inner_radius-1.5*width)
    if not all(m.any() for m in (outer,inner_flat,core_flat)):raise ValueError('Missing expected boundary subset')
    measured=dict(outerWall_m2=float(area[outer].sum()),
        innerWall_m2=float((-area[inner]*radial[inner]).sum()),
        coreEnd_m2=float((-area[inner]*normal[inner,2]).sum()),
        injector_m2=ports['inlet_cm2']*1e-4,outlet_m2=ports['outlet_cm2']*1e-4)
    errors={name:abs(value/analytic[name]-1) for name,value in measured.items()}
    closure=(normal*area[:,None]).sum(axis=0)+[0,0,measured['outlet_m2']-measured['injector_m2']]
    closure_error=float(np.linalg.norm(closure)/sum(measured.values()))
    gauss_volume=float((np.sum(area*np.sum(normal*xyz,axis=1))+geometry.outlet_z*measured['outlet_m2'])/3)
    gauss_error=abs(gauss_volume/volume['fluid_volume_m3']-1)
    directions=dict(outer_min_radial_projection=float(radial[outer].min()),
        inner_min_inward_projection=float((-radial[inner_flat]).min()),
        core_min_negative_z_projection=float((-normal[core_flat,2]).min()))
    checks=dict(cold_volume_checks_passed=volume['passed'],surface_hook_present=status['surface_diagnostics'],
        exactly_one_owned_record_per_cut_cell=len(data)==volume['cut_cells'] and len(np.unique(indices,axis=0))==len(data),
        indices_in_domain=bool(np.all(indices>=0) and np.all(indices<np.array(status['n_cell']))),
        positive_area_and_cut_fraction=bool(np.all(area>0) and np.all(data['vfrac']>0) and np.all(data['vfrac']<1)),
        unit_normals=float(max(abs(np.linalg.norm(normal,axis=1)-1)))<1e-12,
        correct_wall_orientation=min(directions.values())>.95,
        inward_core_corner_components=bool(np.all(radial[inner]<1e-10) and np.all(normal[inner,2]<1e-10)),
        boundary_areas=max(errors.values())<.01,surface_vector_closure=closure_error<1e-10,
        gauss_volume_consistency=gauss_error<1e-3)
    checks={k:bool(v) for k,v in checks.items()}
    return dict(passed=all(checks.values()),checks=checks,surface_records=len(data),measured=measured,
        normal_convention='Stored PeleC eb_normal points into fluid; physical outward normal = -stored normal (EB.cpp aperture definition and MOL.cpp pressure-flux sign)',
        area_relative_errors=errors,orientation=directions,surface_vector_closure_relative=closure_error,
        gauss_volume_m3=gauss_volume,gauss_volume_relative_difference=gauss_error,
        criteria='Areas <1%; normals unit to 1e-12 and correct sign/projection >.95 away from core corner; vector closure <1e-10; divergence-theorem volume agreement <0.1%',
        scope='Native wall-flux areas/normals and port apertures. Inner-wall/core-end corner contributions use radial/axial projected area. Directional flow, repair budgets, AMR and reactive behavior remain separate.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);args=parser.parse_args()
    report=analyze(args.run);(args.run/'surface_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
