"""Direct native chemistry operator probe for a failed reactor comparison."""
import modal
from modal_controls import image
app=modal.App('prox-rde-3d-native-rate-probe',include_source=False)


@app.function(image=image,serialized=True,cpu=(2.,2.),memory=(2048,2048),
              timeout=120,startup_timeout=120,retries=0,max_containers=1)
def rates():
    import json
    import shlex
    import subprocess
    from pathlib import Path
    root=Path('/opt/PeleC')
    entries=json.loads((root/'build-cpu/compile_commands.json').read_text())
    entry=next(e for e in entries if '/LiDryer/mechanism.cpp' in e['file'])
    args=shlex.split(entry['command']);flags=[];i=0
    while i<len(args):
        if args[i] in ('-o','-c','-MT','-MF','-MQ'):
            i+=2;continue
        if args[i] not in ('-MD','-MMD'):flags.append(args[i])
        i+=1
    source=Path('/tmp/rates.cpp')
    source.write_text(r'''
#include "mechanism.H"
#include <iostream>
#include <iomanip>
int main() {
  double p,T,Y[NUM_SPECIES],W[NUM_SPECIES],u,cv,rho;
  std::cout << std::setprecision(17);
  while (std::cin >> p >> T) {
    for(int k=0;k<NUM_SPECIES;++k) std::cin >> Y[k];
    CKWYP(p,T,Y,W); CKUBMS(T,Y,u); CKCVBS(T,Y,cv); CKRHOY(p,T,Y,rho);
    std::cout << rho << " " << u << " " << cv;
    for(int k=0;k<NUM_SPECIES;++k) std::cout << " " << W[k];
    std::cout << "\n";
  }
}
''')
    flags += [str(source),'-o','/tmp/rates']
    compiled=subprocess.run(flags,cwd=entry['directory'],capture_output=True,text=True,timeout=90)
    if compiled.returncode:
        return json.dumps({'status':'compile_failed','command':flags,'log':compiled.stdout+compiled.stderr})
    # Public upstream reference states; no engine data is required for this diagnostic.
    inputs=[]
    for T in (300.,1001.,1200.,2000.,3000.):
        for p in (1013250.,3000000.):
            for y in ([.06,.5,0.,0.,0.,0.,0.,0.,.44],
                      [.04,.25,.3,.002,.002,.006,.001,.001,.398]):
                inputs.append([p,T,*y])
    completed=subprocess.run(['/tmp/rates'],input='\n'.join(' '.join(map(str,row)) for row in inputs)+'\n',
                             capture_output=True,text=True,check=True,timeout=10)
    values=[[float(x) for x in row.split()] for row in completed.stdout.splitlines()]
    return json.dumps({'status':'rates_evaluated','inputs_cgs':inputs,'values_cgs':values,
                       'columns':['density','internal_energy','cv']+['wdot_'+str(i) for i in range(9)],
                       'compile_command':flags,'scope':'Direct CPU mechanism thermodynamics/production rates; independent of CFD/CVODE'})
