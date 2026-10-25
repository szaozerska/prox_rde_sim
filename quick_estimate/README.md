# 2D Quick Estimate

**Experimental comparison warning:** this version misses all five tested annular
sustained-wave points from Mundt and also rejects a real deflagration point. The
coreless sixth geometry is unsupported. Do not use it as a validated wave-count
or sustain/fail predictor. See [the comparison](validation/README.md).

Offline algebraic wave-count screening, adapted from Fable's sizing code.
Python 3.9+ standard library only. No installation, chemistry integration or CFD.
Run from the repository root:

```sh
python3 -m quick_estimate quick_estimate/examples/synthetic.json
python3 -m quick_estimate quick_estimate/examples/law2021_design.json --out /tmp/law-estimate.json
python3 -m unittest discover -s quick_estimate/tests -v
```

Copy an example JSON and replace its inputs with your engine's values and source
notes. Use a new output filename for each run. JSON goes to stdout without `--out`;
a compact summary goes to stderr. The synthetic example has a nominal candidate
of **2 waves**. It is an arithmetic fixture, not a validated engine design.
The Law example deliberately preserves an unfavorable design-point estimate.

Read `nominal_candidate_wave_counts` first, then
`possible_candidate_wave_counts` and `checks`. `expected_wave_count` is null if
no unique nominal candidate exists. Refill capacity alone is not the expected
stable head count. All candidates remain conditional on the supplied assumptions.

See [THEORY.md](THEORY.md) for equations, units, empirical ranges, source lineage,
accuracy limits and verification. [VERIFICATION.md](VERIFICATION.md) records the
executed checks. This independent module leaves the CFD workflow unchanged.
