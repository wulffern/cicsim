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

    def test_multiline_subckt_with_leading_plus(self):
        """Standard spice continuation, no trailing backslash."""
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(
                d,
                ".SUBCKT myblk vdd vss\n+ in out\n.ENDS\n",
            )
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["vdd", "vss", "in", "out"])

    def test_multiline_subckt_three_continuations(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(
                d,
                ".subckt myblk a b\n+ c d\n+ e f\n.ends\n",
            )
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b", "c", "d", "e", "f"])

    def test_backslash_continuation_without_leading_plus(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(
                d,
                ".SUBCKT myblk vdd vss \\\n  in out\n.ENDS\n",
            )
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["vdd", "vss", "in", "out"])

    def test_trailing_parameters_are_not_ports(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".subckt myblk a b c W=1 L=2\n.ends\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b", "c"])

    def test_params_keyword_is_not_a_port(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".subckt myblk a b c params: w=1\n.ends\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b", "c"])

    def test_inline_comment_is_not_a_port(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".subckt myblk a b c $ this is a comment\n.ends\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b", "c"])

    def test_semicolon_comment_is_not_a_port(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".subckt myblk a b c ; comment\n.ends\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b", "c"])

    def test_dollar_inside_net_name_is_kept(self):
        """'$' only starts a comment after whitespace, net names may contain it."""
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".subckt myblk a$0 b$1 c\n.ends\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a$0", "b$1", "c"])

    def test_subckt_without_ports(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(d, ".subckt myblk\n.ends\n")
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, [])

    def test_name_that_is_prefix_of_another_subckt(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(
                d,
                ".subckt myblk_big x y\n.ends\n.subckt myblk a b\n.ends\n",
            )
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b"])

    def test_full_line_comment_between_continuations(self):
        with tempfile.TemporaryDirectory() as d:
            path = self._write_spice(
                d,
                ".subckt myblk a b\n* a comment\n+ c d\n.ends\n",
            )
            ports = SpiceParser().fastGetPortsFromFile(path, "myblk")
            self.assertEqual(ports, ["a", "b", "c", "d"])

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
