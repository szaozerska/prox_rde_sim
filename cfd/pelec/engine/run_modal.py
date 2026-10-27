"""Bounded native engine runs, durable raw evidence and compact SI export."""

from pathlib import Path
import json
import os
import modal
from build_engine import build_engine

HERE = Path(__file__).resolve().parent
BASE_IMAGE = os.environ.get("RDE_ENGINE_BUILD_BASE_ID", "im-5VEDv2fncn7sbP6TlKcfHo")
image = (
    modal.Image.from_id(os.environ["RDE_ENGINE_IMAGE_ID"])
    if os.environ.get("RDE_ENGINE_IMAGE_ID")
    else (
        modal.Image.from_id(BASE_IMAGE)
        .add_local_dir(HERE / "native", "/opt/engine-native", copy=True)
        .add_local_file(HERE / "build_engine.py", "/root/build_engine.py", copy=True)
        .run_function(
            build_engine, cpu=16, memory=65536, timeout=3600, include_source=False
        )
        .pip_install("numpy==2.5.4", "cantera==3.2.0", "yt==4.4.3")
        .add_local_file(HERE / "export_fields.py", "/root/export_fields.py", copy=True)
    )
)
volume = modal.Volume.from_name("prox-rde-2d-engine", create_if_missing=True)
app = modal.App("prox-rde-2d-engine", include_source=False)


