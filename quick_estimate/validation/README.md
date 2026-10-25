# Mundt comparison: failed transfer of the algebraic screen

## What “Fable's sizing code” means

It is the Python source `Simulation/Models/chamber_sizing.py` from the user's
older RDEPathwaySpaceXBackyard repository. “Sizing” means algebraic calculation
of dimensions and refill capacity. Fable is the user's name for the earlier
code-generation workflow, not the numerical framework or a CFD library. The
framework here is Law2021's empirical cell-size relations plus mass balance.
The unchanged source is retained in `../vendor/`; the supported version adds
validation, geometry/refill checks, integer candidates and traces.

## Verdict

The unchanged quick-estimate model admits **none of the five selected annular
sustained-wave cases**, and rejects the selected real deflagration case too.
It therefore has no useful sustained-versus-failed discrimination on this small
comparison. The coreless sixth geometry is unsupported and excluded, not scored
as a prediction of zero. No coefficients were tuned after inspecting outcomes.
The numerical implementation can pass its checks while this physical model fails
against experiments. These are different acceptance criteria.

See [the generated table](mundt_results/comparison.md) and
[all inputs, diagnostics and outputs](mundt_results/comparison.json).
Reproduce from the repository root with a fresh output directory:

```sh
python3 -m quick_estimate.compare_mundt --out /tmp/mundt-comparison-new
python3 -m unittest discover -s quick_estimate/tests -v
```

## Selection and source precision

The six names identify geometries, not unique operating conditions. Mundt has
400+ tests, varying equivalence ratio and flow, and several wave modes for some
geometries. We chose one representative point per geometry near the shared
mass-flux sweep, plus a lower-flow deflagration point. Run 937 is exactly tabulated;
the remaining conditions and labels are visually read from Figures 3.13--3.18.
The selected markers are plain co-rotating modes, without counter waves. The
comparison does not score unstable, pulsing or counter-wave behavior.

- Geometry: Table 2-1, printed p.28 / PDF p.44.
- Run 937: Table 3-2, printed p.52 / PDF p.68.
- 51-FI-5: Figure 3.13, red circle near phi 1.42, flux 243; two waves.
- 25-FI-5: Figure 3.16, blue circle near phi 1.45, flux 243; one wave.
- 25-FI-3: Figure 3.17, blue circle near phi 1.42, flux 243; one wave.
- 25-FI-7: Figure 3.14, rightmost blue circle near phi 1.20, flux 239; one wave.
- 25-FI-12.7: Figure 3.18, blue circle near phi 1.40, flux 243; one wave.
- Negative: Figure 3.16, yellow square near phi 1.42, flux 162; deflagration.
  Combustion is present but sustained detonation is absent. This is not a
  zero-fuel toy example, and is not assigned the unidentified Appendix B.10 run.

Figure coordinates are approximate (phi roughly +/-0.03; flux roughly +/-5
kg/(s m2)), not exact run records. Cases near the nominal shared sweep can have
slightly different measured flow/mixture values. The input registry explicitly
retains this limitation instead of inventing run IDs or extra precision.

Fresh pressure is computed using Mundt Eq.4.1, then density from the ideal-gas
law for premixed CH4:phi/O2:2 at 300 K. This pressure fit is itself derived from
Mundt's experiments: this is a consistency/transfer check, not fully independent
out-of-sample prediction. Flow is flux times exact annular area, except Run 937's
reported flow. Cell sizes are approximate visual readings from Figure 4.2 and
interpolated in phi and pressure. The registry records every grid value. CJ
references come from Table 3-2 or approximate Figure 4.3 readings. We never feed
measured wave counts, passage frequency or inferred operating fill height back
into the estimator. No new chemical integration was run. For the deflagration control, the pressure
fit and hypothetical CJ state describe an assumed premixed state; they are not
a measured detonation state or a guarantee that the fit transfers to deflagration.

## What the outputs mean

Empty candidate lists mean the inherited rules admit no integer mode. For a
sustained experimental case, this is a miss by the model under the selected
input assumptions, not evidence against the experiment. The refill-capacity
floor is zero for each supported case, but it is not independently a prediction
of extinction. On these selected points:

- Observed primary count admitted: 0/5 supported positive cases.
- Correct absence of a candidate: 1/1 real negative case.
- Unsupported: 1 coreless case, excluded from both denominators.

One could count 1/6 agreements among supported points, but calling that “17%
accuracy” would imply an unjustified generality: this is a small selected,
figure-based sample, not a representative validation dataset. In particular,
getting the negative case right is uninformative when every case is rejected.

## Why it fails: a cell-size-independent conflict

Let C = pi D_outer and H1 = mdot/(rho U gap), the one-head refill depth in the
implemented strip model. Refill requires N Lcrit <= H1. The spacing criterion
requires K = C/(N Lcrit) <= 9. Together they require:

    K >= C/H1, and K <= 9

The five positive annular points have C/H1 approximately 43.5, 47.4, 53.3, 48.4,
and 57.7. Thus no choice of cell size or integer N can satisfy both rules with
these state/speed assumptions. This explains why merely refining the visual
cell-size readings cannot cure the disagreement. It also shows why we should
not launch further CFD or chemistry runs just to test this algebraic conflict.

The bounded sensitivity check uses U = 0.5, 0.75 and 1.0 times the CJ reference,
and cell size multipliers 0.8, 1.0 and 1.2 (nine evaluations per supported case).
All nominal and coefficient-range candidate lists remain empty. These choices
are explicit stress tests, not confidence bounds. Mundt reports bulk measured
speeds around 50--80% CJ, so using CJ alone is not the whole explanation.

The paper's strip-area approximation also becomes poor for wide gaps. Using
exact annular area for the refill diagnostic and half-CJ speed still gives
required K approximately 20--22 for all five positives, above 9. That diagnostic
is not a changed model or a new fitted prediction. The coreless case has no
inner annular wall, so its algebraic extrapolation is not treated as valid.

The transfer of the combined Law/Bykovskii/Kiyanda sizing assumptions to Mundt's
small methane/oxygen engines and inferred fresh state is failing here. We have
not uniquely isolated an empirical-rule applicability problem from fresh-state
modeling assumptions. We should not lower the pressure, change cell size or
remove a constraint merely to force agreement without independent justification.

## Practical consequence

Keep this version as an auditable reference calculator and a failed model
baseline. Do not use its no-candidate output as a hardware feasibility gate or
its refill-capacity floor as an expected stable wave count for Mundt engines.
A useful predictor would need a different, justified relation or a separately
calibrated empirical model, tested on withheld operating points including failures.
No such model has been silently substituted in this comparison.

## Verification execution

The first 17-check run exposed an overprecise, mistyped expected pressure value
in the new test fixture (difference 0.00002148 kPa). The independent audit only
reports 377.917 kPa; the check now uses that documented rounded value to three
decimal places. The implementation and comparison outputs were unchanged.
The final test run is saved in `test_results.txt`. Software checks are not scored
as successful experimental validation.
