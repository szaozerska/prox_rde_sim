# Short planar formed-wave numerical control

This case only imports independently calculated **conserved cell averages**.
PeleC supplies all fluxes, equation-of-state evaluation, time integration and
chemistry. There is no ongoing ignition or custom reaction/heat source. The
3D grid is uniform in two transverse periodic directions; it is a planar control,
not a rotating annular simulation. Only a uniform, zero-origin, non-AMR x grid is
supported by this initializer.

The reference is the existing checked SDToolbox/Cantera GRI law with source-derived
PelePhysics constant conventions. It retains the explicitly audited inverse
interval and the previously documented physical fit limitations. Reference cleanup
is limited to measured floating-point species residue; native species are not
clipped by this case. The imported table contains cgs density, momentum, total
energy density, and species densities; temperature is recovered by native EOS.

The pinned `Diffusion.cpp` passes `plm_iorder` to the MOL flux function, although
`mol_iorder` is parsed and checked. Set both explicitly. A negative test changing
only `mol_iorder` did not alter the output. First-order reconstruction is a
**diagnostic candidate**, not an accuracy pass: it must be checked for excessive
numerical diffusion, reaction-zone error and grid dependence.

Preparation, bounded launch and artifact analysis are in `tools/pelec/prepare_wave.py`,
`modal_wave.py`, `collect_result.py` and `analyze_wave.py`. The default 2 ns probe
cannot certify propagation. The 0.2 us extension still covers only about 1.49
reference induction times; full G2b and sustained-engine claims remain separate.
