# F2: explicit reduced-case and result contracts

The supported manual constant annulus now has a versioned SI manifest: source
units/hash, dimensions, areas, coordinates, named boundaries and omissions. Saved
inputs include physical/feed references separately from numerical settings, the
backend's capabilities, native field units/location and energy conventions.
The shared contract does not require other backends to use this solver's arrays.

`run.py --preflight --case config.yaml --calibration calib.json` checks the actual
case/calibration/initializer and prints this manifest without advancing CFD or
creating a run directory. It allocates the proposed initial mesh, so this is a
construction check, not a zero-memory schema linter. The real run path also
rejects CAD/nonuniform/unknown geometry fields and coreless geometry; unsupported
geometry cannot be silently reduced. Native snapshot iteration validates fields
and reads one committed snapshot at a time. No CAD importer is claimed.

Review 1 found that an unused schema would not enforce backend restrictions;
validation is called by `resolve_case`. Review 2 kept source references and
reduced feed distinct, with explicit omitted jets/nozzle/predetonator. Review 3
added corrupted snapshot, uncommitted-tail and no-output CLI checks, rather than
only testing manifest dictionary contents.

Verification: 98 existing tests passed (one opt-in skipped), plus all four new contract tests passed: 102 distinct passing tests; see
[f2_tests.txt](f2_tests.txt) and [f2_contract_tests.txt](f2_contract_tests.txt).
The full suite began discovery before the new test file existed; therefore the
four contract tests were run separately, not counted twice. Counts/results are
recorded in those logs. No new engine propagation study was launched.

Changing the runner and its fingerprint means old checkpoints remain analyzable
but cannot be resumed with the changed source. Use their original git revision
and environment for exact restarts. The native format stays at version 2; the
new contracts are additive version-1 metadata.
