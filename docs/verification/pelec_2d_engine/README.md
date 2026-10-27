# Native 2D engine movie attempt — 27 October 2026

## Requested deliverable and interpretation

Target 1 ms native PeleC movies for Run 937, followed by controlled 51-FI-5
and 25-FI-5 geometry variants. Unwrapped pressure, heat release, density-gradient
and vorticity panels plus a wrapped cylinder view use actual native fields and
explicit simulation times. Cylinder wrapping is a visualization, not radial flow.
The external solver and candidate FFCM1_Red chemistry remain unvalidated for
predicting experimental sustainment. No physical success is inferred from a movie.

## Progress before engine launch

Native MOL's existing Lax–Friedrichs flux removes the observed state/element/EOS
failures in the 0.2 µs planar lab and moving-frame controls. The original-flux
frozen-chemistry moving-frame control also passes these checks. Short-window
wave speed and reaction structure remain outside the previous screening limits;
these controls do not establish physical propagation acceptance.

A new native engine problem supplies a finite +theta formed-wave launch,
periodic circumference, homogenized premixed pressure-responsive feed, and an
approximate pressure outlet. Its native evolution and chemistry sources remain
unmodified. Launch projection preserves conservative energy/species; background
and inlet share elemental composition. The 3.8 mm fresh layer is an initial
condition, not continuously imposed. There are no resolved impinging jets,
pre-detonator tube, radial momentum dynamics, CAD or 3D branch changes.

The exploratory Run 937 mesh is 512 x 192 (0.437 mm circumferential spacing),
which does not resolve the approximately 46 µm candidate-chemistry half-reaction
length. Even a completed movie would not prove mesh-independent sustainment.

## Completed controls and failures

- Uniform native engine control: 20 ns, six frames; stationary state preserved.
  Independent EOS energy residual 1.89e-11. Cold-feed control: 5 µs, six frames,
  mass gain 9.6144e-7 kg, independent EOS energy residual 4.69e-10.
- First engine target: 1 ms; CVODE stopped at approximately 0.042 µs.
  Its internal step collapsed; no post-initial 5 µs output was reached.
- Smaller fixed 1 ns timestep: stopped at 0.0431 µs. The saved 0.0401 µs
  field contains minimum Y=-0.04183 (HO2, near x-periodic seam), Tmin=156.67 K,
  and maximum element-fraction error 0.001148. This is invalid numerical output,
  not physical extinction, fuel exhaustion, or experimental disagreement.
- Inspection found AMReX device assertions are disabled by the upstream release
  build. `AMREX_ALWAYS_ASSERT` does not guarantee device execution in that build.
  Earlier statements that these engine runs checked every step were incorrect.
  Independent exported-field checks did reject the invalid field. The engine
  problem guards now use an unconditional CUDA trap, independent of NDEBUG;
  cached engine images lacking the guard manifest flag are rejected. A compiler
  flag-only attempt was insufficient because the underlying assert is still
  disabled by NDEBUG; its build also stopped when a local exporter file changed
  during image construction, so no run result is attributed to that attempt. Numerical source and
  thermodynamic fit ranges remain unchanged.

The first two controls used the previous release build; their independent saved
field checks are valid, but are not evidence of functioning every-step guards.
A native negative control must demonstrate the rebuilt guard actually aborts.

## Next bounded actions

1. Verify the assertion-enabled build stops at its first invalid state. Inspect
   source coupling and compare existing native MOL corrections and Godunov/SDC
   with unchanged physical inputs; no species clipping or expanded thermo range.
2. Only a state-valid reacting launch may be extended toward 1 ms. Preserve
   failed attempts and actual end times; never stretch a short prefix to 1 ms.
3. Render/inspect both views from valid native fields, publish provenance and
   checks, then run additional geometries. P2 physical acceptance stays open.

### Declared trace-budget experiment

