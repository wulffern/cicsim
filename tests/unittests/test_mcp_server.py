"""Tests for the cicsim MCP server tools.

The module imports the MCP SDK at import time, so skip the whole file
when it isn't installed (it is an optional extra: `pip install
cicsim[mcp]`). The tools themselves are plain functions -- FastMCP's
.tool() decorator registers and returns the original -- so they can be
called directly without standing up a server.
"""

import os
import shutil
import struct
import tempfile
import unittest

try:  # pragma: no cover - optional dep
    from cicsim import mcp_server
    HAVE_MCP = True
except Exception:
    HAVE_MCP = False


def _write_raw(path, varnames, rows):
    """Write a minimal ngspice binary rawfile that ngRawRead accepts."""
    with open(path, "wb") as fo:
        fo.write(b"Title: test\n")
        fo.write(b"Date: Thu Jan  1 00:00:00  2026\n")
        fo.write(b"Plotname: Transient Analysis\n")
        fo.write(b"Flags: real\n")
        fo.write(b"No. Variables: %d\n" % len(varnames))
        fo.write(b"No. Points: %d\n" % len(rows))
        fo.write(b"Variables:\n")
        for i, n in enumerate(varnames):
            unit = "time" if i == 0 else "voltage"
            fo.write(b"\t%d\t%s\t%s\n" % (i, n.encode(), unit.encode()))
        fo.write(b"Binary:\n")
        for row in rows:
            for v in row:
                fo.write(struct.pack("d", v))


