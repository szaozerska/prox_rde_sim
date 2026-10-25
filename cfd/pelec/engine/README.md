# Pending native engine workflow

`cases.json` records the requested Run 937 and two additional geometry variants.
`visualize.py` renders unwrapped pressure, native heat release, numerical schlieren
and vorticity plus a cylindrical mapping from an explicitly supplied SI NPZ.
The wrapped view is a coordinate mapping, not resolved radial/3D flow.

This is scaffolding: no native engine adapter has passed acceptance and no engine
fields have been exported by this increment. The input contract is tested; the
renderer has only a synthetic zero-heat smoke check, not engine visual validation.
See the [P2 report](../../../docs/verification/pelec_2d_propagation/README.md).

Input arrays: `time_s`, uniform cell centers `x_m`, `y_m`, and (time,x,y) arrays
`pressure_Pa`, `density_kg_m3`, `heat_release_W_m3`, `u_mps`, `v_mps`. The input
must cover one periodic circumference, with axial feed at the bottom. Use actual
saved native fields; do not manufacture a traveling engine wave for this renderer.
