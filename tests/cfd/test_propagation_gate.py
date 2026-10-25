"""Failure-oriented tests for the numerical propagation acceptance checks."""

import copy
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cfd/pelec/propagation"))
from analyze_wave import crossing, history_complete


class GateTests(unittest.TestCase):
    def test_front_crossing_does_not_wrap_or_invent_a_front(self):
        x = np.arange(5.0)
        self.assertIsNone(crossing(x, np.ones(5), 2))
        self.assertAlmostEqual(crossing(x, np.array([4.0, 4.0, 4.0, 0.0, 0.0]), 2), 2.5)

    def test_missing_intermediate_step_fails_with_correct_endpoints(self):
        good = {
            k: [[0, 1, 2], [1e-9, 1, 2], [2e-9, 1, 2]]
            for k in ("density", "Temp", "pressure", "massfrac", "sumYminus1")
        }
        self.assertTrue(history_complete(good, 2e-9, 1e-9))
        bad = copy.deepcopy(good)
        bad["Temp"].pop(1)
        self.assertFalse(history_complete(bad, 2e-9, 1e-9))
        bad = copy.deepcopy(good)
        bad["Temp"][1][0] = 2e-9
        self.assertFalse(history_complete(bad, 2e-9, 1e-9))
        bad = copy.deepcopy(good)
        bad["pressure"][1][1] = np.nan
        self.assertFalse(history_complete(bad, 2e-9, 1e-9))

    def test_empty_history_fails(self):
        self.assertFalse(history_complete({}, 2e-9, 1e-9))


class AnimationInputTests(unittest.TestCase):
    def test_animation_rejects_invented_or_invalid_time_and_fields(self):
        import importlib.util

        path = Path(__file__).resolve().parents[2] / "cfd/pelec/engine/visualize.py"
        spec = importlib.util.spec_from_file_location("native_animation", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        good = dict(time_s=np.array([0.0, 1.0]), x_m=np.arange(3.0), y_m=np.arange(3.0))
        for key in (
            "pressure_Pa",
            "density_kg_m3",
            "heat_release_W_m3",
            "u_mps",
            "v_mps",
        ):
            good[key] = np.ones((2, 3, 3))
        mod.validate(good)
        bad = copy.deepcopy(good)
        bad["time_s"][1] = 0
        with self.assertRaises(ValueError):
            mod.validate(bad)
        bad = copy.deepcopy(good)
        bad["pressure_Pa"][1, 1, 1] = np.nan
        with self.assertRaises(ValueError):
            mod.validate(bad)
        bad = copy.deepcopy(good)
        bad["x_m"][2] = 3.0
        with self.assertRaises(ValueError):
            mod.validate(bad)
        bad = copy.deepcopy(good)
        bad["density_kg_m3"][1, 1, 1] = -1
        with self.assertRaises(ValueError):
            mod.validate(bad)


class FrameTests(unittest.TestCase):
    def test_galilean_round_trip_preserves_internal_energy_and_species(self):
        from boost import transform

        table = np.array(
            [
                [0.004, 800.0, -2000.0, 0.001, 0.003],
                [0.02, 1200.0, 50000000.0, 0.01, 0.01],
            ]
        )
        transformed = transform(table, 253081.0)
        np.testing.assert_array_equal(transformed[:, 3:], table[:, 3:])
        np.testing.assert_allclose(
            transform(transformed, -253081.0), table, rtol=1e-10, atol=1e-7
        )


if __name__ == "__main__":
    unittest.main()
