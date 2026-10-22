# Reduced 2D workflow: completion boundary and acceptance

This completes the functional software track F1–F4 on `main`. It does not close
RDE-001 or mark the broader physical-validation stages complete. The independent
sustaining-wave study and the 3D branch remain separate.

| Planned capability | Implementation | Verification |
|---|---|---|
| Explicit physical/numerical case; supported geometry and result contracts | `contracts.py`, `run.py --preflight`; SI geometry, original feed references, omissions/capabilities, native-field metadata | Exact annulus areas/volume, unit conversions, stable source identity, reject coreless/CAD/nonuniform input before output |
| Calibration and reference separation | `calibrate.py`, `reference.py`, `model_audit.py` | CJ/jump invariants, optional pinned physical references, no imported calibration side effects |
| Conservative 2D solver and source controls | `physics.py`, `solver.py` | Sod, contacts, directional/row equivalence, reaction ODE/refinement, positivity failures and native RK budgets |
| Bounded execution, formed start, progress, interruption/restart | `run.py`, `formed.py` | CLI start/resume, immutable inputs, exact replay, locks, interrupted-write recovery, initial inventories |
| Windowed native mass/energy/momentum/force/Isp accounting | `window_report.py` | Known analytical forces with nonzero storage, partial steps, missing/corrupt data, independent control-volume balance |
| Optional adiabatic wall drag and model-dependent torque | `physics.py`, `solver.py`, native reports | Exact decay/heating, reversal, zero-Cf bitwise baseline, coefficient/time sensitivity, angular storage/flux balance and restart |
| Pressure/front/reaction inspection | `coupling.py`, `plot.py --coupling`, streaming `--workflow` | Known travelling peaks, periodic seam, ambiguity/cadence gates, pressure and reaction shown together; no automatic detonation label |
| Spectra, rolling spectral windows and reference comparison | `workflow_analysis.py` | Known sinusoid power/frequency, changing-frequency signal, conservative irregular-sampling limit, short/flat data qualifications, nominal Run 937 identity guard |
| Saved-data reports, playback, wrapped/head-end views, periodic preview | `plot.py --workflow`, optional `--follow` | Read-only CLI acceptance, no solver import, complete/incomplete markers, new-checkpoint-only refresh, bounded corrupt-prefix retry; visually checked PNGs |
| Reusable sensitivity comparison | `--compare-runs` | Shared-window reductions, explicit changed settings/confounds, duplicate-run and incomplete-window rejection; CSV/JSON export |
| Illustrative roll response | `--inertia-kg-m2` with the wall model | Constant-torque closed form and reversed-sign checks; no vehicle-stability claim |

## Work deliberately not declared complete

- Sustained Run 937 detonation, settled wave count/speed and physically validated
  pressure, thrust or torque. Existing D1/D2 failures remain specific open cases.
- Production fixed-model mesh/source/outlet/window and coefficient-sensitivity
  campaigns. The software can run declared case files and compare saved outputs;
  this completion run does not execute those costly studies or assert convergence.
- Full Chapter 3/4 operating maps, held-out measured-thrust experiments and
  predictive design rankings. Mundt Run 937 has no measured thrust target.
- The independent report's full **2.5D** tier: radial momentum/velocity,
  centrifugal pressure split, curvature loss, heat loss, injector-face shear and
  separate inner/outer wall states. Current drag is one mean-radius closure.
- CAD import, nonuniform/coreless geometry, alternate CFD backend installation,
  detailed-chemistry CFD, GPU port and 3D. Unsupported geometry is rejected.

The first working iteration's **software** is complete when the final acceptance
suite and CLI/visual checks pass. Its **physical model** remains a research
prototype subject to the above gates. The plan's Stage 3 sustained-wave gate and
Stage 4 predictive validation are not relabelled as passed.
