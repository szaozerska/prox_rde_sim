"""Retain compact auditable evidence; large native fields stay in ignored runs3d."""
import sys,json,base64,hashlib,tarfile,io,gzip,shutil
from pathlib import Path
import numpy as np

def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def windows(report):
    rows=report['history'];end=rows[-1]['time_s'];bounds=[(0,.2e-6),(.2e-6,.5e-6),(.5e-6,1e-6),(1e-6,2e-6)] if end>1e-6 else [(0,end/2),(end/2,end)]
    out=[]
    for lo,hi in bounds:
        r=[r for r in rows if lo-1e-15<=r['time_s']<=hi+1e-15]
        if len(r)<3:continue
        speeds=[float(np.polyfit([v['time_s'] for v in r],[v['shock_locations_m'][j] for v in r],1)[0]) if all(v['shock_locations_m'][j] is not None for v in r) else None for j in range(3)]
        out.append(dict(start_s=lo,end_s=hi,samples=len(r),speed_mps=speeds))
    return out

def main(source,dest):
    source=Path(source);dest=Path(dest);dest.mkdir(parents=True,exist_ok=True);index=[]
    for backend in ('gpu','cpu'):
      for phase in ('','_planar','_flux','_flux_tight'):
        manifest=source/(backend+phase+'_manifest.json')
        if not manifest.exists():continue
        spec=json.loads(manifest.read_text());results=Path(spec['output'])
        for item in spec['cases']:
            name=backend+'_'+item['name'];out=dest/name;src=results/(item['name']+'.json');err=results/(item['name']+'.error.json')
            row=dict(name=name,backend=backend,status='pending',limit_s=item['limit'],raw_result=str(src))
            if err.exists():row.update(status='remote_error',error=json.loads(err.read_text()));index.append(row);continue
            if not src.exists():index.append(row);continue
            try:r=json.loads(src.read_text())
            except json.JSONDecodeError:index.append(row);continue
            out.mkdir(exist_ok=True);run=r.get('run',r.get('manifest'));save(out/'execution.json',run)
            raw=base64.b64decode(r['artifact_tar_gz_base64'],validate=True)
            if hashlib.sha256(raw).hexdigest()!=r['artifact_sha256']:raise ValueError('Checksum mismatch: '+name)
            save(out/'provenance.json',dict(artifact_sha256=r['artifact_sha256'],raw_result=str(src),input=item))
            # Retain original native logs, configuration, and build provenance without field duplication.
            marker=out/'archive_verified.json'
            cached=(marker.exists() and json.loads(marker.read_text())['artifact_sha256']==r['artifact_sha256'])
            if not cached:
                with tarfile.open(fileobj=io.BytesIO(raw),mode='r|gz') as archive:
                    for entry in archive:
                        if not entry.isfile():continue
                        if entry.name in ('case/solver.log','case/case.json','case/init_annulus.json','case/wave_case.json','case/reference.json','build/manifest.json','build/flux_patch.json','case/system/fvSchemes','case/system/controlDict') or entry.name.startswith('case/log.') and ('mpirun' in entry.name or 'detonationFoam' in entry.name):
                            data=archive.extractfile(entry).read();fname=entry.name.replace('/','_')
                            if fname.endswith('.log') or fname.startswith(('case_log.','case_system_')):(out/(fname+'.gz')).write_bytes(gzip.compress(data,mtime=0))
                            else:(out/fname).write_bytes(data)
                save(marker,dict(artifact_sha256=r['artifact_sha256']))
            checks=r.get('checks');native=results/(item['name']+'_native')/'case'
            row['status']='completed_execution' if (run.get('completed') if backend=='gpu' else all(v['returncode']==0 for v in run['commands'])) else 'incomplete_execution'
            row['wall_seconds']=run['wall_seconds'];row['time_scope']='solver only' if backend=='gpu' else 'mesh, solver, reconstruction, analysis'
            if checks is not None:
                save(out/'checks.json',checks);last=checks['rows'][-1]
                row.update(actual_time_s=last['time_s'],failed_checks=[k for k,v in checks['checks'].items() if not v],final_min_species=last['min_species'],max_saved_species_sum_error=max(v['species_sum_error'] for v in checks['rows']))
                if backend=='gpu':row.update(worst_logged_species=checks['every_step_history'].get('extrema',{}).get('massfrac',[None])[0],mass_relative_change=last['mass_kg']/checks['rows'][0]['mass_kg']-1)
                else:row['clipping']=checks['clipping']
            elif (native/'wave_checks.json').exists():
                checks=json.loads((native/'wave_checks.json').read_text());checks['window_fits']=windows(checks);save(out/'wave_checks.json',checks)
                row.update(failed_checks=[k for k,v in checks['checks'].items() if not v],actual_time_s=checks['history'][-1]['time_s'],window_fits=checks['window_fits'])
                shutil.copyfile(native/'wave_profiles.npz',out/'wave_profiles.npz')
                if (native/'element_conventions.json').exists():shutil.copyfile(native/'element_conventions.json',out/'element_conventions.json')
            elif (native/'contact_checks.json').exists():
                checks=json.loads((native/'contact_checks.json').read_text());save(out/'contact_checks.json',checks);row.update(actual_time_s=checks['rows'][-1]['time_s'],max_pressure_relative_error=max(v['pressure_relative_error'] for v in checks['rows']),max_velocity_error_mps=max(v['velocity_error_mps'] for v in checks['rows']))
            else:row['analysis']='No final field analysis: native execution stopped before reconstruction; see retained solver log.' if row['status']=='incomplete_execution' else 'pending or failed; see local analysis log'
            index.append(row)
    save(dest/'index.json',index)
    print(json.dumps([dict(name=r['name'],status=r['status'],failed=r.get('failed_checks'),analysis=r.get('analysis')) for r in index],indent=2))
if __name__=='__main__':main(*sys.argv[1:])