@app.function(
    image=image,
    serialized=True,
    gpu="H100!",
    cpu=8,
    memory=32768,
    timeout=14400,
    retries=0,
    max_containers=2,
    volumes={"/evidence": volume},
)
def run(
    case: dict, profile: str, run_id: str, stop: float, wall_limit: int, dt: float = 0.0
):
    import base64
    import hashlib
    import io
    import json
    import re
    import shutil
    import subprocess
    import tarfile
    import time
    from pathlib import Path

    if not re.fullmatch(r"[a-zA-Z0-9_-]+", run_id):
        raise ValueError("Run id")
    if not 0 < stop <= 0.001 or not 30 <= wall_limit <= 12600 or not 0 <= dt <= 1e-7:
        raise ValueError("Outside run envelope")
    if case["nx"] * case["ny"] > 600000 or case["nx"] % 8 or case["ny"] % 8:
        raise ValueError("Outside grid envelope")
    if hashlib.sha256(profile.encode()).hexdigest() != case["profile_sha256"]:
        raise ValueError("Profile checksum")
    root = Path("/evidence") / run_id
    root.mkdir(exist_ok=False)
    case = dict(case, requested_stop_s=stop)
    (root / "case.json").write_text(json.dumps(case, indent=2) + "\n")
    (root / "profile.dat").write_text(profile)
    meta = json.loads(Path("/opt/pelec-engine-build/manifest.json").read_text())
    if not meta.get("device_assertions_enabled"):
        raise ValueError("Engine GPU assertions must be enabled")
    exe = Path("/opt/PeleC/build-2d/Exec/RegTests/Engine2D/PeleC-Engine2D")
    if hashlib.sha256(exe.read_bytes()).hexdigest() != meta["executable_sha256"]:
        raise ValueError("Executable changed")
    shutil.copytree("/opt/pelec-engine-build", root / "build")
    hydro = case.get("hydro_method", "mol")
    if hydro not in ("mol", "godunov"):
        raise ValueError("Unknown hydro method")
    inputs = f"""stop_time = {stop}
max_step = 1000000
geometry.is_periodic = 1 0
geometry.coord_sys = 0
geometry.prob_lo = 0 0
geometry.prob_hi = {case["circumference_m"] * 100} {case["length_m"] * 100}
amr.n_cell = {case["nx"]} {case["ny"]}
amr.max_level = 0
amr.blocking_factor = 8
amr.max_grid_size = 128
amr.checkpoint_files_output = 1
amr.check_file = chk
amr.check_int = 1000
amr.plot_files_output = 1
amr.plot_file = plt
amr.plot_int = 100000000
amr.plot_per = {min(case["plot_interval_s"], stop / 5)}
amr.plot_vars = density rho_E Temp heatRelease
amr.derive_plot_vars = pressure x_velocity y_velocity soundspeed
pelec.plot_massfrac = 1
pelec.plot_rhoy = 0
pelec.plot_reactions = 1
amr.data_log = datlog
pelec.lo_bc = Interior UserBC
pelec.hi_bc = Interior UserBC
pelec.do_hydro = 1
pelec.do_react = 1
pelec.do_mol = {int(hydro == "mol")}
pelec.use_laxf_flux = {int(hydro == "mol")}
pelec.mol_iters = {case.get("mol_iters", 1)}
pelec.mol_iorder = 1
pelec.ppm_type = 0
pelec.plm_iorder = 1
pelec.sdc_iters = {case.get("sdc_iters",2)}
pelec.dual_energy_update_E_from_e = 0
pelec.diffuse_temp = 0
pelec.diffuse_enth = 0
pelec.diffuse_spec = 0
pelec.diffuse_vel = 0
pelec.chem_integrator = ReactorCvode
cvode.solve_type = GMRES
cvode.max_order = {case.get("cvode_max_order", 5)}
ode.rtol = 1e-9
ode.atol = 1e-18
pelec.cfl = 0.1
pelec.init_shrink = 0.1
pelec.max_dt = 5e-8
pelec.dt_cutoff = 1e-20
pelec.sum_interval = 20
pelec.v = 1
amr.v = 1
amrex.abort_on_unused_inputs = 1
amrex.signal_handling = 0
prob.profile = profile.dat
prob.species_floor = {case.get("species_floor",-1e-12)}
prob.uniform_control = {int(case["uniform_control"])}
prob.fill = {case["fill_m"] * 100}
prob.p0 = {case["p0_Pa"] * 10}
prob.T0 = {case["T0_K"]}
prob.area = {case["area_ratio_effective"]}
prob.pback = {case["pback_Pa"] * 10}
prob.R = {case["R_JkgK"] * 1e4}
prob.gamma = {case["gamma"]}
prob.bg_T = {case["bg_T"]}
prob.freshY = {" ".join(map(str, case["freshY"]))}
prob.bgY = {" ".join(map(str, case["bgY"]))}
prob.element_weights = {" ".join(map(str, case["element_weights"]))}
prob.elements = {" ".join(map(str, case["elements"]))}
"""
    if dt:
        inputs += f"pelec.fixed_dt = {dt}\n"
    (root / "inputs").write_text(inputs)
    start = time.monotonic()
    last_print = 0
    with (root / "solver.log").open("w") as log:
        proc = subprocess.Popen(
            [str(exe), "inputs"], cwd=root, stdout=log, stderr=subprocess.STDOUT
        )
        while proc.poll() is None:
            elapsed = time.monotonic() - start
            if elapsed > wall_limit:
                proc.terminate()
                time.sleep(2)
                proc.kill() if proc.poll() is None else None
                break
            if elapsed - last_print > 30:
                log.flush()
                with (root / "solver.log").open("rb") as progress:
                    progress.seek(max(0, progress.seek(0, 2) - 12000))
                    text = progress.read().decode(errors="replace")
                steps = re.findall(r"STEP = (\d+) TIME = (\S+) DT = (\S+)", text)
                if steps:
                    print(
                        dict(
                            run=run_id,
                            wall_seconds=round(elapsed),
                            step=steps[-1][0],
                            time_s=steps[-1][1],
                        ),
                        flush=True,
                    )
                last_print = elapsed
            time.sleep(2)
        code = proc.wait()
    record = dict(
        returncode=code,
        wall_seconds=time.monotonic() - start,
        run_id=run_id,
        volume="prox-rde-2d-engine",
        target_time_s=stop,
        interpretation="Exploratory native 2D engine; independent physical validation remains open",
    )
    (root / "execution.json").write_text(json.dumps(record, indent=2) + "\n")
    volume.commit()
    from export_fields import export_fields

    try:
        record.update(export_fields(root, root / "export"))
    except Exception as exc:
        record.update(export_error=str(exc), valid_snapshots=False)
    record["completed"] = bool(
        code == 0
        and record.get("valid_snapshots")
        and abs(record.get("last_time_s", 0) - stop) < 1e-12
    )
    (root / "execution.json").write_text(json.dumps(record, indent=2) + "\n")
    volume.commit()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name in (
            "case.json",
            "inputs",
            "execution.json",
            "solver.log",
            "build",
            "export",
        ):
            if (root / name).exists():
                tar.add(root / name, arcname=name)
    raw = stream.getvalue()
    return dict(
        record,
        artifact_sha256=hashlib.sha256(raw).hexdigest(),
        data=base64.b64encode(raw).decode(),
    )


@app.local_entrypoint()
def main(
    case_file: str,
    profile_file: str,
    output: str,
    stop: float = 0.001,
    wall_limit: int = 7200,
    dt: float = 0.0,
):
    import base64
    import hashlib

    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=False)
    call = run.spawn(
        json.loads(Path(case_file).read_text()),
        Path(profile_file).read_text(),
        dest.name,
        stop,
        wall_limit,
        dt,
    )
    (dest / "call.json").write_text(json.dumps(dict(id=call.object_id)) + "\n")
    try:
        r = call.get(timeout=wall_limit + 1500)
    except BaseException:
        call.cancel()
        raise
    raw = base64.b64decode(r.pop("data"))
    assert hashlib.sha256(raw).hexdigest() == r["artifact_sha256"]
    (dest / "results.tar.gz").write_bytes(raw)
    (dest / "status.json").write_text(json.dumps(r, indent=2) + "\n")
    print(r)
    if not r["completed"]:
        raise RuntimeError(
            "Run did not complete valid requested window; evidence retained"
        )
