#!/usr/bin/env python3
"""Tests for column-name unit auto-detection."""

import unittest

from cicsim.wavefiles import parse_unit_from_name


class TestParseUnitFromName(unittest.TestCase):
    def test_underscore_suffix_si_prefix(self):
        # Frequency_MHz -> data scaled by 1e6, base unit Hz.
        self.assertEqual(parse_unit_from_name("Frequency_MHz"),
                         (1e6, "Hz", "Frequency"))

    def test_bracket_suffix_log_unit(self):
        # Amplitude [dBm] -> no scaling, literal dBm.
        self.assertEqual(parse_unit_from_name("Amplitude [dBm]"),
                         (1.0, "dBm", "Amplitude"))

    def test_paren_suffix_plain_unit(self):
        self.assertEqual(parse_unit_from_name("Power (W)"),
                         (1.0, "W", "Power"))

    def test_space_separated_suffix(self):
        self.assertEqual(parse_unit_from_name("Vout V"),
                         (1.0, "V", "Vout"))

    def test_slash_separated_suffix(self):
        self.assertEqual(parse_unit_from_name("phase / deg"),
                         (1.0, "deg", "phase"))

    def test_si_prefix_voltage(self):
        # input_mV -> 1e-3 * V
        self.assertEqual(parse_unit_from_name("input_mV"),
                         (1e-3, "V", "input"))

    def test_si_prefix_amps_micro_alias(self):
        # I_uA -> 1e-6 * A (u is alias for micro)
        self.assertEqual(parse_unit_from_name("I_uA"),
                         (1e-6, "A", "I"))

    def test_si_prefix_time_picoseconds(self):
        self.assertEqual(parse_unit_from_name("delay [ps]"),
                         (1e-12, "s", "delay"))

    def test_dbm_variants(self):
        # All dBm-style suffixes are literal log units, no rescale.
        for tok in ("Amp_dBm", "Amp [dBm]", "Amp (dBm)", "Amp dBm"):
            with self.subTest(name=tok):
                r = parse_unit_from_name(tok)
                self.assertIsNotNone(r)
                scale, unit, clean = r
                self.assertEqual(scale, 1.0)
                self.assertEqual(unit, "dBm")
                self.assertEqual(clean, "Amp")

    def test_does_not_misfire_on_node_names(self):
        # ngspice/SPICE node names like v(out) and i(M1.d) must NOT be
        # parsed as having a unit (the parens contain the node name).
        self.assertIsNone(parse_unit_from_name("v(out)"))
        self.assertIsNone(parse_unit_from_name("i(M1.d)"))

    def test_does_not_misfire_on_unknown_suffixes(self):
        self.assertIsNone(parse_unit_from_name("temperature_value"))
        self.assertIsNone(parse_unit_from_name("foo_xyz"))

    def test_empty_input(self):
        self.assertIsNone(parse_unit_from_name(""))
        self.assertIsNone(parse_unit_from_name(None))


class TestWaveAppliesUnitDetection(unittest.TestCase):
    """End-to-end: a CSV with Frequency_MHz / Amplitude_dBm columns must
    produce a Wave with the right xunit (Hz, rescaled), yunit (dBm), and
    no rescale on y."""

    def setUp(self):
        import os
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = os.path.join(self.tmp.name, "spurscan.csv")
        with open(self.csv, "w") as f:
            f.write("Frequency_MHz,Amplitude_dBm\n")
            # 100 MHz, 200 MHz -> after auto-rescale should be 1e8, 2e8 Hz
            f.write("100,-66.3\n")
            f.write("200,-66.6\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_wave_picks_up_units_and_scales(self):
        from cicsim.wavefiles import WaveFile, Wave
        wf = WaveFile(self.csv, xaxis="")
        w = Wave(wf, "Amplitude_dBm", xaxis="")
        self.assertEqual(w.xunit, "Hz")
        self.assertEqual(w.yunit, "dBm")
        # MHz -> Hz means data * 1e6
        self.assertAlmostEqual(float(w.x[0]), 1e8)
        self.assertAlmostEqual(float(w.x[1]), 2e8)
        # dBm is log-domain: y must NOT be rescaled
        self.assertAlmostEqual(float(w.y[0]), -66.3)
        self.assertAlmostEqual(float(w.y[1]), -66.6)
        # Cleaned-up label should drop the "_MHz" suffix
        self.assertEqual(w.xlabel, "Frequency")


if __name__ == "__main__":
    unittest.main()
