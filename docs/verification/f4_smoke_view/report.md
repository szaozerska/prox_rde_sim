# Saved-window report

Window: 0.055–0.25 µs; mode: development_benchmark; saved run status: completed_limit.

Physical validation: not established by this report; transient window, no steady-state or sustained-detonation classification.
Saved invalid-state count: 0.

| Quantity | Result |
|---|---|
| Mean modeled engine wall torque | 3.1006728e-06 N m |
| Mean native annulus-exit force | 8.7366045 N |
| Mean exit force from control-volume balance | 8.7366045 N |
| Mean cell-centre exit estimate | 17.241455 N |
| Mean inlet mass flow | 0.015042484 kg/s |
| Mean outlet mass flow | 0.0019040505 kg/s |
| Annulus-exit effective Isp | 59.224642 s |
| Chemical-to-thermal conversion | 0 J |
| Maximum scaled conservation residual | 1.0663203e-16  |

Source: `/Users/sgfx/Desktop/Projects/prox_rde_sim/rde_sim_starter/runs/f4_workflow_smoke`; committed step 61.
Input SHA-256: `53ee9c6700763070a4e328cf2daa3a421072190607dfb8fd7623c251b020aae6`.

| Axial station [mm] | Window mean pressure [kPa] |
|---|---:|
| 0 | 379.84628 |
| 2 | 377.10685 |
| 4 | 374.36741 |

These are transient station means, not a comparison to experimental long-window averages.

| Conserved quantity | Storage change | Net influx + source | Residual |
|---|---:|---:|---:|
| mass [kg] | 2.5619945e-09 | 2.5619945e-09 | 1.06e-22 |
| azimuthal_momentum [kg m/s] | -3.8336494e-09 | -3.8336494e-09 | -1.93e-21 |
| axial_momentum [kg m/s] | 3.1779577e-06 | 3.1779577e-06 | -1.27e-21 |
| total_energy [J] | 0.013459865 | 0.013459865 | -3.12e-17 |
| reacted_mass [kg] | -7.4255174e-11 | -7.4255174e-11 | -1.09e-24 |

Budget closure within 1e-10: **True**.

39 contributing steps; 0 partially included.
native integrals prorated within partial steps; inventory linearly interpolated between accepted states; other samples use step-end rectangles.
partial-step closure checks this interpolation, not an independently evolved state.

Native and control-volume exit forces describe the same contribution; do not add them. These are not whole-engine thrust estimates.
Effective Isp uses net injected mass over this same window; it is not validated engine performance.
Engine torque: constant-Cf adiabatic closure, unvalidated; mean-radius approximation; no vehicle stability claim.

## Workflow qualifications

surface (theta,z) model; cylindrical display is not 3D or the full proposed 2.5D tier
Radial momentum, centrifugal pressure split, curvature loss and heat loss are not implemented.
Spectral peaks are pressure oscillations, not a detected detonation mode.

Experimental pressure comparison unavailable: geometry.r_outer_mm differs from nominal Run 937 reduction; geometry.r_inner_mm differs from nominal Run 937 reduction; geometry.length_mm differs from nominal Run 937 reduction; development benchmark is not an experimental comparison

See `index.html` for saved field playback, views and numerical plots. No simulation runs in the viewer.