The strict Godunov/SDC run at fixed 100 ps passes to 0.2 µs. Adaptive Godunov
first-step failures are 1e-10–8.5e-10 in trace CH/CH3 fractions, unlike the MOL
percent-level failure. Four deferred corrections alone do not remove them.
Before attempting a longer preview, test an explicitly separate Y >= -1e-8
budget (0.01 ppm), with no clipping, unchanged element/sum/EOS/temperature
checks, and the same independent fields compared against the strict 100 ps
baseline. This does not change the default -1e-12 guard or P2 acceptance.
Predeclared comparison: final pressure/density/temperature relative L2 error
below 1%, integrated mass/energy difference below 1e-5 relative, and no growing
violation of the trace budget. Failure blocks extension. Chemistry source and
mechanism remain unchanged. This is a truncation-error experiment, not a claim
that all negative fractions are roundoff or that any tolerance can be relaxed.
Compare the field L2 errors both over the whole domain and the bottom 15 mm
containing the launch/feed layer, so the largely unchanged background cannot
hide launch errors. Both regions must pass. The 1 ms deliverable remains pending.


## Final result of this increment

**The requested approximately 1 ms engine movie is NOT complete.** No result
here establishes sustained or failed experimental Run 937 detonation.

- The unconditional CUDA guard demonstrably stops an invalid native state.
  MOL with two corrections fails its first 100 ps step. The instrumented
  one-correction MOL run also reports negative H2 of approximately -5.35e-8
  near the periodic seam, rather than a harmless floating-point sign at zero.
- Godunov/SDC with fixed 100 ps completes **0.2 µs** with six saved frames,
  every-step guards, independent element/EOS checks and no state clipping.
  This is a short native launch diagnostic, **5,000 times shorter than 1 ms**.
- Adaptive Godunov and four-correction Godunov fail the strict species guard.
  The explicitly separate 1e-8 trace-budget experiment also fails as the
  adaptive step grows (about 1.055e-8 negative CH2 after the 19th step).
  Fixed 4 ns fails that budget on step two (about 1.114e-8 negative CH).
  The predeclared comparison therefore cannot pass; the budget was not widened
  further, and no long run was launched with invalid states.
- One trace image build disconnected locally. Its completed native build was
  reused; the retry used Modal detachment and retained a separate run identity.
- The two short GIF formats are actual native pressure/heat-release/gradient/
  velocity data. Their labels and manifests preserve 0–0.2 µs; they are not
  padded, retimed or presented as a 1 ms movie. The wrapped view has explicit
  pressure and density-gradient scales. First/last images were visually checked.

The evidence narrows the practical blocker to timestep-sensitive transport/
reaction coupling for the engine launch, especially the product/fresh-gas
interfaces. It does not yet prove a unique root cause. It is not evidence of
fuel exhaustion, missing injector fuel pulses, collision cancellation, or a
need for radial/3D terms. More GPUs alone will not fix negative species states.

Next work is a focused coupling/positivity and timestep study at these localized
interfaces, including a reduced reproducer and a longer strict valid control.
Do not widen tolerances further to obtain a movie. The coarse mesh remains a
separate physical-accuracy limitation even after numerical validity is fixed.
No additional engine geometry campaign or CAD work was started.


## Diagnostic media and validation

- [Unwrapped 0–0.2 µs native launch](launch_0p2us/unwrapped.gif)
- [Cylinder-mapped 0–0.2 µs native launch](launch_0p2us/wrapped.gif)
- [Exact frame times and source checksum](launch_0p2us/animation_manifest.json)
- [Independent saved-field checks](field_checks.json)
- [Native execution, case and build records](execution_evidence.json)

The 16 Python adapter tests pass; Ruff and scoped whitespace checks pass.
Native solver failures are recorded separately and are not overridden by those
unit-test results. Both GIFs contain six frames and their source hash matches
the committed compact `fields_si.npz`. No cloud simulation is left running.
