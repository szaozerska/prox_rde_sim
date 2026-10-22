"""Direct native methane thermodynamic round trips before building a CFD case."""
from pathlib import Path
import json
import modal
from modal_controls import image
app=modal.App('prox-rde-3d-methane-thermo-audit',include_source=False)


@app.function(image=image,serialized=True,cpu=(2.,2.),memory=(2048,2048),
              timeout=300,startup_timeout=120,retries=0,max_containers=1)
def audit(cases: list, gri_inverse_bound: int = 3000):
    import hashlib
    import json
    import shlex
    import subprocess
    from pathlib import Path
    root=Path('/opt/PeleC')
    entry=next(e for e in json.loads((root/'build-cpu/compile_commands.json').read_text())
               if '/LiDryer/mechanism.cpp' in e['file'])
    original=shlex.split(entry['command']);flags=[];i=0
    while i<len(original):
        if original[i] in ('-o','-c','-MT','-MF','-MQ'):
            i+=2;continue
        if original[i] not in ('-MD','-MMD'):flags.append(original[i])
        i+=1
    if gri_inverse_bound not in (3000,5000):
        raise ValueError('Only original or explicit diagnostic GRI bound is permitted')
    records=[]
    for case in cases:
        name=case['mechanism']
        if name not in ('drm19','grimech30','FFCM1_Red'):
            raise ValueError('Only the three public preflight candidates are permitted')
        header=root/f'Submodules/PelePhysics/Mechanisms/{name}/mechanism.H'
        original_hash=hashlib.sha256(header.read_bytes()).hexdigest()
        patch=None
        if name=='grimech30' and gri_inverse_bound==5000:
            original_text=header.read_text()
            before='amrex::Real tmax = 3000.0; // min upper bound for thermo def'
            after='amrex::Real tmax = 5000.0; // explicit polynomial-consistency diagnostic; NOT extended data validity'
            if original_text.count(before)!=2:
                raise RuntimeError('Unexpected pinned inverse source; refusing diagnostic patch')
            header=Path('/tmp/gri-thermo-diagnostic.H')
            header.write_text(original_text.replace(before,after))
            patch={'scope':'Only EY/HY inverse upper bound; no rates or thermo coefficients changed',
                   'replacements':2,'before':before,'after':after,
                   'original_header_sha256':original_hash,
                   'thermo_fit_ranges_unchanged':True}
        source=Path('/tmp/thermo.cpp')
        source.write_text('#include "'+str(header)+'"\n'+r'''
#include <iostream>
#include <iomanip>
int main() {
  double T,P,Y[NUM_SPECIES],W[NUM_SPECIES],u,cv,recovered,recovered_u,h,cp,ht,recovered_h;
  int status,hstatus;
  std::cout << std::setprecision(17);
  while(std::cin >> T >> P) {
    for(int k=0;k<NUM_SPECIES;++k) std::cin >> Y[k];
    CKUBMS(T,Y,u); CKCVBS(T,Y,cv);
    recovered=1000.;
    GET_T_GIVEN_EY(u,Y,recovered,status);
    CKUBMS(recovered,Y,recovered_u);
    CKHBMS(T,Y,h); CKCPBS(T,Y,cp); ht=1000.;
    GET_T_GIVEN_HY(h,Y,ht,hstatus); CKHBMS(ht,Y,recovered_h);
    std::cout << u << " " << cv << " " << recovered << " " << recovered_u << " " << status << " " << h << " " << cp << " " << ht << " " << recovered_h << " " << hstatus;
    CKWYP(P,T,Y,W);
    for(int k=0;k<NUM_SPECIES;++k) std::cout << " " << W[k];
    std::cout << "\n";
  }
}
''')
        command=flags+[str(source),'-o','/tmp/thermo']
        built=subprocess.run(command,cwd=entry['directory'],capture_output=True,text=True,timeout=90)
        if built.returncode:
            raise RuntimeError(built.stdout+built.stderr)
        inputs='\n'.join(' '.join(map(str,[s['temperature_K'],s['pressure_Pa']*10,*s['Y']])) for s in case['states'])+'\n'
        output=subprocess.run(['/tmp/thermo'],input=inputs,capture_output=True,text=True,check=True,timeout=15)
        values=[[float(x) for x in line.split()] for line in output.stdout.splitlines()]
        if len(values)!=len(case['states']):raise RuntimeError('Incomplete operator output')
        records.append(dict(case,values_cgs=[v[:10] for v in values],rate_values_mol_cm3_s=[v[10:] for v in values],
                       generated_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
                       compile_command=command,diagnostic_patch=patch,
                       effective_inversion_upper_bound_K=gri_inverse_bound if name=='grimech30' else case['native_inversion_upper_bound_K']))
    return {'scope':'Independent native operator audit, no flow/kinetic integration and no RDE claim',
            'initial_temperature_guess_K':1000.,
            'columns':['u_erg_g','cv_erg_g_K','recovered_temperature_K','recovered_u_erg_g','inversion_status','h_erg_g','cp_erg_g_K','enthalpy_recovered_temperature_K','recovered_h_erg_g','enthalpy_inversion_status'],
            'cases':records}


@app.local_entrypoint()
def main(states: str, output: str, gri_inverse_bound: int = 3000):
    target=Path(output)
    if target.exists():raise FileExistsError('Do not overwrite audit evidence')
    result=audit.remote(json.loads(Path(states).read_text()),gri_inverse_bound)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print('Saved native thermodynamic operator audit to '+str(target))
