"""Separate cross-package molecular-weight differences from transport error."""
import json,re,sys
from pathlib import Path
import numpy as np
import cantera as ct
ROOT=Path(__file__).resolve().parents[2]
def audit(path):
    path=Path(path);gas=ct.Solution(str(ROOT/'rde3d/mechanisms/FFCMy12/mechanism.yaml'));text=(path/'constant/foam/thermo.foam').read_text()
    weights=np.array([float(re.search(r'(?m)^'+s+r'\s*\{\s*specie\s*\{\s*molWeight\s+(\S+);',text).group(1)) for s in gas.species_names])
    atoms=np.array([[gas.n_atoms(s,e) for e in gas.element_names] for s in gas.species_names]);atomic=np.linalg.lstsq(atoms,weights,rcond=None)[0]
    residual=float(np.max(abs(atoms@atomic-weights)))
    if residual>1e-9:raise ValueError('Native species weights do not share consistent element weights')
    matrix=atoms*atomic[None,:]/weights[:,None];data=np.load(path/'wave_profiles.npz');element=data['species_Y']@matrix;lo=element[0].min(axis=0);hi=element[0].max(axis=0)
    report=dict(native_atomic_weights=dict(zip(gas.element_names,atomic.tolist())),native_molecular_weights=weights.tolist(),cantera_molecular_weights=gas.molecular_weights.tolist(),maximum_relative_molecular_weight_difference=float(np.max(abs(weights/gas.molecular_weights-1))),native_weight_consistency_residual=residual,initial_native_element_span=(hi-lo).tolist(),max_excursion_outside_initial_native_element_ranges=float(max(0,np.maximum(element-hi,lo-element).max())),scope='Diagnostic only. Original common-reference element check is retained. Differing molecular-weight conventions create a small elemental-composition gradient in the initialized cross-package ZND profile; no conservation pass inferred from this audit.')
    (path/'element_conventions.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2))
