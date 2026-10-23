# Longer observation of the existing directional startup

October 22, 2026. User-requested extension to inspect later propagation. This is
a time extension of the existing model, not implementation of the finite
pre-detonator discharge or radial wave reflections in revision 20. RDE-001 OPEN.

## Protocol fixed before completion

Continue the accepted 40 us, step-2780 checkpoint to the original three-reference-
passage cap: 189.393939 us total, about 1.5 experimental reference revolutions.
Use unchanged startup, chemistry, mesh, feed, walls and saved 2 us field cadence.
This reference duration does not impose a wave speed or claim a simulated passage.
Review fields before deciding whether the optional five-passage cap is useful.
Stop on invalid states or a numerical failure. A valid but weakening wave is
still informative within this specifically requested later-observation window.

Preserve the original `runs/directional_startup_40us` and its published hashes.
The continuation is `runs/directional_startup_extended`, initially a byte-identical
copy, with its lineage in `continuation.json`. The original native status remains
`failed` from the documented SIGINT/Numba interruption after 40 us. No original
field or status is rewritten. All eight fingerprinted source files match commit
`411a895`; Python and numerical package versions also match. Only the present
checkout's `run.py` differs, because of the later interruption fix.

Run with the exact archived source under `/tmp/rde-directional-source-411a895`
and the same project virtualenv; do not bypass the restart guard or alter its
manifest. The archived source is extracted from Git, not a branch change or an
edit of the current main checkout. Native checkpoint loading checks state,
schedules and input hash before advancement. The bounded run finishes normally,
without the deliberate SIGINT used in the earlier 40 us experiment.

[Provenance](directional_extension_provenance.json) records the source commit,
parent/copied files and hashes. The raw [run log](directional_extension_run.txt)
is retained. A first read-only attempt to import the current runner hit Numba's
cache-write restriction in the sandbox, before opening/advancing any run. The
source/environment audit then used direct hashes; execution uses the authorized
writable archive and output directory. No numerical setting was changed.

## Inspection and acceptance

Use saved pressure and reaction together at z approximately 0.75, 3.8 and 8 mm.
Retain peaks and reaction maxima within +/-2, 4 and 8 mm; map the entire ring over
time so trailing reaction cannot be mistaken for reaction at the leading shock.
Candidate tracking breaks at ambiguous matches/dropouts and is not a detonation
classifier. Check pressure peaks against local reactions and visual structure,
not pressure travel alone. No automated claim of sustained detonation or permanent
extinction follows from a finite window.

After completion, verify native history/checkpoint consistency, all original
field hashes, the unchanged original run, preserved history prefix, zero invalid
states and integrated mass/energy/momentum closure. Render both flat and wrapped
pressure/reaction GIFs from every saved field and inspect representative frames.
The wrapped view has no resolved radial degree of freedom.

No new solver implementation means a full repeated unit suite is not required
for this extension. Native validity/budget/prefix checks and artifact verification
are the applicable checks. Record measured outcomes here before committing.

Restart recovery preserved the original 16,711-byte history tail after the 40 us
checkpoint in the continuation's `recovery/` directory. Prefix verification uses
the checkpoint's committed byte offset (5,773,835), not the original file's EOF.
The original run and its full file remain untouched. The continuation reproduces
advancement from the coherent checkpoint; tail rows are not treated as committed.

## Completed results

The continuation completed normally at **189.393939 us**, step **13,165**:
10,385 additional accepted steps after the preserved 40 us checkpoint, in
480.02 seconds (8.0 minutes) for this invocation. All 96 saved frames are used.
Zero invalid states; the independent native history reduction closes mass,
momentum and energy with maximum scaled residual **7.01e-14**, below its 1e-10
acceptance tolerance. The original run/files, all 21 original field hashes,
unchanged inputs, committed history prefix and preserved recovery tail pass.

| Saved time, us | Maximum pressure at z=0.751974 mm, MPa | Maximum reaction anywhere on that ring, 1/s |
|---:|---:|---:|
| 40 | 2.56288 | 837.375 |
| 80 | 1.55059 | 0.600865 |
| 120 | 0.963000 | 0.0320755 |
| 160 | 0.549868 | 0.0112157 |
| 189.394 | 0.418147 | 0.0120273 |

These are separate ring maxima, not necessarily colocated. The earlier audit's
near-leading-peak rate at 40 us was only 7.08923/s: the larger 837.375/s maximum
was farther behind. Pressure motion persists after strong near-injector reaction
has faded. The longer window does not show recovery of sustained shock-coupled
rotation. The lower-ring pressure-candidate track from 4–128 us covers about
122 mm; it is not a completed detonation revolution. Tracks end when their
threshold or matching conditions fail, not at a physically determined extinction
time. Their fitted speed is not a validated detonation velocity.

The 3.75987 mm ring maximum reaction is 0.00372612/s at the endpoint, and the
7.77039 mm ring maximum is 0.690931/s. Whole-domain maximum reaction remains
88,295.6/s, so complete chamber extinction is not claimed. Reaction higher in the
chamber must not be confused with a sustained near-injector detonation.

Fresh-mixture inventory rises from **15.0175 to 45.8275 mg**, with **48.9811 mg**
of mixture injected during the whole window. Global fuel exhaustion is again
excluded. This does not prove correct local mixing/refill or explain the cause
of coupling loss. The finite discharge and cross-gap reflections remain absent.

The three-passage observation was sufficient to see substantial decay without
late near-injector recovery. The optional 315.657 us cap was not launched; a longer
unchanged run is not supported merely to wait for a visually satisfying result.
This finite window does not exclude every possible later reinitiation.

Artifacts: [pressure/reaction space-time plots](directional_extension/space_time.png),
[metrics and hashes](directional_extension/metrics.json),
[unwrapped GIF](directional_extension/gifs/unwrapped.gif),
[wrapped GIF](directional_extension/gifs/wrapped.gif).
Both animations show this continued directional case, not the old hot-patch case.
All saved frames are used, with time-fixed scales computed over the full window.
Compare numerical labels/scales when comparing with an earlier shorter-window GIF.
The end is the configured limit, not an exhaustion/extinction detector.

Final artifact QA: both GIFs contain all 96 verified fields, play for 15.5 s
including the final hold, and have no looping extension. Encoded frame counts,
durations, output hashes and native frame identities agree with the manifest.
Pressure/reaction color limits are exactly unchanged from the earlier 0–40 us
GIFs. Midpoint/endpoint PNGs and the space-time map were visually inspected; local
documentation links, script hash/syntax and whitespace checks pass. No new solver
unit tests were required because this increment changes no solver code.
