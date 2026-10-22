# Saved-window report

Window: 100–180 µs; mode: engine_intervals; saved run status: completed_limit.

Physical validation: not established by this report; transient window, no steady-state or sustained-detonation classification.
Saved invalid-state count: 0.

| Quantity | Result |
|---|---|
| Mean modeled engine wall torque | Unavailable: no wall-traction model; angular conservation residual is not engine torque |
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

## Workflow qualifications

surface (theta,z) model; cylindrical display is not 3D or the full proposed 2.5D tier
Radial momentum, centrifugal pressure split, curvature loss and heat loss are not implemented.
Spectral peaks are pressure oscillations, not a detected detonation mode.

transient reduced-model vs experimental long-window mean; nominal case identity only, not validation

| z [mm] | Model window [kPa] | Experiment [kPa] | Difference [%] |
|---|---|---|---|
| 0 | 325.685 | 368.5 | -11.62 |
| 22.2 | 345.425 | 323.3 | 6.844 |
| 34.9 | 319.012 | 292.3 | 9.139 |
| 47.6 | 287.247 | 281.1 | 2.187 |
| 60.3 | 254.233 | 255.4 | -0.457 |
| 73 | 221.811 | 238.4 | -6.959 |

See `index.html` for saved field playback, views and numerical plots. No simulation runs in the viewer.
