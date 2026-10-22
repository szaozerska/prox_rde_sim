# Review of the proposed reaction-length / layer-height diagnosis

October 22, 2026. **Assessment: credible leading hypothesis; not a demonstrated
root cause. The decisive proposed controls have not been performed.** This review
reads the submitted diagnostic, production source, existing D1–D3 results, and
primary literature. It postprocesses saved profiles/histories and evaluates simple
algebra; it does not advance a CFD solver or run a new thermochemical calculation.

## What was already checked

| Question | Existing evidence | What remains untested |
|---|---|---|
| Is the surrogate much thicker than the physical reference? | D3: half-heat distance 1.000 versus 0.03952 mm; 95%-heat distance 4.177 versus 0.05108 mm. The paper audit explicitly identified the reaction tail as comparable to the initial layer. | Whether the present semi-confined layer can support an already formed detonation with this chemistry. |
| Does the surrogate support a confined propagating wave? | D1/D3: single-row 1D propagation, source-step check, three spatial grids; speeds and fit windows remain mesh sensitive. | A multirow, transversely uniform reactive strip and directional checks. These would test particular 2D implementation paths, not exclude every possible 2D bug. |
| Does increasing startup fill help? | D2 doubled requested fill to 7.6 mm and also increased ignition energy. It did not demonstrate sustained rotation. | A controlled layer-height comparison independent of ignition strength. D2 is not such a test and did not identify a critical height. |
| Can numerical contact mixing cause burning? | D3 moving-contact controls: reactive conversion decreases with refinement; frozen controls release no heat. | Its causal contribution in the evolving 2D engine, including interface stretching and pressure/temperature changes. |
| Can the current igniter start a wave in a layer known to support one? | The igniter initiates the 1D tube wave; it has not demonstrated sustained rotation in the two engine starts. | A formed-profile versus blast comparison at otherwise matched, demonstrated sustainable layer conditions. |

We had identified ingredients of the proposed explanation, but had not performed
its distinguishing experiment. The earlier tests must not be described as having
ruled this mechanism out or tried its remedy unsuccessfully. A confined 1D wave
is useful verification; it does not verify survival with transverse pressure relief.

## Checks of the numerical claims

From the saved `runs/d3_reference/profiles.npz`, integrating distance divided by
shock-relative velocity along the saved surrogate profile gives approximately
2.261 microseconds to half heat release and **5.723 microseconds to 95%**. The
saved physical profile reaches those fractions in 0.1327 and 0.1440 microseconds.
These are postprocessed steady reference structures, not measured engine-particle
histories or new simulations.

The surrogate frozen post-shock sound speed is 913.9 m/s. Dividing the requested
3.8 mm height by that speed gives **4.158 microseconds**; using its actual coarse
cell-mask height, 4.0105 mm, gives **4.388 microseconds**. These numbers support
competition between reaction and transverse expansion. They do not establish a
universal failure inequality: reaction length is streamwise, layer height is
transverse, and the evolving front, sonic surface, confinement impedance and
heat-release distribution determine the coupling. The 95% point is not a proven
hydrodynamic cutoff. The physical/surrogate difference is not a uniform 25-fold
stretch: the ratio is about 25 at half heat but about 82 at 95% heat.

