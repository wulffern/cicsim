#!/usr/bin/env python3
"""
Test for issue #16: spiceparser port extraction.

fastGetPortsFromFile must correctly return port lists from single-line
and multi-line (continuation) SUBCKT definitions.
"""

import os
import tempfile
import unittest

from cicsim.spiceparser import SpiceParser


class TestSpiceParserPorts(unittest.TestCase):

    def _write_spice(self, tmpdir, content):
        path = os.path.join(tmpdir, "test.spi")
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_single_line_subckt(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".SUBCKT myblk vdd vss in out\n.ENDS\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["vdd", "vss", "in", "out"])

    def test_multiline_subckt_with_backslash(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(
                d,
                ".SUBCKT myblk vdd vss \\\n+ in out\n.ENDS\n",
            )
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["vdd", "vss", "in", "out"])

    def test_case_insensitive_subckt_keyword(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".subckt myblk a b c\n.ends\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b", "c"])

    def test_missing_subckt_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".SUBCKT other vdd vss\n.ENDS\n")
            result = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertIsNone(result)

    def test_multiple_subckts_selects_correct_one(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(
                d,
                ".SUBCKT first a b\n.ENDS\n.SUBCKT myblk x y z\n.ENDS\n",
            )
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["x", "y", "z"])


if __name__ == "__main__":
    unittest.main()
