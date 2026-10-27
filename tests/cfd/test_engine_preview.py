"""Engine adapters must preserve units, conserved launch states and valid inputs."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    p = ROOT / "cfd/pelec/engine" / f"{name}.py"
    spec = importlib.util.spec_from_file_location("engine_" + name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class PreviewContracts(unittest.TestCase):
    def test_uniform_grid_and_complete_physical_frames_required(self):
        v = module("visualize")
        a = dict(
            time_s=np.array([0.0, 0.001]),
            x_m=np.arange(4.0) * 0.001,
            y_m=np.arange(3.0) * 0.001,
        )
        for n in (
            "pressure_Pa",
            "density_kg_m3",
            "heat_release_W_m3",
            "u_mps",
            "v_mps",
        ):
            a[n] = np.ones((2, 4, 3))
        v.validate(a)
        bad = dict(a)
        bad["time_s"] = np.array([0.0, 0.0])
        with self.assertRaises(ValueError):
            v.validate(bad)
        bad = dict(a)
        bad["density_kg_m3"] = -a["density_kg_m3"]
        with self.assertRaises(ValueError):
            v.validate(bad)

    def test_prepared_native_launch_conserves_elements_and_has_tangential_momentum(
        self,
    ):
        import cantera as ct

        reference = ROOT / "docs/verification/pelec_2d_propagation"
        mechanism = ROOT / "runs_cfd/ffcm_wave_n2048_mol/native/mechanism.yaml"
        if not mechanism.exists():
            self.skipTest("Pinned local native mechanism artifact unavailable")
        g = ct.Solution(str(mechanism))
        prep = module("prepare")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "case"
            c = prep.prepare(reference, mechanism, "run937_76fi5", out, nx=64, ny=24)
            a = np.loadtxt(out / "profile.dat", skiprows=1)
            rho = a[:, 0] * 1000
            mom = a[:, 1] * 10
            energy = a[:, 2] * 0.1
            Y = a[:, 3:] / a[:, 0, None]
            np.testing.assert_allclose(Y.sum(axis=1), 1, atol=1e-10)
            e = Y @ np.array(c["element_weights"]).reshape(g.n_species, g.n_elements)
            np.testing.assert_allclose(
                e, np.broadcast_to(c["elements"], e.shape), atol=1e-10
            )
            self.assertGreater(mom.sum(), 0)
            self.assertGreater(c["circumference_m"], 0.2)
            for i in range(c["nx"]):
                g.TDY = 1000, rho[i], Y[i]
                g.UV = energy[i] / rho[i] - 0.5 * (mom[i] / rho[i]) ** 2, 1 / rho[i]
                self.assertGreaterEqual(g.T, 200)
                self.assertLessEqual(g.T, 5000)
            # Background and feed have the same element fractions; no fuel/oxygen reset can hide mixing errors.
            coeff = np.array(c["element_weights"]).reshape(g.n_species, g.n_elements)
            np.testing.assert_allclose(
                np.array(c["bgY"]) @ coeff, c["elements"], atol=1e-10
            )
            self.assertAlmostEqual(c["area_ratio_effective"], 0.110 * 0.76)
            with self.assertRaises(ValueError):
                prep.prepare(
                    reference,
                    mechanism,
                    "run937_76fi5",
                    Path(tmp) / "bad",
                    nx=63,
                    ny=24,
                )


if __name__ == "__main__":
    unittest.main()
