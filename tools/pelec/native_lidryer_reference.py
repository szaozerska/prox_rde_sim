"""Independent Cantera representation of the pinned generated LiDryer constants.

This does not replace the nominal YAML reference or alter the native solver.
It isolates a measured code-generation convention from integration error.
"""
import hashlib
import json
import re
from pathlib import Path
import cantera as ct


def make_reference(mechanism: Path):
    nominal=ct.Solution(str(mechanism))
    if nominal.species_names != ['H2','O2','H2O','H','O','OH','HO2','H2O2','N2']:
        raise ValueError('Diagnostic is restricted to the pinned LiDryer species set')
    header=mechanism.with_suffix('.H').read_text()
    rc_native=float(re.search(r'ruc\s*=\s*([0-9.eE+-]+)',header)[1])
    r_ref_native=float(re.search(r'refC\s*=\s*101325\s*/\s*([0-9.eE+-]+)',header)[1])
    rc_cantera=ct.gas_constant/4184.0  # thermochemical cal/(mol K)
    activation_factor=rc_cantera/rc_native
    pressure_factor=(ct.gas_constant/1000.0)/r_ref_native
    species=nominal.species()
    for specie in species:
        thermo=specie.thermo
        if not isinstance(thermo,ct.NasaPoly2):
            raise ValueError('This diagnostic is limited to the pinned NASA7 LiDryer mechanism')
        specie.thermo=ct.NasaPoly2(thermo.min_temp,thermo.max_temp,
                                thermo.reference_pressure*pressure_factor,thermo.coeffs)
    gas=ct.Solution(thermo='ideal-gas',kinetics='gas',species=species,reactions=nominal.reactions())
    for index,reaction in enumerate(gas.reactions()):
        data=json.loads(json.dumps(reaction.input_data))
        if reaction.rate.type not in ('Arrhenius','falloff'):
            raise ValueError(f'Unsupported diagnostic rate type: {reaction.rate.type}')
        for key in ('rate-constant','low-P-rate-constant','high-P-rate-constant'):
            if key in data:
                data[key]['Ea']*=activation_factor
        gas.modify_reaction(index,ct.Reaction.from_dict(data,gas))
    return gas,{'kind':'native_generated_constants',
                'mechanism_sha256':hashlib.sha256(mechanism.read_bytes()).hexdigest(),
                'generated_header_sha256':hashlib.sha256(header.encode()).hexdigest(),'native_Rcal':rc_native,
                'cantera_Rcal':rc_cantera,'native_reference_R_SI':r_ref_native,
                'activation_energy_factor':activation_factor,
                'species_reference_pressure_factor':pressure_factor,
                'scope':'Source-derived constant conventions, not fitted to reactor data. Direct hot-state rates verified separately; nominal YAML comparisons remain separate. Low-temperature coefficient-rounding residual remains.'}
