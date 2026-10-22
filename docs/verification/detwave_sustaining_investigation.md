# Detonation sustaining investigation — October 22, 2026

Branch: `2d-modelling-detwave-sustaining-fix`, created from GitHub main
`9695ae57b718bbc21394956c6fb7c961ebf8af88`. Worktree:
`/private/tmp/prox-rde-detwave-fix`. Original dirty main checkout is preserved.
The user's branch instruction supersedes historical documents saying main only.

## Initial assessment and hypotheses (before new runs)

Reviewed README, HANDOFF, revision 10, the C1–C6 plan, paper/model audit,
RDE-001, C5 results and the local independent investigation. Historical plans
are context, not fresh evidence. Mundt printed pp. 9, 11–12, 52, 74–78 and 90
were checked directly in the supplied PDF.

**Critical assumption:** experimentally sustained Run 937 does not imply this
particular reduced model must sustain. The 1 mm half-reaction distance is our
numerical model choice; Mundt does not prescribe it. Its 4.177 mm 95%-reaction
tail is comparable to a nominal 3.8 mm fresh layer. The physical reference has
0.03952/0.05108 mm half/95% distances. Similar CJ speed does not validate timing.

| Hypothesis | Existing evidence | Discriminating next evidence |
|---|---|---|
| H1: slow thickened chemistry loses coupling under transverse expansion | C3 thin formed layer fails; thick layer survives its bounded window; C5 shorter chemistry remains coupled for 10 us | Same-mesh engine comparison with fixed formed startup and original/quarter-length chemistry |
| H2: blast startup never establishes a viable wave | Original zero-velocity burned patch is not a traveling detonation; C4 blast is weaker | Original chemistry with formed startup tests whether startup alone suffices |
| H3: contact diffusion consumes/heats fresh gas and alters coupling | Contact burning is mesh dependent; initial aligned thin layer still fails | Inspect full fields, fresh inventory, ring heat release; conditional mesh check, not blanket dismissal |
| H4: replenishment/outlet assumptions prevent periodic survival | Layer controls omit both; existing inlet is idealized and annulus exit omits expansion | Periodic engine through 189.394 us, with native budgets and inlet/outlet diagnostics |
| H5: timestep or coordinate defect | C1 direction/row and C2 source checks argue against tested defects | Independent reactors and planar timestep controls for the selected execution settings |

Do not call H1 uniquely confirmed, impose a universal h/L50 threshold, infer
detonation from pressure alone, or use larger ignition energy as an automatic fix.
The inferred 3.8 mm refill height uses *measured* two-wave frequency; it is not a
fixed operating layer for a simulation that may select one wave.

## Predeclared test list and stop rules

1. Fast existing regression plus independent initialization/seam/inventory checks.
2. Evaluate existing supported source fractions 0.20 versus 0.10/0.05 in cold,
   warm and shock-heated reactors and formed planar waves. Accept <=2e-4 absolute
   progress error, decreasing on halving; planar speed change <1%, valid states,
   budget residual <1e-10. This changes accuracy settings, not chemistry or the
   integrator. If it fails, retain 0.05 rather than replace the integrator.
3. A 2 us engine benchmark at 0.125 mm; compare source fractions over an early
   common window before adopting the faster setting. Require <1% total heat
   difference and <=one-cell front displacement, valid states and budgets.
4. Periodic Run 937 geometry, formed finite 25 mm charge, 3.8 mm initial layer,
   1500 K products, original inlet/outlet; 0.125 mm mesh. Original and preselected
   L50=0.25 mm chemistry, no rate search. Cap each at three reference passage
   intervals (189.394 us). Stop on invalid state; preserve failed evidence.
   Check runtime after benchmark; stay within a few hours rather than launching
   a broad sweep. Chemistry-dependent ZND profiles change initial inventories;
   record that confound rather than calling this a pure identical-state A/B.
5. Assess late shock-associated reaction, travel beyond initial charge, periodic
   return into replenished gas, fresh inventory, boundary/source budgets, and
   pressure–reaction space-time plots. Conditional refinement only for a
   specific uncertainty. A short success is not validated steady Run 937.

## Literature implications

Mundt Table 3-2 (p.52) reports two waves and means over the final 100 ms of a
0.696 s burn. Equations 4.3–4.5 use measured frequency to infer refill height.
The h/cell-size >=4.5 discussion (p.90) is a thrust guideline, explicitly not a
rule; it is not a survival threshold for our artificial Arrhenius model.

[Strakey & Ferguson, AIAA 2022-1113](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf)
use a 12-species, 38-step mechanism with stiff split chemistry, include an exhaust
plenum, check numerical wave-speed sensitivity, and typically reach limit-cycle
operation after 3–5 ms. This supports checking chemistry/numerics and downstream
closure, not asserting that 189 us validates experimental means.

[Li, Mi & Higgins, geometric scaling](https://arxiv.org/abs/1405.7753)
study finite reactive layers with yielding confinement and critical dimensions.
Their pressure-dependent kinetics support the mechanism analogy, not a numerical
threshold transferable to methane/oxygen or this one-step surrogate.

## Execution/provenance log

- Initial literature/plan assessment complete. No new propagation result yet.
- Preflight correction, before engine runs: original chemistry's tabulated
  99.9999% tail is 23.768 mm, so a 20 mm charge cannot contain it. Use the same
  25 mm finite charge in both engine cases. The initializer correctly rejected
  the incompatible original-chemistry construction; no flow ran in that attempt.
- Four initializer checks passed: independent normal-shock identities,
  piecewise quadrature through the periodic seam, all five inventories across
  meshes/phases, and translation invariance through actual flow steps.
- Investigation initializer reuses C2 profile utilities from branch base and
  ports the finite periodic-charge construction from the concurrent uncommitted
  C6a implementation into an isolated module. The original files are untouched;
  this branch verifies the port before using it. Production defaults unchanged.
- A ten-minute chat follow-up was configured for at most three hours. Local
  automation requires the computer awake and app running; quitting is not a
  supported guarantee. Every run saves progress/checkpoints for recovery.
