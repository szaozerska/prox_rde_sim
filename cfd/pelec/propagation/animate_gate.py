"""Animate actual planar verification profiles; never label them an RDE run."""

import argparse
from pathlib import Path
import numpy as np


def render(coarse, fine, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    a = np.load(coarse)
    b = np.load(fine)
    out.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True, layout="constrained")
    lines = []
    for ax, key, label in zip(
        axes,
        ["pressure_Pa", "heat_fraction"],
        ["Pressure (MPa)", "Chemical heat fraction relative to CJ"],
    ):
        lines.append(
            [
                ax.plot([], [], label="2 µm native mesh", color="#e69f00")[0],
                ax.plot([], [], label="1 µm native mesh", color="#0072b2")[0],
            ]
        )
        ax.set_ylabel(label)
        ax.grid(alpha=0.2)
        ax.legend(loc="upper left")
    axes[0].set_ylim(
        0, max(a["pressure_Pa"].max(), b["pressure_Pa"].max()) / 1e6 * 1.05
    )
    axes[1].set_ylim(
        -0.05, max(a["heat_fraction"].max(), b["heat_fraction"].max()) * 1.05
    )
    axes[1].set(xlim=(1.95, 2.9), xlabel="Planar propagation distance (mm)")
    markers = [ax.axvline(2.048, color="#666666", ls="--", lw=1) for ax in axes]
    title = fig.suptitle("")

    def update(i):
        t = b["time_s"][i]
        j = int(np.argmin(abs(a["time_s"] - t)))
        for k, key in enumerate(["pressure_Pa", "heat_fraction"]):
            factor = 1e-6 if key == "pressure_Pa" else 1.0
            lines[k][0].set_data(
                (a["x_m"] + float(a.get("frame_speed_mps", 0.0)) * a["time_s"][j])
                * 1000,
                a[key][j] * factor,
            )
            lines[k][1].set_data(
                (b["x_m"] + float(b.get("frame_speed_mps", 0.0)) * t) * 1000,
                b[key][i] * factor,
            )
            markers[k].set_xdata([2.048 + 2530.8130725897217 * t * 1000] * 2)
        title.set_text(
            f"Planar verification only — NOT a Run 937 engine simulation\nFine time {t * 1e6:.4f} µs; coarse time {a['time_s'][j] * 1e6:.4f} µs | dashed: steady CJ position"
        )
        return [*lines[0], *lines[1], *markers, title]

    update(len(b["time_s"]) - 1)
    fig.savefig(out / "planar_comparison.png", dpi=150)
    FuncAnimation(fig, update, frames=len(b["time_s"]), interval=150, blit=False).save(
        out / "planar_comparison.gif", writer=PillowWriter(fps=7)
    )
    plt.close(fig)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("coarse", type=Path)
    p.add_argument("fine", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    render(a.coarse, a.fine, a.output)
