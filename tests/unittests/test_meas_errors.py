#!/usr/bin/env python3
"""
Test for issue #11: Check if errors in meas run are caught.

ngspiceMeas must return False when the .logm file contains "Error:" or "failed"
lines, True when clean, and ignore "incomplete or empty netlist" errors.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock


class TestMeasErrorDetection(unittest.TestCase):

    def _make_simulation(self, tmpdir, log_content):
        """Create a minimal Simulation-like object with a real logm file."""
        from cicsim.cmdrunng import Simulation

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
            from cicsim.cmdrunng import Simulation
            with patch.object(Simulation, "__init__", lambda self, *a, **kw: None):
                sim = Simulation.__new__(Simulation)
                sim.name = "tran_TtVt"
                sim.oname = os.path.join(d, "nonexistent")
                sim.runmeas = False
                sim.progress = False
            self.assertTrue(sim.ngspiceMeas())


if __name__ == "__main__":
    unittest.main()
