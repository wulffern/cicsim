"""Unit tests for the VCD parser in cicsim.wavefiles."""

import os
import tempfile
import unittest

from cicsim.wavefiles import read_vcd, _vcd_parse_timescale


_SAMPLE_VCD = """\
$date Fri May 1 12:00:00 2026 $end
$version test $end
$timescale 10ns $end
$scope module top $end
$var wire 1 ! clk $end
$var wire 1 " rst_n $end
$var reg 8 # cnt [7:0] $end
$var real 1 $ vsense $end
$scope module sub $end
$var wire 1 % done $end
$upscope $end
$upscope $end
$enddefinitions $end
$dumpvars
0!
1"
b00000000 #
r0.5 $
0%
$end
#1
1!
b00000001 #
#2
0!
b00000010 #
1%
#3
1!
bxxxxxxxx #
rNaN $
"""


class TestTimescale(unittest.TestCase):
    def test_simple_timescale(self):
        self.assertEqual(_vcd_parse_timescale("1 ps"), 1e-12)
        self.assertEqual(_vcd_parse_timescale("10ns"), 10e-9)
        self.assertEqual(_vcd_parse_timescale("  1   ns  "), 1e-9)
        self.assertEqual(_vcd_parse_timescale("1us"), 1e-6)
        self.assertEqual(_vcd_parse_timescale("1µs"), 1e-6)

    def test_unknown_unit_falls_back(self):
        self.assertEqual(_vcd_parse_timescale("1 quux"), 1.0)

    def test_empty_returns_one(self):
        self.assertEqual(_vcd_parse_timescale(""), 1.0)
        self.assertEqual(_vcd_parse_timescale(None), 1.0)


class TestReadVcd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.vcd', delete=False)
        self.tmp.write(_SAMPLE_VCD)
        self.tmp.close()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_columns_are_scoped_names(self):
        df = read_vcd(self.tmp.name)
        cols = list(df.columns)
        self.assertIn('time', cols)
        self.assertIn('top.clk', cols)
        self.assertIn('top.rst_n', cols)
        self.assertIn('top.cnt', cols)
        self.assertIn('top.vsense', cols)
        self.assertIn('top.sub.done', cols)

    def test_timescale_applied(self):
        df = read_vcd(self.tmp.name)
        # 4 time markers (#0, #1, #2, #3) at 10 ns each
        self.assertEqual(len(df), 4)
        self.assertAlmostEqual(df['time'].iloc[0], 0.0)
        self.assertAlmostEqual(df['time'].iloc[1], 10e-9)
        self.assertAlmostEqual(df['time'].iloc[2], 20e-9)
        self.assertAlmostEqual(df['time'].iloc[3], 30e-9)

    def test_signal_kinds(self):
        df = read_vcd(self.tmp.name)
        kinds = df.attrs['cicsim_vcd']['kinds']
        self.assertEqual(kinds['top.clk'], 'bit')
        self.assertEqual(kinds['top.rst_n'], 'bit')
        self.assertEqual(kinds['top.cnt'], 'vector')
        self.assertEqual(kinds['top.vsense'], 'real')
        self.assertEqual(kinds['top.sub.done'], 'bit')

    def test_signal_widths(self):
        df = read_vcd(self.tmp.name)
        widths = df.attrs['cicsim_vcd']['widths']
        self.assertEqual(widths['top.clk'], 1)
        self.assertEqual(widths['top.cnt'], 8)

    def test_bit_values(self):
        df = read_vcd(self.tmp.name)
        # clk: 0 at #0, 1 at #1, 0 at #2, 1 at #3
        self.assertEqual(list(df['top.clk']), ['0', '1', '0', '1'])
        # rst_n is set to 1 at #0 and stays 1 (forward-fill)
        self.assertEqual(list(df['top.rst_n']), ['1', '1', '1', '1'])

    def test_vector_values(self):
        df = read_vcd(self.tmp.name)
        cnt = list(df['top.cnt'])
        self.assertEqual(cnt[0], 0)
        self.assertEqual(cnt[1], 1)
        self.assertEqual(cnt[2], 2)
        # last value contains x bits -> stored as the lowercase string
        self.assertEqual(cnt[3], 'xxxxxxxx')

    def test_real_values(self):
        df = read_vcd(self.tmp.name)
        v = list(df['top.vsense'])
        self.assertAlmostEqual(v[0], 0.5)
        self.assertAlmostEqual(v[1], 0.5)  # forward-filled

    def test_forward_fill_across_scopes(self):
        df = read_vcd(self.tmp.name)
        # done starts at 0 (#0) and goes to 1 at #2; #1 should still be 0
        self.assertEqual(df['top.sub.done'].iloc[0], '0')
        self.assertEqual(df['top.sub.done'].iloc[1], '0')
        self.assertEqual(df['top.sub.done'].iloc[2], '1')
        self.assertEqual(df['top.sub.done'].iloc[3], '1')


if __name__ == '__main__':
    unittest.main()
