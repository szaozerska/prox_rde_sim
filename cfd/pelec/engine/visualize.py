"""Timed native-field animations: unwrapped diagnostics and cylindrical display.

The cylinder is a coordinate mapping of a 2D solution, never a 3D computation.
Input SI NPZ contains time_s, x_m, y_m, pressure_Pa, density_kg_m3,
heat_release_W_m3, u_mps, v_mps. No interpolated or fabricated simulation frames.
"""

import argparse
import json
from pathlib import Path
import numpy as np


def validate(data):
    t = data["time_s"]
    x = data["x_m"]
    y = data["y_m"]
    shape = (len(t), len(x), len(y))
    if len(t) < 2 or not np.isfinite(t).all() or not np.all(np.diff(t) > 0):
        raise ValueError("Invalid time history")
    if (
        len(x) < 3
        or len(y) < 3
        or not np.isfinite(x).all()
        or not np.isfinite(y).all()
        or not np.all(np.diff(x) > 0)
        or not np.all(np.diff(y) > 0)
    ):
        raise ValueError("Invalid coordinates")
    for axis in (x, y):
        if not np.allclose(np.diff(axis), axis[1] - axis[0], rtol=1e-8, atol=1e-15):
            raise ValueError("Uniform grid required")
    for name in ("pressure_Pa", "density_kg_m3", "heat_release_W_m3", "u_mps", "v_mps"):
        if data[name].shape != shape or not np.isfinite(data[name]).all():
            raise ValueError("Invalid native field: " + name)
    if np.min(data["pressure_Pa"]) <= 0 or np.min(data["density_kg_m3"]) <= 0:
        raise ValueError("Nonphysical fields")


