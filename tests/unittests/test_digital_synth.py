"""Tests for analog -> digital bit synthesis (PgWave.synthesizeDigitalBits).

The synthesis lives inside cmdwave_pg.py which depends on PySide6/pyqtgraph;
import lazily and skip the module entirely when those aren't available.
"""

import unittest

import numpy as np

try:  # pragma: no cover - optional GUI deps
    from cicsim.cmdwave_pg import PgWave
    HAVE_PG = True
except Exception:
    HAVE_PG = False


@unittest.skipUnless(HAVE_PG, "pyqtgraph / PySide6 not installed")
class TestSynthesizeDigitalBits(unittest.TestCase):

    def _make_wave(self, y):
        """Build a PgWave-like object with just the attributes the
        synthesizer touches, avoiding the full ctor + WaveFile setup."""
        w = PgWave.__new__(PgWave)
        w.y = np.asarray(y, dtype=float)
        w.x = np.arange(len(y), dtype=float)
        return w

    def test_clean_square_wave(self):
        y = np.tile([0.0, 0.0, 1.0, 1.0], 4)
        bits = self._make_wave(y).synthesizeDigitalBits()
        self.assertEqual(list(bits), list(map(str, y.astype(int))))

    def test_constant_signal_no_transitions(self):
        bits = self._make_wave([0.5] * 8).synthesizeDigitalBits()
        self.assertTrue(all(b == bits[0] for b in bits))
        self.assertEqual(set(bits), {'1'})

    def test_constant_zero_reports_low(self):
        bits = self._make_wave([0.0] * 8).synthesizeDigitalBits()
        self.assertEqual(set(bits), {'0'})

    def test_threshold_uses_min_max_midpoint(self):
        #- Mid-level is 1.4 V (half of 0..2.8). Samples below that map
        #- to 0, above to 1.
        y = [0.0, 1.0, 1.5, 2.0, 1.3, 2.8]
        bits = self._make_wave(y).synthesizeDigitalBits()
        self.assertEqual(list(bits), ['0', '0', '1', '1', '0', '1'])

    def test_hysteresis_suppresses_noise(self):
        #- Noisy crossing around the threshold; with default 5%
        #- hysteresis the small bumps inside the band shouldn't toggle.
        y = [0.0, 0.0, 0.49, 0.51, 0.49, 0.51, 0.49, 1.0, 0.51,
             0.0, 0.0]
        #- Range = 1.0 -> hysteresis band = [0.45, 0.55]. Once we
        #- cross to '1' (at >=0.55) we don't drop back to '0' until
        #- we go <=0.45.
        bits = self._make_wave(y).synthesizeDigitalBits()
        # initial 0s, in-band wobbles hold low, true 1.0 forces high,
        # then 0.0 returns low.
        self.assertEqual(bits[0], '0')
        self.assertEqual(bits[1], '0')
        self.assertEqual(bits[7], '1')
        self.assertEqual(bits[-1], '0')
        #- The number of transitions should be small (just 2 in the
        #- ideal case: low->high once, high->low once).
        transitions = sum(1 for i in range(1, len(bits))
                          if bits[i] != bits[i - 1])
        self.assertLessEqual(transitions, 2)

    def test_nan_becomes_x(self):
        y = [np.nan, 0.0, 1.0, np.nan, 1.0]
        bits = self._make_wave(y).synthesizeDigitalBits()
        self.assertEqual(list(bits), ['x', '0', '1', 'x', '1'])

    def test_empty_input(self):
        w = self._make_wave([])
        bits = w.synthesizeDigitalBits()
        self.assertEqual(len(bits), 0)


if __name__ == '__main__':
    unittest.main()
