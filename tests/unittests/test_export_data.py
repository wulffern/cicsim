"""Tests for PgWave.exportData (plotted-waveform data export).

Uses PgWave.__new__ to skip the Qt ctor — same pattern as
test_digital_synth.py — and stubs the bits of state the exporter
touches (wave_data, _digital_waves, plot.vb).
"""

import os
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

try:  # pragma: no cover - optional GUI deps
    from cicsim.cmdwave_pg import PgWavePlot
    HAVE_PG = True
except Exception:
    HAVE_PG = False


def _make_wave(key, x, y, *, xlabel="Time", xunit="s", yunit="V",
               tag=None):
    """Build a wave-like object with just the attributes the exporter
    touches (matches the cicsim.wavefiles.Wave surface)."""
    return SimpleNamespace(
        key=key, ylabel=key, xlabel=xlabel, xunit=xunit, yunit=yunit,
        tag=tag or key,
        x=np.asarray(x), y=np.asarray(y),
    )


def _make_pg(waves, view_xrange=None, digital_tags=()):
    """Build a stripped-down PgWavePlot instance for exportData."""
    p = PgWavePlot.__new__(PgWavePlot)
    p.wave_data = {w.tag: (w, w.yunit) for w in waves}
    p._digital_waves = {t: None for t in digital_tags}
    if view_xrange is None:
        # A vb that raises -> the exporter falls back to "no clip".
        class _NoView:
            def viewRange(self):
                raise RuntimeError("no view")
        p.plot = SimpleNamespace(vb=_NoView())
    else:
        class _View:
            def __init__(self, xr):
                self._xr = xr
            def viewRange(self):
                return [list(self._xr), [0.0, 1.0]]
        p.plot = SimpleNamespace(vb=_View(view_xrange))
    return p


@unittest.skipUnless(HAVE_PG, "pyqtgraph / PySide6 not installed")
class ExportDataTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cicwave-export-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _path(self, name):
        return os.path.join(self.tmp, name)

    def test_csv_two_traces_side_by_side(self):
        w1 = _make_wave("v(out)", [0.0, 1.0, 2.0], [0.1, 0.2, 0.3])
        w2 = _make_wave("v(in)", [0.0, 1.0, 2.0], [1.0, 0.5, 0.0])
        out = self._path("two.csv")
        n_traces, n_rows = _make_pg([w1, w2])._export_data_to(out)
        self.assertEqual(n_traces, 2)
        self.assertEqual(n_rows, 3)
        df = pd.read_csv(out)
        # 4 columns: x_w1, y_w1, x_w2, y_w2 (side-by-side).
        self.assertEqual(len(df.columns), 4)
        self.assertEqual(list(df.columns)[0:2], ["Time (s)", "v(out) (V)"])
        np.testing.assert_array_equal(df["v(out) (V)"].to_numpy(),
                                      [0.1, 0.2, 0.3])
        np.testing.assert_array_equal(df["v(in) (V)"].to_numpy(),
                                      [1.0, 0.5, 0.0])

    def test_unique_column_names_when_keys_collide(self):
        w1 = _make_wave("y", [0, 1, 2], [10, 20, 30], tag="a")
        w2 = _make_wave("y", [0, 1, 2], [40, 50, 60], tag="b")
        out = self._path("collide.csv")
        _make_pg([w1, w2])._export_data_to(out)
        df = pd.read_csv(out)
        # Two "y (V)" columns must be disambiguated.
        self.assertEqual(sum(c.startswith("y (V)") for c in df.columns), 2)
        self.assertEqual(len(set(df.columns)), len(df.columns))

    def test_heterogeneous_lengths_pad_with_nan(self):
        w1 = _make_wave("a", [0, 1, 2, 3], [1.0, 2.0, 3.0, 4.0])
        w2 = _make_wave("b", [0, 1], [10.0, 20.0])  # shorter
        out = self._path("pad.csv")
        n_traces, n_rows = _make_pg([w1, w2])._export_data_to(out)
        self.assertEqual(n_rows, 4)
        df = pd.read_csv(out)
        # Last two values of "b (V)" should be NaN.
        b = df["b (V)"].to_numpy()
        self.assertEqual(b[0], 10.0)
        self.assertEqual(b[1], 20.0)
        self.assertTrue(np.isnan(b[2]))
        self.assertTrue(np.isnan(b[3]))

    def test_view_xrange_is_honoured(self):
        x = np.arange(10, dtype=float)
        y = x * 10
        w = _make_wave("v", x, y)
        out = self._path("zoomed.csv")
        # Zoomed to [3, 6] inclusive -> 4 samples.
        _, n_rows = _make_pg([w], view_xrange=(3.0, 6.0))._export_data_to(out)
        self.assertEqual(n_rows, 4)
        df = pd.read_csv(out)
        np.testing.assert_array_equal(df["v (V)"].to_numpy(),
                                      [30.0, 40.0, 50.0, 60.0])

    def test_digital_traces_are_skipped(self):
        analog = _make_wave("v", [0, 1, 2], [0.0, 0.5, 1.0])
        digital = _make_wave("clk", [0, 1, 2], [0, 1, 0], tag="clk_d")
        pg = _make_pg([analog, digital], digital_tags=["clk_d"])
        out = self._path("nodig.csv")
        n_traces, _ = pg._export_data_to(out)
        self.assertEqual(n_traces, 1)
        df = pd.read_csv(out)
        self.assertNotIn("clk (V)", df.columns)

    def test_tsv_extension(self):
        w = _make_wave("v", [0, 1, 2], [1.0, 2.0, 3.0])
        out = self._path("out.tsv")
        _make_pg([w])._export_data_to(out)
        with open(out, "r") as fh:
            head = fh.readline()
        self.assertIn("\t", head)

    def test_parquet_round_trip(self):
        try:
            import pyarrow  # noqa: F401
        except Exception:
            self.skipTest("pyarrow not installed")
        w = _make_wave("v", [0.0, 1.0, 2.0], [10.0, 20.0, 30.0])
        out = self._path("out.parquet")
        _make_pg([w])._export_data_to(out)
        df = pd.read_parquet(out)
        np.testing.assert_array_equal(df["v (V)"].to_numpy(),
                                      [10.0, 20.0, 30.0])

    def test_unknown_extension_raises(self):
        w = _make_wave("v", [0, 1], [0.0, 1.0])
        with self.assertRaises(ValueError):
            _make_pg([w])._export_data_to(self._path("out.bogus"))

    def test_no_traces_raises(self):
        with self.assertRaises(ValueError):
            _make_pg([])._export_data_to(self._path("out.csv"))


if __name__ == "__main__":
    unittest.main()
