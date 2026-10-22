# Pinned native solver environment

Installed on this Intel Mac: Colima 0.10.3, Lima 2.2.1, Docker CLI 29.9.2.
Dedicated profile: `rde3d`, two CPUs, 4 GiB RAM, 12 GiB data disk, 8 GiB root disk.
The original 2D checkout is not mounted. No login service was enabled.

Use `docker --context colima-rde3d ...` explicitly. If stopped, start the saved
profile with `colima start rde3d --activate=false --ssh-config=false`.

`source.lock.json` records the exact upstream revision and base-image digest.
The solver and all libraries built by upstream Allwmake were compiled without
source modifications. This Dockerfile chains each build with `&&`, so a failed
intermediate library cannot be hidden by a successful later command.

To rebuild from the repository root in a new build context:

```sh
mkdir -p .tooling/rebuild
git init .tooling/rebuild/detonationFoam
git -C .tooling/rebuild/detonationFoam fetch --depth 1 https://github.com/JieSun-pku/detonationFoam.git 4bd2e86003447fdb143b475f199c846146f754e3
git -C .tooling/rebuild/detonationFoam checkout --detach FETCH_HEAD
cp tools/openfoam/Dockerfile .tooling/rebuild/Dockerfile
cp tools/openfoam/foam-env.sh .tooling/rebuild/foam-env.sh
DOCKER_BUILDKIT=0 docker --context colima-rde3d build --build-arg OPENFOAM_IMAGE=openfoam/openfoam8-graphical-apps@sha256:1ccf8ef688f8757635a0c2361f53d1957ed84e3f5993d53da81a72abb760d9e0 -t prox-rde/detonationfoam:4bd2e86 .tooling/rebuild
```

The local verified build context is `.tooling/build`; both contexts and runs are
ignored by Git. Linux build sources/libraries stay inside the image, avoiding
macOS case-insensitive build-file collisions. Source pin and image ID are distinct:
the native runner records the actual image ID on every execution. The legacy
builder is used because this installation has the CLI without a buildx plugin.

With the existing Python environment (read-only dependencies), run the bounded
installation smoke in a new destination:

```sh
/Users/sgfx/Desktop/Projects/prox_rde_sim/.venv/bin/python -m rde3d.verify tutorial --source .tooling/build/detonationFoam/tutorials/1D_NH3_O2_cracking_0.3_detonation --out runs3d/new_install_smoke
```

This is a **tutorial-based installation check**, not a published-wave replication:
400 cells, both transverse directions empty, 2 ns, fixed 0.1 ns steps, reset fresh
mixture from the upstream end state and the supplied setFields hot patch. The
upstream initial files contain an advanced 20,000-cell profile. The absent optional
`libODE_DLB.so` entry is omitted; the built DLB chemistry library uses linked
OpenFOAM ODE. No chemistry model coefficients are fitted.

Require `Mesh OK.`, normal solver end, requested final time and finite required
fields. The x-position shock cutoff is set beyond the domain. Logs, per-command
input hashes, image ID and durations are retained even for failures. Existing
outputs are refused. Default wall timeout is 120 s per native command.

Known limitations: native adaptive stepping is convective-only; fixed steps are
used. Upstream species clipping still requires instrumentation before quantitative
chemistry validation. The smoke does not establish methane/oxygen chemistry,
spatial convergence, energy closure, sustained detonation or 3D RDE performance.
