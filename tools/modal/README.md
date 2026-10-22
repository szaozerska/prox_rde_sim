# Modal client setup

The official Modal Python CLI is installed in `.tooling/modal-venv`, isolated
from the 2D environment. No Modal plugin was returned by the plugin catalog search.
This is a CLI connection, not a plugin installation. Client authentication has
been verified; GPU allocation and solver execution have not yet been tested.

Reproduce this Intel macOS / Python 3.12 client environment from the repository root:

```sh
python3.12 -m venv .tooling/modal-venv
.tooling/modal-venv/bin/python -m pip install --upgrade pip
.tooling/modal-venv/bin/python -m pip install --only-binary=:all: -r tools/modal/client-requirements.txt
.tooling/modal-venv/bin/python -m pip check
.tooling/modal-venv/bin/modal token new
```

Complete authentication in the browser. The official CLI stores its credentials
outside this repository in the user's Modal configuration. Never copy credentials
into manifests, logs or commits. `modal profile list --json` checks profile names;
`modal billing rates --json` reads rates. Workspace settings do not expose GPU
allocation limits in the installed CLI. Listed rates do not establish capacity.

The first unbounded dependency install selected cbor2 6.1.5, which needed a Rust
compiler on this Intel Mac. Installing compatible prebuilt packages selected
cbor2 5.9.0; Modal 1.6.2 then installed and dependency checks passed. The pinned
client requirements record that working environment. They do not constrain the
future Linux/CUDA/PeleC container, which needs its own source/build pins.

See the G0-G5 gates in `../../first_sim_plan.md`. Start with a bounded single-GPU
hardware check before claiming GPU execution, memory, topology or scaling.
