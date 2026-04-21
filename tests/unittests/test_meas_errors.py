#!/usr/bin/env python3
"""
Test for issue #11: Check if errors in meas run are caught.

ngspiceMeas must return False when the .logm file contains "Error:" or "failed"
lines, True when clean, and ignore "incomplete or empty netlist" errors.
"""

import importlib.util
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "cicsim" / "cmdrunng.py"


def load_simulation_class():
    original = sys.modules.get("cicsim")
    stub = types.ModuleType("cicsim")
    stub.__path__ = [str(REPO_ROOT / "cicsim")]
    stub.CdsConfig = type("CdsConfig", (), {})
    sys.modules["cicsim"] = stub

    spec = importlib.util.spec_from_file_location("cicsim.cmdrunng", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if original is not None:
        sys.modules["cicsim"] = original
    else:
        del sys.modules["cicsim"]

    return module.Simulation


Simulation = load_simulation_class()


class TestMeasErrorDetection(unittest.TestCase):

    def _make_simulation(self, tmpdir, log_content):
        """Create a minimal Simulation-like object with a real logm file."""
        oname = os.path.join(tmpdir, "tran_TtVt")
        logm_path = oname + ".logm"
        with open(logm_path, "w") as f:
            f.write(log_content)

        with patch.object(Simulation, "__init__", lambda self, *a, **kw: None):
            sim = Simulation.__new__(Simulation)
            sim.name = "tran_TtVt"
            sim.oname = oname
            sim.runmeas = False
            sim.progress = False
        return sim

    def test_returns_true_when_no_errors(self):
        with tempfile.TemporaryDirectory() as d:
            sim = self._make_simulation(d, "Measurements for tran\nvx = 0.91\n")
            self.assertTrue(sim.ngspiceMeas())

    def test_returns_false_when_error_line_present(self):
        with tempfile.TemporaryDirectory() as d:
            sim = self._make_simulation(d, "Error: undefined variable vx\n")
            self.assertFalse(sim.ngspiceMeas())

    def test_returns_false_when_failed_line_present(self):
        with tempfile.TemporaryDirectory() as d:
            sim = self._make_simulation(d, "Measurement vx failed\n")
            self.assertFalse(sim.ngspiceMeas())

    def test_ignores_incomplete_netlist_error(self):
        with tempfile.TemporaryDirectory() as d:
            sim = self._make_simulation(
                d, "Error: incomplete or empty netlist\nvx = 0.91\n"
            )
            self.assertTrue(sim.ngspiceMeas())

    def test_returns_true_when_ignore_flag_set(self):
        with tempfile.TemporaryDirectory() as d:
            sim = self._make_simulation(d, "Error: undefined variable vx\n")
            self.assertTrue(sim.ngspiceMeas(ignore=True))

    def test_returns_true_when_logm_missing(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(Simulation, "__init__", lambda self, *a, **kw: None):
                sim = Simulation.__new__(Simulation)
                sim.name = "tran_TtVt"
                sim.oname = os.path.join(d, "nonexistent")
                sim.runmeas = False
                sim.progress = False
            self.assertTrue(sim.ngspiceMeas())


if __name__ == "__main__":
    unittest.main()