@unittest.skipUnless(HAVE_MCP, "mcp SDK not installed")
class TestRawTools(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.raw = os.path.join(self.dir, "tran.raw")
        _write_raw(
            self.raw,
            ["time", "v(out)", "v(xdut.xbias.vc)"],
            [(0.0, 0.0, 0.5), (1e-6, 1.8, 0.5), (2e-6, 0.0, 0.7)],
        )

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_raw_info_lists_vectors_and_span(self):
        out = mcp_server.raw_info(self.raw)
        self.assertIn("v(out)", out)
        self.assertIn("v(xdut.xbias.vc)", out)
        self.assertIn("Transient Analysis", out)
        #- The x span is what shows whether the run reached t_stop.
        self.assertIn("2e-06", out)

    def test_raw_info_pattern_filters(self):
        out = mcp_server.raw_info(self.raw, pattern="vc")
        self.assertIn("v(xdut.xbias.vc)", out)
        self.assertNotIn("    v(out)", out)
        self.assertIn("matching", out)

    def test_raw_info_pattern_matching_nothing_is_not_an_error(self):
        out = mcp_server.raw_info(self.raw, pattern="nosuchnode")
        self.assertIn("no vector names matched", out)

    def test_raw_signals_reports_stats(self):
        out = mcp_server.raw_signals(self.raw, ["v(out)"])
        self.assertIn("v(out)", out)
        self.assertIn("1.8", out)

    def test_raw_signals_is_case_insensitive(self):
        out = mcp_server.raw_signals(self.raw, ["V(OUT)"])
        self.assertIn("v(out)", out)
        self.assertNotIn("NOT FOUND", out)

    def test_raw_signals_names_missing_vectors(self):
        out = mcp_server.raw_signals(self.raw, ["v(nope)"])
        self.assertIn("NOT FOUND", out)

    def test_raw_signals_at_picks_nearest_sample(self):
        out = mcp_server.raw_signals(self.raw, ["v(out)"], at=1e-6)
        self.assertIn("nearest sample", out)
        #- v(out) is 1.8 at t=1u; the "at" column must show it.
        self.assertGreaterEqual(out.count("1.8"), 1)


@unittest.skipUnless(HAVE_MCP, "mcp SDK not installed")
class TestStaleness(unittest.TestCase):
    """The sha comparison, which is the point of sim_status.

    mtime cannot be used here: the design flow regenerates the netlist
    on every run, so its mtime always moves. Only the recorded hash
    distinguishes "rewritten" from "actually changed".
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.rundir = os.path.join(self.dir, "output_tran")
        os.makedirs(self.rundir)

        self.netlist = os.path.join(self.dir, "netlist.spice")
        with open(self.netlist, "w") as fo:
            fo.write("* original\n")

        with open(os.path.join(self.dir, "tran_Sch_typical.run"), "w") as fo:
            fo.write("output_tran/tran_SchTt\n")

        self._write_sha()

    def _write_sha(self):
        import yaml
        shas = {"../netlist.spice": mcp_server._sha256(self.netlist)}
        with open(os.path.join(self.rundir, "tran_SchTt.sha"), "w") as fo:
            fo.write(yaml.dump(shas))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_unchanged_netlist_is_up_to_date(self):
        out = mcp_server.sim_status(self.dir)
        self.assertIn("up to date", out)

    def test_rewriting_identical_content_stays_up_to_date(self):
        #- What `make netlist` does every single run.
        os.utime(self.netlist, (0, 0))
        with open(self.netlist, "w") as fo:
            fo.write("* original\n")
        out = mcp_server.sim_status(self.dir)
        self.assertIn("up to date", out)

    def test_changed_netlist_is_stale(self):
        with open(self.netlist, "w") as fo:
            fo.write("* edited\n")
        out = mcp_server.sim_status(self.dir)
        self.assertNotIn("up to date", out)
        self.assertIn("netlist.spice", out)

    def test_missing_dependency_is_stale(self):
        os.unlink(self.netlist)
        out = mcp_server.sim_status(self.dir)
        self.assertIn("netlist.spice", out)

    def test_run_without_sha_is_reported_unknown(self):
        os.unlink(os.path.join(self.rundir, "tran_SchTt.sha"))
        out = mcp_server.sim_status(self.dir)
        self.assertIn("no .sha recorded", out)

    def test_directory_is_restored_after_call(self):
        before = os.getcwd()
        mcp_server.sim_status(self.dir)
        self.assertEqual(before, os.getcwd())

    def test_empty_directory_is_not_an_error(self):
        empty = tempfile.mkdtemp()
        try:
            self.assertIn("no .run files", mcp_server.sim_status(empty))
        finally:
            shutil.rmtree(empty, ignore_errors=True)


@unittest.skipUnless(HAVE_MCP, "mcp SDK not installed")
class TestResults(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.rundir = os.path.join(self.dir, "output_tran")
        os.makedirs(self.rundir)

        with open(os.path.join(self.dir, "tran_Sch_typical.run"), "w") as fo:
            fo.write("output_tran/tran_SchTt\n")

        #- idd is in amps; the spec is written in uA with scale -1e6, and
        #- "sweep" is a list, which is the shape that used to crash the
        #- scaling (a spec name can collide with a post-processed list).
        with open(os.path.join(self.rundir, "tran_SchTt.yaml"), "w") as fo:
            fo.write("idd_25: -3.0e-05\nsweep: [1, 2, 3]\n")

        with open(os.path.join(self.dir, "tran.yaml"), "w") as fo:
            fo.write(
                "idd:\n"
                "  src:\n    - idd_25\n"
                "  typ: 30\n  min: 5\n  max: 100\n"
                "  scale: -1e6\n  digits: 3\n  unit: uA\n"
                "sweep:\n"
                "  typ: 0\n  min: 0\n  max: 10\n  unit: x\n"
            )

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_scaled_value_is_within_spec(self):
        out = mcp_server.results("tran_Sch_typical.run", directory=self.dir)
        self.assertIn("idd_25", out)
        self.assertIn("30", out)
        self.assertIn("ok", out)

    def test_list_valued_key_does_not_crash(self):
        #- A spec named "sweep" exists, but the measured value is a list;
        #- it must be skipped rather than multiplied by the scale.
        out = mcp_server.results("tran_Sch_typical.run", directory=self.dir)
        self.assertNotIn("Traceback", out)

    def test_only_fails_filters_passing_rows(self):
        out = mcp_server.results("tran_Sch_typical.run", directory=self.dir,
                                 only_fails=True)
        self.assertIn("within min/max", out)

    def test_out_of_spec_is_reported_with_corner(self):
        with open(os.path.join(self.rundir, "tran_SchTt.yaml"), "w") as fo:
            fo.write("idd_25: -3.0e-03\n")
        out = mcp_server.results("tran_Sch_typical.run", directory=self.dir,
                                 only_fails=True)
        self.assertIn("FAIL", out)
        self.assertIn("SchTt", out)

    def test_missing_runfile_is_reported(self):
        out = mcp_server.results("nope.run", directory=self.dir)
        self.assertIn("no such run file", out)


if __name__ == "__main__":
    unittest.main()
