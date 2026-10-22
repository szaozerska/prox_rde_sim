# Modal client setup

The official Modal Python CLI is installed in `.tooling/modal-venv`, isolated
from the 2D environment. No Modal plugin was returned by the plugin catalog search.
This is a CLI connection, not a plugin installation. Client authentication has
been verified. An 8-core / 1 GiB CPU-only allocation and execution check passed;
A single H100 allocation/driver check also passed; solver execution remains pending.

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

## CPU access check

Run explicitly with `.tooling/modal-venv/bin/modal run --profile prox
--write-result /private/tmp/prox_rde_3d_modal_cpu_check.json
tools/modal/check_cpu.py` (one shell command). This creates a temporary job,
requests 8 CPU cores and 1 GiB RAM, requests no GPU, and limits function execution
to 30 seconds with no retries. Source automount is disabled; only the serialized
probe function is sent. Importing the script alone does not execute a remote job.

The October 22 check passed; saved evidence is in
`../../docs/verification/modal_cpu_access.json`. The remote environment reported
x86_64 and eight visible logical CPUs, but did not expose a CPU model or cgroup
limits at the probed paths. Do not infer a particular processor, maximum quota,
dedicated-node topology or MPI throughput from this check.


## GPU access check

Run `.tooling/modal-venv/bin/modal run --profile prox --write-result
/private/tmp/prox_rde_3d_modal_gpu_check.json tools/modal/check_gpu.py` as one
command. Requests one H100, two CPU cores and 2 GiB RAM for at most 30 function
seconds, no retries. Requires the expected single CUDA 9.0 device and records
actual device/driver/memory. Source automount is disabled. Saved evidence is in
`../../docs/verification/modal_gpu_access.json`. This is a hardware/driver check,
not a CUDA kernel or reacting-flow benchmark.
