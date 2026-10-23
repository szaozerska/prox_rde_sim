"""Read native fields for a short formed-wave control; never certify an engine."""
import argparse,json
from pathlib import Path
import numpy as np
import cantera as ct
from analyze_sod import load_fields
from validation import native_log_errors

def crossing(x,values,threshold):
    hits=np.flatnonzero((values[:-1]>=threshold)&(values[1:]<threshold))
    if not len(hits):return None
    i=int(hits[-1]);return float(x[i]+(threshold-values[i])/(values[i+1]-values[i])*(x[i+1]-x[i]))

def analyze(run,reference):
    case=json.loads((run/'case.json').read_text());result=json.loads((run/'result.json').read_text())
    ref=json.loads((reference/'reference.json').read_text());cj=ref['CJ'];znd=np.load(reference/'znd.npz')
    gas=ct.Solution(str(reference/'native_constants.yaml'));gas.TPY=300.,cj['pressure_Pa'],cj['initial']['Y']
    elements0=np.array([gas.elemental_mass_fraction(e) for e in gas.element_names])
    gas.TP=298.15,ct.one_atm;hf=gas.standard_enthalpies_RT*ct.gas_constant*gas.T/gas.molecular_weights
    element_matrix=np.array([[gas.n_atoms(s,e)*gas.atomic_weight(e)/gas.molecular_weights[s] for e in range(gas.n_elements)] for s in range(gas.n_species)])
    initial=np.load(reference/f"initial_n{case['nx']}.npz")['conserved_SI']
    names=('density','Temp','pressure','rho_E','x_velocity','y_velocity','z_velocity')+tuple('Y('+s+')' for s in gas.species_names)
    rows=[];checks={};profiles=[];maxima=dict(species_sum=0.,negative_species=0.,element_error=0.,integrated_element_ratio_error=0.,pressure_EOS=0.,energy_EOS=0.,transverse_mps=0.,transverse_nonuniformity=0.)
    initial_error=None;maxchar=0.
    for plot in sorted(run.glob('plt[0-9]*')):
        t,fields,dx,lo=load_fields(plot,names)
        if fields['density'].shape!=(case['nx'],8,8) or not np.allclose(dx,case['dx_m']*100,rtol=1e-12,atol=0):raise ValueError('Unexpected native grid')
        if not all(np.isfinite(v).all() for v in fields.values()):raise ValueError('Nonfinite native fields')
        for name,values in fields.items():
            scale=max(float(np.max(abs(values))),1e-10 if name.startswith('Y(') else 1e-30)
            maxima['transverse_nonuniformity']=max(maxima['transverse_nonuniformity'],float(np.max(np.ptp(values,axis=(1,2))))/scale)
        maxima['transverse_mps']=max(maxima['transverse_mps'],max(float(np.max(abs(fields[k])))/100 for k in ('y_velocity','z_velocity')))
        data={k:v.mean(axis=(1,2)) for k,v in fields.items()}
        rho=data['density']*1000;pressure=data['pressure']/10;energy=data['rho_E']/10;u=data['x_velocity']/100;T=data['Temp']
        Y=np.array([data['Y('+s+')'] for s in gas.species_names]).T
        maxima['species_sum']=max(maxima['species_sum'],float(np.max(abs(Y.sum(axis=1)-1))))
        maxima['negative_species']=max(maxima['negative_species'],float(max(0,-Y.min())))
        if min(rho.min(),pressure.min())<=0 or T.min()<299. or T.max()>5000:raise ValueError('Outside positive declared thermodynamic envelope')
        maxima['integrated_element_ratio_error']=max(maxima['integrated_element_ratio_error'],float(np.max(abs(np.average(Y@element_matrix,weights=rho,axis=0)-elements0))))
        for r,p,temp,y,e,v in zip(rho,pressure,T,Y,energy/rho,u):
            gas.TDY=temp,r,y
            maxima['element_error']=max(maxima['element_error'],float(np.max(abs(np.array([gas.elemental_mass_fraction(el) for el in gas.element_names])-elements0))))
            maxima['pressure_EOS']=max(maxima['pressure_EOS'],abs(gas.P/p-1))
            maxima['energy_EOS']=max(maxima['energy_EOS'],abs(gas.int_energy_mass+.5*v*v-e)/max(abs(e),gas.cv_mass*temp))
            maxchar=max(maxchar,abs(v)+gas.sound_speed)
        x=(np.arange(case['nx'])+.5)*case['dx_m']
        q=(np.dot(cj['initial']['Y'],hf)-Y@hf)/cj['q_equilibrium_Jkg']
        positions=[crossing(x,pressure,cj['pressure_Pa']+f*(cj['VN']['p']-cj['pressure_Pa'])) for f in (.25,.5,.75)]
        half=crossing(x,q,.5)
        row=dict(time_s=t,shock_locations_m=positions,half_heat_location_m=half,
            half_heat_distance_m=None if half is None or positions[1] is None else positions[1]-half,
            temperature_minmax_K=[float(T.min()),float(T.max())],mass_per_area_kg_m2=float(rho.sum()*case['dx_m']),
            total_energy_per_area_J_m2=float(energy.sum()*case['dx_m']))
        rows.append(row);profiles.append(dict(x_m=x,pressure_Pa=pressure,temperature_K=T,density_kg_m3=rho,velocity_mps=u,heat_fraction=q,species_Y=Y))
        if t==0:
            actual=np.column_stack([rho,rho*u,energy,rho[:,None]*Y]);scale=np.maximum(np.max(abs(initial),axis=0),1e-20)
            initial_error=float(np.max(np.mean(abs(actual-initial),axis=0)/scale))
    if len(rows)<2:raise ValueError('Need native initial and final fields')
    final_time=rows[-1]['time_s']
    checks.update(completion=result['completion_passed'],solver_log=not native_log_errors((run/'solver.log').read_text()),
        final_time=abs(final_time-result['target_time'])<1e-15,initial_cell_averages=initial_error is not None and initial_error<1e-10,
        species_sum=maxima['species_sum']<1e-10,species_nonnegative=maxima['negative_species']<1e-12,
        elements=maxima['element_error']<1e-8,EOS_pressure=maxima['pressure_EOS']<1e-7,EOS_energy=maxima['energy_EOS']<1e-6,
        transverse_motion=maxima['transverse_mps']<1e-8,transverse_invariance=maxima['transverse_nonuniformity']<1e-9,
        wave_inside_domain=all(r['shock_locations_m'][1] is not None for r in rows))
    # Conservative initial/final characteristic bound; no incoming boundary should
    # reach the moving wave/reaction window over this short interval.
    margin=case['shock_initial_m']-(maxchar-cj['CJ_speed_mps'])*final_time-2e-4
    checks['boundary_cone_margin']=margin>0
    propagation={};long_enough=final_time>=1.99e-7
    if long_enough and checks['wave_inside_domain']:
        late=[r for r in rows if r['time_s']>=.5*final_time]
        speeds=[float(np.polyfit([r['time_s'] for r in late],[r['shock_locations_m'][j] for r in late],1)[0]) if all(r['shock_locations_m'][j] is not None for r in late) else None for j in range(3)]
        distances=[r['half_heat_distance_m'] for r in late]
        expected=ref['ZND']['heat_fraction_lengths_m']['0.5']
        checks['reacting_enabled']=result.get('reacting',True)
        propagation=dict(speed_mps_by_threshold=speeds,reference_speed_mps=cj['CJ_speed_mps'],
            half_heat_distances_m=distances,reference_half_heat_m=expected,
            induction_times_elapsed=final_time/ref['ZND']['induction_time_max_dTdt_s'])
        checks['short_wave_speed']=all(v is not None and abs(v/cj['CJ_speed_mps']-1)<.05 for v in speeds)
        checks['shock_reaction_coupling']=all(v is not None and 0<v<2*expected for v in distances)
    else:checks['propagation_window_complete']=False
    checks={key:bool(value) for key,value in checks.items()}
    diagnostic_pass=all(v for k,v in checks.items() if k!='propagation_window_complete')
    report=dict(numerical_field_checks_passed=diagnostic_pass,short_propagation_checks_passed=all(checks.values()),
        full_G2b_passed=False,checks=checks,max_errors=maxima,initial_cell_average_relative_L1_error=initial_error,
        boundary_cone_margin_m=margin,max_observed_characteristic_mps=maxchar,history=rows,propagation=propagation,
        wall_seconds=result['wall_seconds'],scope='Short formed-wave diagnostic only; grid/timestep and longer-window checks still required; no engine sustainability claim')
    (run/'wave_checks.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    np.savez_compressed(run/'wave_profiles.npz',time_s=[r['time_s'] for r in rows],**{k:np.array([d[k] for d in profiles]) for k in profiles[0]})
    print(json.dumps({k:v for k,v in report.items() if k!='history'},indent=2))
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('reference',type=Path);a=p.parse_args()
    report=analyze(a.run,a.reference);raise SystemExit(0 if report['numerical_field_checks_passed'] else 1)
