"""Build only the native engine problem against the previously pinned source."""


def build_engine():
    import hashlib
    import json
    import shutil
    import subprocess
    import time
    from pathlib import Path

    root = Path("/opt/PeleC")
    out = Path("/opt/pelec-engine-build")
    out.mkdir(exist_ok=True)
    prior = json.loads(Path("/opt/pelec-propagation-build/manifest.json").read_text())
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    if actual != prior["pelec_commit"]:
        raise ValueError("Wrong cached upstream")
    for name, value in prior["mechanism_sha256"].items():
        if (
            hashlib.sha256(
                (
                    root / "Submodules/PelePhysics/Mechanisms/FFCM1_Red" / name
                ).read_bytes()
            ).hexdigest()
            != value
        ):
            raise ValueError("Mechanism changed")
    shutil.copytree(
        "/opt/engine-native", root / "Exec/RegTests/Engine2D", dirs_exist_ok=True
    )
    p = root / "Exec/RegTests/CMakeLists.txt"
    if "add_subdirectory(Engine2D)" not in p.read_text():
        p.write_text(p.read_text() + "\nadd_subdirectory(Engine2D)\n")
    start = time.monotonic()
    for name, args in [
        (
            "configure",
            [
                "cmake",
                "-S",
                str(root),
                "-B",
                str(root / "build-2d"),
            ],
        ),
        (
            "build",
            [
                "cmake",
                "--build",
                str(root / "build-2d"),
                "--target",
                "PeleC-Engine2D",
                "-j",
                "8",
            ],
        ),
    ]:
        with (out / (name + ".log")).open("w") as log:
            r = subprocess.run(
                args, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=2400
            )
        if r.returncode:
            print((out / (name + ".log")).read_text()[-14000:], flush=True)
            raise RuntimeError(name + " failed")
    exe = root / "build-2d/Exec/RegTests/Engine2D/PeleC-Engine2D"
    manifest = dict(
        upstream=prior,
        seconds=time.monotonic() - start,
        executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
        problem_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("/opt/engine-native").iterdir()
            if p.is_file()
        },
        numerical_source_patches=[],
        device_assertions_enabled=True,
        guard_implementation="unconditional CUDA trap; independent of NDEBUG",
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Native Engine2D built", flush=True)
