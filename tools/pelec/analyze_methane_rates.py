"""Direct GRI source-rate check, independent of native CFD/CVODE integration."""
import argparse
import json
from pathlib import Path
import cantera as ct
import numpy as np
from native_generated_reference import make_reference


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path);parser.add_argument('mechanism',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    evidence=json.loads(args.evidence.read_text())
    case=next(c for c in evidence['cases'] if c['mechanism']=='grimech30')
    gas,metadata=make_reference(args.mechanism);nominal=ct.Solution(str(args.mechanism))
    if gas.species_names!=case['species']:raise ValueError('Species order mismatch')
    if not case['states'] or len(case['states'])!=len(case['rate_values_mol_cm3_s']):
        raise ValueError('Incomplete native rate records')
    original_hash=(case.get('diagnostic_patch') or {}).get('original_header_sha256',case['generated_header_sha256'])
    if original_hash!=metadata['generated_header_sha256']:
        raise ValueError('Native probe and independent reference source hashes differ')
    rows=[]
    for state,native in zip(case['states'],case['rate_values_mol_cm3_s']):
        if len(native)!=gas.n_species or not np.isfinite(native).all():raise ValueError('Invalid native rates')
        native=np.asarray(native)*1000. # mol/cm3/s -> kmol/m3/s
        row=dict(temperature_K=state['temperature_K'],pressure_Pa=state['pressure_Pa'],condition=state['condition'])
        for label,phase in [('nominal',nominal),('source_derived',gas)]:
            phase.TPY=state['temperature_K'],state['pressure_Pa'],state['Y']
            gross=np.maximum(abs(phase.creation_rates),abs(phase.destruction_rates))
            scale=np.maximum(gross,max(float(max(gross))*1e-12,1e-30))
            errors=abs(native-phase.net_production_rates)/scale
            row[label+'_max_normalized_rate_error']=float(max(errors))
            row[label+'_worst_species']=gas.species_names[int(np.argmax(errors))]
        rows.append(row)
    # Error is normalized by gross rates to avoid division by near-zero equilibrium net source.
    passed=max(r['source_derived_max_normalized_rate_error'] for r in rows)<1e-7
    report=dict(passed=passed,reference=metadata,rows=rows,
        criteria='All sampled species: absolute net-source difference / max(gross species rate, 1e-12 maximum gross rate, 1e-30 kmol/m3/s) <1e-7',
        scope='Direct pinned GRI CPU source rates only; no reactor, GPU, or physical mechanism validation')
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    raise SystemExit(0 if passed else 1)


if __name__=='__main__':main()
