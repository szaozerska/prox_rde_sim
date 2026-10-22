# SDToolbox source used by the optional physical reference

`sdtoolbox/` contains unmodified Python files and the BSD 3-clause license from
https://shepherd.caltech.edu/EDL/PublicResources/sdt/SDToolbox.zip . Retrieved
October 22, 2026. The Python headers identify the April 2026 update; the website's
download label is older. `sdtoolbox_provenance.json` records archive/file SHA256.
Original line endings and whitespace are preserved for source verification.

The public `reference.py` driver verifies those hashes before loading this
package. It uses bounded minimization of upstream `CJ_calc` and a checked SciPy
integrator for upstream `ZNDSys`. It does not use the unbounded outer `CJspeed`
fit loop or rely on the upstream convenience ZND driver's implicit completion.
No upstream mathematical source was edited. The independent driver records its
algorithm, tolerances, termination, warnings and conservation/sonic checks.

Cantera is optional: install the pinned packages in `requirements-reference.txt`
using the root README instructions. Rendering existing results and running the
CFD regression suite do not require Cantera. Importing `reference.py` does not
load this vendor package (whose own imports include Matplotlib).