def render(path, output, title, max_frames=240):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.colors import Normalize, SymLogNorm

    if max_frames < 2:
        raise ValueError("At least two animation frames required")
    data = np.load(path)
    validate(data)
    output.mkdir(parents=True, exist_ok=False)
    t = data["time_s"]
    x = data["x_m"]
    y = data["y_m"]
    dx = float(np.mean(np.diff(x)))
    dy = float(np.mean(np.diff(y)))
    ids = np.unique(
        np.rint(np.linspace(0, len(t) - 1, min(max_frames, len(t)))).astype(int)
    )
    rho = data["density_kg_m3"]
    u = data["u_mps"]
    v = data["v_mps"]
    # Periodic circumferential derivatives; one-sided axial edge gradients.
    drx = (np.roll(rho, -1, axis=1) - np.roll(rho, 1, axis=1)) / (2 * dx)
    dry = np.gradient(rho, dy, axis=2)
    sch = np.hypot(drx, dry) / rho
    vort = (np.roll(v, -1, axis=1) - np.roll(v, 1, axis=1)) / (2 * dx) - np.gradient(
        u, dy, axis=2
    )
    pressure = data["pressure_Pa"] / 1e6
    heat = data["heat_release_W_m3"]
    fields = [pressure, heat, sch, vort]
    limits = [float(np.max(abs(a))) for a in fields]
    norms = [
        Normalize(0, limits[0]),
        SymLogNorm(
            max(limits[1] * 1e-4, 1.0),
            vmin=-max(limits[1], 1.0),
            vmax=max(limits[1], 1.0),
        ),
        Normalize(0, max(np.quantile(sch, 0.999), 1.0)),
        SymLogNorm(
            max(limits[3] * 1e-3, 1.0), vmin=-max(limits[3], 1), vmax=max(limits[3], 1)
        ),
    ]
    cmaps = ["inferno", "coolwarm", "gray_r", "RdBu_r"]
    labels = [
        "Pressure (MPa)",
        "Native heat release (W/m³)",
        "Numerical schlieren |∇ρ|/ρ (1/m)",
        "Vorticity (1/s); shear/contact candidates",
    ]
    extent = [
        (x[0] - dx / 2) * 1000,
        (x[-1] + dx / 2) * 1000,
        (y[0] - dy / 2) * 1000,
        (y[-1] + dy / 2) * 1000,
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout="constrained")
    images = []
    for ax, field, norm, cmap, label in zip(axes.flat, fields, norms, cmaps, labels):
        im = ax.imshow(
            field[0].T,
            origin="lower",
            extent=extent,
            aspect="auto",
            norm=norm,
            cmap=cmap,
        )
        images.append(im)
        fig.colorbar(im, ax=ax, label=label)
        ax.set(
            xlabel="Circumferential distance (mm) → +θ", ylabel="Axial distance (mm)"
        )
    heading = fig.suptitle("")

    def update(k):
        i = ids[k]
        for im, a in zip(images, fields):
            im.set_data(a[i].T)
        heading.set_text(
            f"{title} | t = {t[i] * 1e3:.4f} ms\nNative 2D fields; feed at bottom, outlet at top; fixed color scales"
        )
        return images + [heading]

    update(0)
    fig.savefig(output / "unwrapped_first.png", dpi=130)
    FuncAnimation(fig, update, frames=len(ids), interval=65, blit=False).save(
        output / "unwrapped.gif", writer=PillowWriter(fps=15)
    )
    plt.close(fig)
    # Show pressure and schlieren on the same cylindrical mapping with a fixed seam.
    ix = np.unique(np.rint(np.linspace(0, len(x) - 1, min(96, len(x)))).astype(int))
    iy = np.unique(np.rint(np.linspace(0, len(y) - 1, min(48, len(y)))).astype(int))
    length = len(x) * dx
    radius = length / (2 * np.pi)
    theta = 2 * np.pi * x[ix] / length
    X = np.cos(theta)[:, None] * radius * 1000 * np.ones((1, len(iy)))
    Y = np.sin(theta)[:, None] * radius * 1000 * np.ones((1, len(iy)))
    Z = np.ones((len(ix), 1)) * y[iy][None, :] * 1000
    fig = plt.figure(figsize=(11, 6), layout="constrained")
    axes = [
        fig.add_subplot(121, projection="3d"),
        fig.add_subplot(122, projection="3d"),
    ]
    for ax, label in zip(axes, ["Pressure", "Numerical schlieren"]):
        ax.set(
            xlim=(-radius * 1000, radius * 1000),
            ylim=(-radius * 1000, radius * 1000),
            zlim=(0, (y[-1] + dy / 2) * 1000),
            xlabel="x (mm)",
            ylabel="y (mm)",
            zlabel="Axial distance (mm)",
            title=label,
        )
        ax.set_box_aspect((2 * radius, 2 * radius, len(y) * dy))
        ax.view_init(elev=18, azim=-55)
    surfaces = []
    heading = fig.suptitle("")

    def wrap(k):
        for s in surfaces:
            s.remove()
        surfaces.clear()
        i = ids[k]
        for ax, a, norm, cmap in zip(
            axes, [pressure, sch], [norms[0], norms[2]], ["inferno", "gray_r"]
        ):
            colors = plt.get_cmap(cmap)(norm(a[i][np.ix_(ix, iy)]))
            surfaces.append(
                ax.plot_surface(
                    X,
                    Y,
                    Z,
                    facecolors=colors,
                    rcount=len(ix),
                    ccount=len(iy),
                    shade=False,
                    linewidth=0,
                    antialiased=False,
                )
            )
        heading.set_text(
            f"{title} | t = {t[i] * 1e3:.4f} ms\nCylindrical mapping of the 2D solution — not a 3D simulation"
        )
        return surfaces + [heading]

    wrap(0)
    fig.savefig(output / "wrapped_first.png", dpi=130)
    FuncAnimation(fig, wrap, frames=len(ids), interval=65, blit=False).save(
        output / "wrapped.gif", writer=PillowWriter(fps=15)
    )
    plt.close(fig)
    (output / "animation_manifest.json").write_text(
        json.dumps(
            dict(
                source=str(path.resolve()),
                selected_frame_indices=ids.tolist(),
                time_s=t[ids].tolist(),
                frames=len(ids),
                fps=15,
                interpretation="Actual saved native fields; no synthetic evolution. Cylinder is a 2D mapping. Vorticity does not uniquely identify a slip line.",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("fields", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--max-frames", type=int, default=240)
    a = p.parse_args()
    render(a.fields, a.output, a.title, a.max_frames)
