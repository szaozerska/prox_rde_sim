# Saved-window report

Window: 0.55–1.75 µs; mode: development_benchmark; saved run status: completed_limit.

Physical validation: not established by this report; transient window, no steady-state or sustained-detonation classification.
Saved invalid-state count: 0.

| Quantity | Result |
|---|---|
| Mean native annulus-exit force | 186.36946 N |
| Mean exit force from control-volume balance | 186.36946 N |
| Mean cell-centre exit estimate | 203.95718 N |
| Mean inlet mass flow | 0.23905448 kg/s |
| Mean outlet mass flow | 0.24896653 kg/s |
| Annulus-exit effective Isp | 79.498182 s |
| Chemical-to-thermal conversion | 1.2635803 J |
| Maximum scaled conservation residual | 2.8501649e-15  |

Source: `/Users/sgfx/Desktop/Projects/prox_rde_sim/rde_sim_starter/runs/c6a_formed_benchmark`; committed step 556.
Input SHA-256: `5c5edcd0bd78bf94ad05346afa8a71017cb769c8a158b85aae65db30d1684692`.

| Axial station [mm] | Window mean pressure [kPa] |
|---|---:|
| 0 | 1427.7821 |
| 22.2 | 377.91697 |
| 34.9 | 377.91697 |
| 47.6 | 377.91697 |
| 60.3 | 377.91697 |
| 73 | 377.91697 |

These are transient station means, not a comparison to experimental long-window averages.

| Conserved quantity | Storage change | Net influx + source | Residual |
|---|---:|---:|---:|
| mass [kg] | -1.1894462e-08 | -1.1894462e-08 | -1.28e-19 |
| azimuthal_momentum [kg m/s] | -4.3368087e-19 | 0 | -4.34e-19 |
| axial_momentum [kg m/s] | 0.0017005603 | 0.0017005603 | 2.6e-18 |
| total_energy [J] | 1.087929 | 1.087929 | -6.87e-13 |
| reacted_mass [kg] | -6.9017964e-08 | -6.9017964e-08 | -8.25e-20 |

Budget closure within 1e-10: **True**.

335 contributing steps; 2 partially included.
native integrals prorated within partial steps; inventory linearly interpolated between accepted states; other samples use step-end rectangles.
partial-step closure checks this interpolation, not an independently evolved state.

Native and control-volume exit forces describe the same contribution; do not add them. These are not whole-engine thrust estimates.
Effective Isp uses net injected mass over this same window; it is not validated engine performance.
Engine torque unavailable: no wall-traction model; angular conservation residual is not engine torque.
