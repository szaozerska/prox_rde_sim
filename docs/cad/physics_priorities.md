# CAD parameters that matter for the current simulations

These priorities distinguish actual measurements from future model inputs. Source:
the [archived CAD audit](mundt_review_audit/report.md), native source inventory and
[Mundt's thesis](../../Mundt2023.pdf), especially printed pp. 28–37. CAD provides
geometry; it does not supply kinetics, mixing rates, discharge coefficients,
wall temperatures, or operating-state measurements. The existing
[paper/model audit](../verification/mundt_model_audit.md) supplies the broader
physical-model context.

## 1. Injector geometry and separate streams: highest priority

Measured from the finished injector: 72 fuel bores of diameter 0.7874 mm and
72 oxygen bores of diameter 1.2446 mm, each inclined 30 degrees to the engine axis.
The uniform circumferential pair spacing is 5 degrees. The axes extrapolate to
an impingement height of 2.15571 mm and diameter of 70.9168 mm. The paper specifies
2.16 mm and 71.2 mm; the small diameter discrepancy warrants checking the later CAD
revision and drawing datums, not silently snapping the measurement to the paper.
The manifest retains each axis, hole radius, inlet intersection, pattern spacing,
and normal area for each propellant separately.

**Physical consequence:** these quantities set where fuel and oxygen enter and
geometrically meet. They influence local composition, momentum direction, mixture
availability and the refill region. The current premixed, uniform inlet cannot
resolve those effects. Impingement height is comparable to the few-millimetre
refill/startup layer discussed in the existing audit. This is a larger modeling
question than the 0.076% CAD-vs-paper gap difference. It is not proof that injector
mixing is the cause of the unresolved wave decay, or that adding it will improve
propagation.

**Act now:** retain separate fuel/oxygen areas and feeds in the common input
contract; plan a mass/enthalpy/momentum-consistent injector closure and controlled
mixing/recovery sensitivity. The 3D path needs resolved bore directions and separate
species boundaries. Do not turn the 30-degree angle into an isolated cosine
multiplier in the existing boundary condition. Bore-normal area is the hydraulic
area; an oblique face ellipse is not an additional throat area. The total measured
normal-area ratio is 0.109592514, versus paper nominal 0.110.

No meaningful tangential cant appears in this archived axis pattern; injection
is radially opposed plus axial. That geometric observation does not establish zero
engine torque: rotating pressure and wall traction still require a flow solution.

Independent primary evidence also supports treating premixing and near-injector
geometry as separate model questions: [Ayers et al., 2022](https://ntrs.nasa.gov/citations/20210024287)
varied premixing and chamber steps and observed different operating behavior. That
hydrogen/air experiment is qualitative context, not a quantitative calibration for
Mundt's methane/oxygen Run 937.

## 2. Core termination and downstream expansion: highest priority

The core ends at 76.2 mm. With the provisional sleeve placement, the selected
38.1 mm bore continues to 152.4 mm. The paper's section view confirms a cylindrical
expansion after the inner core, and places the 85.7/98.4 mm pressure taps downstream
of the annulus. The selected sleeve surface alone does not prove the complete
assembled passage or outlet attachment.

**Physical consequence:** core termination changes flow area and pressure forces;
downstream geometry can affect expansion, reflected disturbances and the effective
outlet condition where characteristics permit upstream influence. It also changes
which surface-pressure integrals contribute to loads. Extending a constant annulus
to the sleeve length would reproduce the wrong geometry.

**Act now:** carry the core-end datum and downstream surface extent into the 3D
geometry contract. Keep the two downstream taps out of the current annular-domain
validation. Assess a supported downstream-domain or effective-outlet model before
using downstream pressures to tune the annulus-exit boundary. Assembly clearance,
facility attachment and operating-state data remain required.

## 3. Near-inlet seat and local area changes: verify assembly soon

The sleeve contains a cylindrical seat of radius 40.0812 mm, compared with the
38.1 mm main bore. Under the inferred -4.445 mm axial shift, its axial support is
approximately 0–3.9624 mm. That is a 1.9812 mm radial enlargement in the sleeve
solid, but another assembled part may occupy it. The extraction deliberately
records it as surface evidence rather than a confirmed gas recess.

**Physical consequence if exposed to gas:** a step or pocket could change local
recirculation, hot-product residence and preheating. This remains conditional;
the magnitude and even the existence of an exposed cavity need assembly proof.

**Act now:** check injector/front-plate/sleeve mating surfaces and intersected
sections. Retain this as an unresolved near-inlet boundary feature. Do not insert
an assumed recirculation pocket into the current solver from a single-part view.

## 4. Hydraulic lengths and plenum volumes: extract after connectivity

The source contains feed passages, plenums and the process/finished injector
lineage. Hole axes and material volumes alone cannot determine connected gas
volumes, effective L/D, contraction edges or the separate feed paths. Split
cylindrical face intervals are not a hydraulic-length measurement.

**Physical consequence:** these features can change pressure losses, transient
injector response and coupling between chamber and feed system. They matter when
replacing constant reservoir conditions with a feed model. CAD does not determine
the appropriate discharge coefficient or recovery time.

**Act now:** reserve separate fields for fuel/oxygen connected volumes, entrance
and exit sections, passage lengths, contraction/edge geometry and boundary roles.
Populate them only after gas-cavity and connectivity checks; keep experimental feed
states and closure/calibration data separately sourced.

## 5. Ports, startup and diagnostics: distinguish holes from active boundaries

The sleeve has 24 candidate radial bores of diameter 3.2258 mm. With the provisional
registration their axis stations are 22.225, 34.925, 47.625, 60.325, 73.025, 85.725,
98.425 and 111.125 mm, three per station. CAD alone does not identify which are
plugged, instrumented or connected to the pre-detonator. Its +x clocking is not yet
registered to the paper's top-of-engine convention. The paper puts the 3.2 mm
pre-detonator port at z=73 mm and 210 degrees.

**Act now:** use the paper's active-port identities and measured clocking for
validation; map them to the assembled CAD before defining 3D boundary patches.
Keep pre-detonator geometry and its transient forcing separate. A drilled hole
does not specify igniter pressure history or energy. Port cavities/standoffs may
also matter for pressure measurement response; circumferential means are a
different diagnostic from local pressure taps.

## 6. Wall mechanics and heat transfer: geometry now, material/state data later

The reduction yields separate inner/outer wetted areas, actual radii, hydraulic
diameter and gas-volume estimate. These directly support the existing radial wall
closures and consistent load/torque integration. The long sleeve's outer material
radius is 50.7619 mm in the archived solid, but wall thickness must be evaluated
where surfaces overlap and local ports/steps remain present. Structural loading
needs the actual surfaces, attachments and time-dependent pressure field.

**Act now:** use measured radii/areas for geometric factors; retain wall surfaces
for subsequent thermal and structural adapters. Source material properties,
roughness, cooling, contact conditions and wall temperature independently. Do not
infer heat-transfer coefficients or structural allowables from STEP shape alone.

The immediate handoff is the injector and downstream geometry evidence, followed
by assembly verification of the inlet seat and active ports. This branch does not
modify physical closures being developed in the other solver branches.