The pressure-relief/finite-layer mechanism has a basis in detonation research.
For example, [Li, Mi and Higgins](https://arxiv.org/abs/1405.7753) initialize a
formed CJ structure and study propagation or failure in layers with yielding
confinement. Their pressure-dependent chemistry differs from ours; their critical
sizes cannot be imported as our threshold. [Taileb et al.](https://doi.org/10.1016/j.combustflame.2020.04.018)
study how kinetic models affect hydrogen–oxygen layer quenching. These sources
support testing the mechanism, not claiming it is already confirmed for Run 937.

The saved 0.752 mm ring shows strong reaction declining sharply during startup:
its maximum rate is about 47,699 /s at 20 microseconds, 627 /s at 30, and 30.7 /s
at 40. However, the full domain still has maximum rates near 85,816 and 91,406 /s
at 30 and 40 microseconds. The ring alone cannot establish absence of every
shock-associated reaction elsewhere, nor date a fully formed detonation's failure.
A more defensible description is **failure to establish sustained propagation
from this startup**. Strong reaction persists elsewhere without establishing a
detonation. Track slopes require a declared operator and window; the 90.5
microsecond CJ circumference-crossing time is correct, but is not an “almost
flat” trajectory on this plot's 189-microsecond time axis.

The 1D saved pressure-threshold track supports an appreciable startup transient:
its 20–30 microsecond fit is about 2040 m/s, rising to about 2610 m/s over 30–40
microseconds and settling closer to the model CJ speed later. The front is at
62.4 mm by 30 microseconds, approximately 52 mm beyond the initial 10 mm patch.
This is consistent with delayed development in the confined tube; a pressure
threshold alone does not identify an exact formation time.

The D1 native budgets give **87.267 J converted**, **84.430 J initially unspent
chemical energy after ignition masks**, and **273.910 J injected chemical energy**.
The note's 87 J is accurate; its 92/280 J are approximate geometric/capacity
estimates rather than the actual discretized inventories. Late inlet flow reaches
267.756 g/s, but its whole-run mean is about 262.954 g/s. Gas supply exists; this
does not validate local refill, mixing, temperature or delivery during the wave.
At the initial fresh-gas density, the reference mass flux corresponds to 60.8 m/s.

For a 1000 m/s normal shock into the initial stationary 300 K surrogate gas,
Mach is 2.906 and the frozen post-shock temperature is about 588 K. The initial
reaction coefficient there is 94.2 /s, with an isothermal e-folding time of 10.6 ms.
At 630 K that e-folding time is approximately 5.4 ms. Neither is a self-heating
ignition delay. Actual shock-relative speed and upstream state must come from
fields. The qualitative low-temperature/slow-reaction argument is reasonable;
the quoted temperature and delay do not identify the cause by themselves.

## Claims that need correction or qualification

**The outlet was not inactive until 43 microseconds.** The first saved accepted
step, at 0.01445 microseconds, already has positive outlet flux. At 30 microseconds
it is about 236.4 g/s. The outlet cells are all axially subsonic then (Mach about
0.985); about 91% remain subsonic at 43 microseconds. They become fully supersonic
for part of the later run, but are again entirely subsonic at the end (Mach
0.946–0.989). Boundary activity starts immediately because the initial interior
pressure differs from the pressure boundary. Axial/normal Mach, not total-speed
Mach, determines the local outflow characteristic count.

An initial acoustic travel estimate from the outlet through hot products to the
layer is about 94 microseconds, which makes direct outlet influence a less obvious
explanation for very early near-injector decay. This is only a travel-scale estimate
in an evolving flow. The diagnostic's claimed delayed outflow and permanent
supersonic isolation cannot be used to rule out boundary effects.

**The contact test does not bound engine interface losses.** Dividing its 726.4
J/m² by the initial 3.8 mm layer's approximately 82,618 J/m² gives 0.88%. The
arithmetic is valid; transferring that fraction is not. The test has one planar
contact at prescribed pressure, temperatures and advection speed. The engine has
a stretching, compressed, evolving interface. A global percentage also does not
exclude localized changes to shock/reaction coupling. This candidate remains
open without treating it as the demonstrated cause.

**Light confinement and initiation energy are credible concerns, with limits.**
The initial products are five times less dense at equal pressure, and have lower
acoustic impedance. That motivates the layered test. The square-law initiation
scaling quoted in the diagnostic applies to cylindrical blast similarity with
other dimensionless conditions controlled; [Caltech's glossary](https://shepherd.caltech.edu/EDL/projects/JetA/Glossary.html)
distinguishes it from planar and spherical scaling. It does not establish the
energy deficit of this wall-adjacent rectangular patch, particularly when the
physical and surrogate chemistry are not uniform rescalings of each other.

**A formed-profile start is a useful control, not a universal RDE requirement.**
For example, [Strakey and Ferguson's methane–oxygen validation study](https://netl.doe.gov/projects/files/ValidationofaComputationalFluidDynamicsModelofaMethaneOxygenRotatingDetonationEngine_010522.pdf)
uses a hot, pressurized ignition kernel and reports a subsequent startup transient.
A pre-detonator differs from our patch, but that alone does not establish that
an imposed patch is incapable of starting an RDE.

**Other causes have not been eliminated.** The injector affects the face from
the start, and the layer evolves immediately. The paper audit concluded that
missing 3D was not an established cause; it did not conclude that dimensional
reduction is irrelevant. Conservation and sensible-looking fields do not rule
out all numerical errors. Differences in thermodynamics also affect sound speed,
expansion and reaction sensitivity and cannot yet be assigned a secondary role.

**The runtime estimate is not a benchmark.** A uniform 0.05 mm annulus grid is
about 6.82 million cells. Keeping the same one-step shape and reducing half-length
from 1 to 0.25 mm multiplies k by four; its source cap alone implies approximately
52,400 steps over the current duration. That is roughly 400 times D1's cell-step
work, not an established 1000-fold runtime. Flow restrictions and memory/parallel
performance can change elapsed cost. Shortening the domain or imposing a half-
circumference sector changes the physical problem and needs separate justification.
A geometrically scaled engine also requires consistent scaling of chemistry,
flow and relevant times; increasing layer height alone is not complete similarity.

## Recommended discriminating tests — not executed

1. Multirow fully fresh strip with transverse-uniform initialization, compared
   against the existing 1D run at matching grid, timestep and boundaries. Include
   direction/rotation checks. Passing is a targeted implementation check.
2. A formed detonation entering a finite fresh layer beneath hot products, with
   fixed chemistry and several deliberately selected heights. Separate startup
   from sustained propagation, control numerical cell-average initialization, and
   prevent driver/remote-boundary contamination. Bracket any critical height and
   assess mesh sensitivity before quoting a threshold.
3. At a height that sustains the formed wave, compare an explicitly documented
   blast start. Account for energy, inventory and momentum; the two starts need
   not have equal energy, but their differences must be reported. This separates
   initiation adequacy from propagation capability in this model.

These controls should precede expensive full-engine 3D reacting studies, while
3D backend/geometry preparation can proceed independently. Failure only at thin
layers would demonstrate a model-specific propagation limitation under the test
conditions; connecting it causally to D1 still requires matched startup/confinement
and engine evidence. Failure at every height could instead indicate the profile,
boundaries, domain length or implementation needs attention.

A reaction-length change chosen beforehand from physical references and a
verified layer assessment is a legitimate model-sensitivity study. It is not
forbidden. Freeze each chosen chemistry across its mesh comparisons, resolve its
structure, retain failed cases and report remaining artificial thickening. A
numerically measured layer threshold alone does not physically validate a new
chemistry model. The existing rule was intended to prohibit outcome-driven tuning,
not controlled investigation of reaction length.
