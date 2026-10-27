"""Bounded 2D native GPU propagation gate; no long engine launch on failure."""

from pathlib import Path
import json
import os
import modal
from build_propagation import build_propagation

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT / "source_lock.json").read_text())
image = modal.Image.from_id(os.environ["RDE_PELEC_IMAGE_ID"]) if os.environ.get("RDE_PELEC_IMAGE_ID") else (
    modal.Image.from_registry(LOCK["cuda_image"], add_python="3.12")
    .apt_install("git", "build-essential", "cmake", "ninja-build")
    .add_local_dir(ROOT / "native", "/opt/adapter/native", copy=True)
    .add_local_file(
        ROOT / "build_propagation.py", "/root/build_propagation.py", copy=True
    )
    .run_function(
        build_propagation,
        kwargs={"lock": LOCK},
        cpu=16,
        memory=65536,
        timeout=3600,
        include_source=False,
    )
)
app = modal.App("prox-rde-2d-propagation", include_source=False)


@app.function(
    image=image,
    serialized=True,
    gpu="H100!",
    cpu=4,
    memory=16384,
    timeout=2000,
    retries=0,
    max_containers=1,
)
def run(case: dict, profile: str, dt: float):
    import base64
    import hashlib
    import io
    import json
    import subprocess
    import tarfile
    import time
    from pathlib import Path

    if hashlib.sha256(profile.encode()).hexdigest() != case["profile_sha256"]:
        raise ValueError("Profile mismatch")
    if (
        case["nx"] not in (512, 1024, 2048, 4096)
        or not 0 < dt <= case["dx_m"] / 20000 * (1 + 1e-12)
        or case.get("reconstruction_order", 2) not in (1, 2)
    ):
        raise ValueError("Outside bounded gate")
    if (
        case.get("hydro_method", "godunov") not in ("godunov", "mol")
        or not 0 < case["final_time_s"] <= 2e-7
    ):
        raise ValueError("Invalid bounded case")
    if type(case.get("reacting", True)) is not bool or type(case.get("use_laxf_flux", False)) is not bool:
        raise ValueError("Physics switches must be explicit booleans")
    if case.get("use_laxf_flux", False) and case.get("hydro_method") != "mol":
        raise ValueError("This flux comparison requires MOL")
    expected = json.loads(Path("/opt/pelec-propagation-build/manifest.json").read_text())
    exe = Path("/opt/PeleC/build-2d/Exec/RegTests/Propagation2D/PeleC-Propagation2D")
    if hashlib.sha256(exe.read_bytes()).hexdigest() != expected["executable_sha256"]:
        raise ValueError("Cached executable mismatch")
    root = Path("/tmp/gate")
    root.mkdir()
    (root / "profile.dat").write_text(profile)
    (root / "case.json").write_text(json.dumps(case, indent=2) + "\n")
    text = f"""stop_time = {case["final_time_s"]}
max_step = 20000
geometry.is_periodic = 0 1
geometry.coord_sys = 0
geometry.prob_lo = 0 0
geometry.prob_hi = {case["length_m"] * 100} {case["dx_m"] * 800}
amr.n_cell = {case["nx"]} 8
amr.max_level = 0
amr.blocking_factor = 8
amr.max_grid_size = 128
amr.checkpoint_files_output = 0
amr.plot_files_output = 1
amr.plot_file = plt
amr.plot_int = 1000000
amr.plot_per = {case["plot_interval_s"]}
amr.plot_vars = density rho_E Temp
amr.derive_plot_vars = pressure x_velocity y_velocity soundspeed
pelec.plot_massfrac = 1
pelec.plot_rhoy = 0
pelec.plot_reactions = 1
amr.data_log = datlog
pelec.lo_bc = FOExtrap Interior
pelec.hi_bc = FOExtrap Interior
pelec.do_hydro = 1
pelec.do_react = {int(case.get("reacting", True))}
pelec.use_laxf_flux = {int(case.get("use_laxf_flux", False))}
pelec.do_mol = {int(case.get("hydro_method", "godunov") == "mol")}
pelec.mol_iters = 1
pelec.mol_iorder = {case.get("reconstruction_order", 2)}
pelec.sdc_iters = 2
pelec.plm_iorder = {case.get("reconstruction_order", 2)}
pelec.dual_energy_update_E_from_e = 0
pelec.diffuse_temp = 0
pelec.diffuse_enth = 0
pelec.diffuse_spec = 0
pelec.diffuse_vel = 0
pelec.chem_integrator = ReactorCvode
cvode.solve_type = GMRES
cvode.max_order = 5
ode.rtol = 1e-9
ode.atol = 1e-18
pelec.fixed_dt = {dt}
pelec.init_shrink = 1
pelec.cfl = 0.2
pelec.dt_cutoff = 1e-20
pelec.sum_interval = 1
pelec.v = 1
amr.v = 1
prob.profile = profile.dat
amrex.abort_on_unused_inputs = 1
amrex.signal_handling = 0
"""
    if not case.get("reacting", True):
        text = "\n".join(line for line in text.splitlines() if not line.startswith(("cvode.", "ode."))) + "\n"
    (root / "inputs").write_text(text)
    start = time.monotonic()
    with (root / "solver.log").open("w") as log:
        try:
            code = subprocess.run(
                [
                    "/opt/PeleC/build-2d/Exec/RegTests/Propagation2D/PeleC-Propagation2D",
                    "inputs",
                ],
                cwd=root,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=1800,
            ).returncode
        except subprocess.TimeoutExpired:
            code = 124
    record = dict(
        returncode=code,
        wall_seconds=time.monotonic() - start,
        dt=dt,
        interpretation="Execution only; requires independent gate",
    )
    (root / "execution.json").write_text(json.dumps(record, indent=2) + "\n")
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as tar:
        tar.add(root, arcname="run")
        tar.add("/opt/pelec-propagation-build", arcname="build")
        tar.add(
            "/opt/PeleC/Submodules/PelePhysics/Mechanisms/FFCM1_Red/mechanism.yaml",
            arcname="mechanism.yaml",
        )
    raw = stream.getvalue()
    return dict(
        record,
        artifact_sha256=hashlib.sha256(raw).hexdigest(),
        data=base64.b64encode(raw).decode(),
    )


@app.local_entrypoint()
def main(case_file: str, profile_file: str, output: str, dt: float = 2e-10):
    import base64
    import hashlib

    p = Path(output)
    if p.exists():
        raise FileExistsError("New output directory required")
    p.mkdir(parents=True)
    call = run.spawn(
        json.loads(Path(case_file).read_text()), Path(profile_file).read_text(), dt
    )
    (p / "call.json").write_text(json.dumps({"id": call.object_id}) + "\n")
    try:
        result = call.get(timeout=2200)
    except BaseException:
        call.cancel()
        raise
    raw = base64.b64decode(result.pop("data"))
    if hashlib.sha256(raw).hexdigest() != result["artifact_sha256"]:
        raise ValueError("Archive mismatch")
    (p / "native.tar.gz").write_bytes(raw)
    (p / "status.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result)
    if result["returncode"]:
        raise RuntimeError("Native gate failed; evidence saved")
