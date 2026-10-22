"""Legacy one-case runner, now safe to import.

The short-run input/output/restart workflow is not implemented yet. Do not use
this entry point for production claims: see HANDOFF.md for remaining blockers.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np
import yaml
from solver import Solver, NG, PERIODIC, INJECTOR, OUTFLOW


HERE = Path(__file__).resolve().parent


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dx", type=float, default=None, help="cell size [mm]")
    ap.add_argument("--cd", type=float, default=0.76, help="injector discharge coefficient (D25)")
    ap.add_argument("--waves", type=int, default=1, help="number of ignition patches (D29)")
    ap.add_argument("--tend", type=float, default=None, help="end time [ms]")
    ap.add_argument("--out", default="run")
    ap.add_argument("--calib", default="calib", help="calibration file name (without .json)")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load(open(f"{HERE}/config.yaml"))
    c = json.load(open(f"{HERE}/{a.calib}.json"))
    geo, op, nm = cfg["geometry"], cfg["operating_point"], cfg["numerics"]
    dx_mm = a.dx or nm["dx_mm"]
    t_end = (a.tend or nm["t_end_ms"]) * 1e-3

    ro, ri, L = geo["r_outer_mm"] * 1e-3, geo["r_inner_mm"] * 1e-3, geo["length_mm"] * 1e-3
    gap = ro - ri
    rm = 0.5 * (ro + ri)
    Wd = 2 * math.pi * rm            # D7: mean circumference; Wd * gap == annulus area exactly
    nx, ny = round(Wd / (dx_mm * 1e-3)), round(L / (dx_mm * 1e-3))
    dx, dy = Wd / nx, L / ny
    g, q, R, k, Ea = c["gamma"], c["q"], c["R"], c["k"], c["Ea"]
    p1, T1 = c["p1"], c["T1"]
    p_pl, T_pl = op["p_plenum_kPa"] * 1e3, op["T_plenum_K"]
    p_b = op["p_back_kPa"] * 1e3
    sigma = geo["area_ratio"]

    s = Solver(nx, ny, dx, dy, (g, q, R, k, Ea), (PERIODIC, PERIODIC, INJECTOR, OUTFLOW),
               inj=(p_pl, T_pl, sigma, a.cd), p_back=p_b, cfl=nm["cfl"])

    # D27: initial state
    x = (np.arange(nx) + 0.5) * dx
    y = (np.arange(ny) + 0.5) * dy
    X, Y = np.meshgrid(x, y, indexing="ij")
    h = nm["fill_height_mm"] * 1e-3
    fresh = Y < h
    T = np.where(fresh, T1, 1500.0)
    xi = np.where(fresh, 0.0, 1.0)
    p = np.full_like(X, p1)
    # D28 (revised after the 1D test): 10 mm patch at 2x CJ pressure, products behind it so
    # only a +x wave forms
    for n in range(a.waves):
        x0 = 0.1 * Wd + n * Wd / a.waves
        patch = (X >= x0) & (X < x0 + 10e-3) & (Y < h)
        p[patch] = 2 * c["CJ"]["p"]; T[patch] = c["CJ"]["T"]; xi[patch] = 1.0
        behind = (X >= x0 - 20e-3) & (X < x0) & fresh
        xi[behind] = 1.0; T[behind] = 1500.0
    rho = p / (R * T)
    s.set_prim(rho, 0 * rho, 0 * rho, p, xi)


    def inj_bottom(pw):
        """Vectorised injector face flux (same formula as solver.injector_flux): mass, y-momentum."""
        pcr = p_pl * (2 / (g + 1)) ** (g / (g - 1))
        cp = g * R / (g - 1)
        Gs = a.cd * p_pl * math.sqrt(g / (R * T_pl)) * (2 / (g + 1)) ** ((g + 1) / (2 * (g - 1)))
        rr = np.clip(pw / p_pl, 0, 1)
        Gsub = a.cd * np.sqrt(np.maximum(2 * g / (g - 1) * p_pl * p_pl / (R * T_pl)
                                         * (rr ** (2 / g) - rr ** ((g + 1) / g)), 0))
        G = np.where(pw >= p_pl, 0.0, np.where(pw < pcr, Gs, Gsub))
        uj = np.sqrt(np.maximum(2 * cp * T_pl * (1 - rr ** ((g - 1) / g)), 0))
        return sigma * G, sigma * G * uj + pw


    jp = int(nm["probe_y_mm"] * 1e-3 / dy)
    t_avg0 = nm["t_avg_start_ms"] * 1e-3
    snap_dt = nm["snap_every_us"] * 1e-6
    log = {k_: [] for k_ in ["t", "dt", "mdot_in", "mdot_out", "F_exit", "F_bottom", "tau_gas",
                              "M_exit", "u_exit", "p_head"]}
    probe_p, cam = [], []
    prof_sum, prof_w = np.zeros(ny), 0.0
    snaps, snap_t = [], []
    next_snap = 0.6e-3 if t_end >= 0.8e-3 else 0.5 * t_end
    t0 = time.time()
    step = 0
    while s.t < t_end:
        dt = s.step()
        step += 1
        W = s.prim()
        r_, u_, v_, p_, xi_ = W
        top = (r_[:, -1], u_[:, -1], v_[:, -1], p_[:, -1])
        m_in, mom_in = inj_bottom(p_[:, 0])
        a_top = np.sqrt(g * top[3] / top[0])
        mflux_top = top[0] * top[2]
        log["t"].append(s.t); log["dt"].append(dt)
        log["mdot_in"].append(gap * dx * m_in.sum())
        log["mdot_out"].append(gap * dx * mflux_top.sum())
        log["F_exit"].append(gap * dx * (top[0] * top[2] ** 2 + top[3] - p_b).sum())   # D36
        log["F_bottom"].append(gap * dx * (mom_in - p_b).sum())                        # D36 cross-check
        log["tau_gas"].append(rm * gap * dx * (top[0] * top[1] * top[2]).sum())       # D37
        Mt = np.sqrt(top[1] ** 2 + top[2] ** 2) / a_top
        log["M_exit"].append((Mt * mflux_top).sum() / max(mflux_top.sum(), 1e-12))     # D38
        log["u_exit"].append((top[1] * mflux_top).sum() / max(mflux_top.sum(), 1e-12))
        log["p_head"].append(p_[:, 0].mean())
        probe_p.append(p_[:, jp].astype(np.float32))                                   # D31a
        cam.append((p_ / (r_ * R)).mean(axis=1).astype(np.float32))                    # D33
        if s.t >= t_avg0:
            prof_sum += p_.mean(axis=0) * dt; prof_w += dt                              # D39
        if s.t >= next_snap:
            Tn = p_ / (r_ * R)
            snaps.append(np.stack([p_, Tn, xi_, np.sqrt(u_ ** 2 + v_ ** 2) / np.sqrt(g * p_ / r_),
                                   u_, v_]).astype(np.float32))
            snap_t.append(s.t); next_snap += snap_dt
        if step % 500 == 0:
            print(f"t={s.t*1e6:7.1f} us  step={step}  pmax={p_.max()/1e6:6.2f} MPa  "
                  f"mdot_in={log['mdot_in'][-1]*1e3:6.1f} g/s  floors={s.floor_hits}  "
                  f"wall={time.time()-t0:5.0f}s", flush=True)

    np.savez_compressed(f"{HERE}/{a.out}.npz", probe_p=np.array(probe_p), cam=np.array(cam),
                        snaps=np.array(snaps), snap_t=np.array(snap_t),
                        prof_p=prof_sum / max(prof_w, 1e-30), y=y, x=x,
                        **{k_: np.array(v_) for k_, v_ in log.items()})
    meta = dict(calib=a.calib, L_half=c["L_half"], Ea_over_RT1=c.get("Ea_over_RT1"), nx=nx, ny=ny, dx=dx, dy=dy, Wd=Wd, L=L, gap=gap, rm=rm, ro=ro, ri=ri, cd=a.cd,
                waves=a.waves, t_end=t_end, t_avg0=t_avg0, jp=jp, probe_y=y[jp], p_back=p_b,
                p_plenum=p_pl, floor_hits=int(s.floor_hits), steps=step, wall_s=time.time() - t0)
    json.dump(meta, open(f"{HERE}/{a.out}.json", "w"), indent=2)
    print("done", meta)


if __name__ == "__main__":
    main()
