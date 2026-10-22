# Saved-window report

Window: 100–180 µs; mode: engine_intervals; saved run status: completed_limit.

Physical validation: not established by this report; transient window, no steady-state or sustained-detonation classification.
Saved invalid-state count: 0.

| Quantity | Result |
|---|---|
| Mean native annulus-exit force | 482.54698 N |
| Mean exit force from control-volume balance | 482.54698 N |
| Mean cell-centre exit estimate | 482.74905 N |
| Mean inlet mass flow | 0.26730581 kg/s |
| Mean outlet mass flow | 0.41516461 kg/s |
| Annulus-exit effective Isp | 184.08166 s |
| Chemical-to-thermal conversion | 37.798805 J |
| Maximum scaled conservation residual | 4.3906775e-14  |

Source: `/Users/sgfx/Desktop/Projects/prox_rde_sim/rde_sim_starter/runs/d1_run937`; committed step 13165.
Input SHA-256: `794de1f8a3229b1dfba7a17d8d3bd1f7cf5da7981d2ce31627fec1069ef5f86d`.

| Axial station [mm] | Window mean pressure [kPa] |
|---|---:|
| 0 | 325.68471 |
| 22.2 | 345.42504 |
| 34.9 | 319.01197 |
| 47.6 | 287.24656 |
| 60.3 | 254.23285 |
| 73 | 221.81057 |

These are transient station means, not a comparison to experimental long-window averages.

| Conserved quantity | Storage change | Net influx + source | Residual |
|---|---:|---:|---:|
| mass [kg] | -1.1828704e-05 | -1.1828704e-05 | -9.76e-19 |
| azimuthal_momentum [kg m/s] | 0.00032612207 | 0.00032612207 | 5.42e-20 |
| axial_momentum [kg m/s] | -0.0078248908 | -0.0078248908 | 1.01e-16 |
| total_energy [J] | 29.79047 | 29.79047 | -1.53e-11 |
| reacted_mass [kg] | -2.6340658e-05 | -2.6340658e-05 | -6.44e-20 |

Budget closure within 1e-10: **True**.

5561 contributing steps; 0 partially included.
native integrals prorated within partial steps; inventory linearly interpolated between accepted states; other samples use step-end rectangles.
partial-step closure checks this interpolation, not an independently evolved state.

Native and control-volume exit forces describe the same contribution; do not add them. These are not whole-engine thrust estimates.
Effective Isp uses net injected mass over this same window; it is not validated engine performance.
Engine torque unavailable: no wall-traction model; angular conservation residual is not engine torque.
