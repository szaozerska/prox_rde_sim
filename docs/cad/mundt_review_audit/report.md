# Mundt CAD parameter audit

Measured from the source-locked STEP reconstructions. This is a selected constant-annulus reduction, not an assembled CFD fluid domain.

| Parameter | CAD (SI) | Paper (SI) | Difference (%) |
|---|---:|---:|---:|
| r_outer_m | 0.0381 | 0.0381 | +0.00000 |
| r_inner_m | 0.0330962 | 0.0331 | -0.01148 |
| length_m | 0.0762 | 0.0762 | +0.00000 |
| gap_m | 0.0050038 | 0.005 | +0.07600 |
| area_ratio | 0.109592514 | 0.11 | -0.37044 |
| fuel_diameter_m | 0.0007874 | 0.00079 | -0.32911 |
| oxidizer_diameter_m | 0.0012446 | 0.00124 | +0.37097 |
| fuel_count | 72 | 72 | +0.00000 |
| oxidizer_count | 72 | 72 | +0.00000 |
| impingement_height_m | 0.00215571044 | 0.00216 | -0.19859 |
| impingement_diameter_m | 0.0709168 | 0.0712 | -0.39775 |

## Bore counting

Areas are normal circular bore areas, summed once per distinct cylindrical axis/radius. Split B-rep faces are joined; feed passages and process-stage parts are not additional injection holes.

- fuel: 72 surface patches -> 72 distinct bores.
- oxidizer: 288 surface patches -> 72 distinct bores.
- instrument_port_candidates: 24 surface patches -> 24 distinct bores.

## Interpretation and unresolved geometry

- These are review reconstructions, not author-certified CAD or final CNC/print exports.
- The archive predates the onshape-applied-validation.json correction record in output/cad-fix; this audit does not certify the latest injector revision.
- Sleeve translation -4.445 mm aligns the port-station pattern approximately; this is inferred registration, not a verified assembly constraint.
- Do not mistake the sleeve full length or material volume for annular combustor length or gas volume.
- Bore selectors are reviewed diameter/angle windows, not expected counts. New geometry or source hashes require a new feature mapping.
- Pressure diagnostics remain the paper/base-case stations: CAD reveals candidate holes, not which holes were used.
- outer_wall selected surface does not cover the entire annulus; scalar continuation is an explicit approximation, not a measured gas boundary.
- Separate fuel/oxidizer jets and mixing become an equivalent premixed inlet.
- Axial/radial end features, port cavities and the downstream expansion are omitted.
- Radial gradients and full CAD wall surfaces are not represented by the 2D backend.
- Solid-part volume is not a validated connected gas domain.
- Only the selected cylindrical wall radii and datum separation enter the constant-annulus case; enlarged sleeve seat near the inlet is continued as the nominal outer cylinder.

## Inputs CAD cannot determine

- Propellant identity, mixture ratio and separate feed thermodynamic states.
- Mass flow, discharge coefficient, plenum dynamics and injector recovery.
- Chemistry, reaction rates, transport, wall temperature and roughness.
- Startup charge, pre-detonator forcing and initial gas state.
- Observed wave count/frequency, pressure measurements and averaging window.
- Which instrument ports are active and how their clocking maps to the assembled engine.

The paper case uses nominal table values. The CAD case is a geometry sensitivity candidate; it retains the supplied base case operating/chemistry/startup settings. Neither case demonstrates sustained detonation or paper-result reproduction.
