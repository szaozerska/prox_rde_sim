# Native initialization adapter

`prob.H` is copied unchanged from PeleC `Exec/RegTests/zeroD` at the pinned
revision. CMake selects upstream grimech30 instead of LiDryer. `prob.cpp` and
`prob_parm.H` specify methane/oxygen initialization only. The upstream BSD license
is retained. No kinetic, thermodynamic or temperature-inversion source is patched.
The domain is compiled with PELE_DIM=2. All state evolution is upstream code.
