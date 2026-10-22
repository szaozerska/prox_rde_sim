# Methane closed-reactor verification case

This overlay supplies only explicit initial pressure (cgs), temperature and mass
fractions to the pinned upstream `zeroD` case. `prob.H`, native EOS, chemistry,
CVODE and field evolution remain upstream. The builder records all overlay hashes.
Required inputs fail on invalid species count, negative/nonfinite fractions or
nonunit sum; there is no implicit hydrogen composition or normalization.

The experimental GRI polynomial-consistency build changes two inverse-temperature
upper bounds from 3000 to 5000 K. This is explicit in the build manifest; it changes
no reaction rates or thermodynamic coefficients. It **does not extend published
thermodynamic validity**. Numerical tests of this declared law are separate from
physical validation. It is not an accepted sustained-detonation engine model.
