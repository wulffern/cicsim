#!/usr/bin/env python3
"""Tests for lazy CSV / column-only loading in WaveFile."""

import os
import tempfile
import unittest

import pandas as pd

from cicsim.wavefiles import WaveFile


class TestWaveFileLazy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = os.path.join(self.tmp.name, "wf.csv")
        with open(self.csv, "w") as f:
            f.write("time,v(out),v(in)\n")
            for i in range(5):
                f.write("%d,%g,%g\n" % (i, i * 0.1, i * 0.2))

    def tearDown(self):
        self.tmp.cleanup()

    def test_open_does_not_load_full_dataframe(self):
        wf = WaveFile(self.csv, xaxis="time")
        self.assertIsNone(wf._df, "df should be None after open (lazy)")
        self.assertEqual(
            list(wf.getWaveNames()), ["time", "v(out)", "v(in)"])
        self.assertIsNone(wf._df, "getWaveNames must not trigger full read")

    def test_df_access_loads_full_dataframe(self):
        wf = WaveFile(self.csv, xaxis="time")
        df = wf.df
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5)
        self.assertEqual(list(df.columns), ["time", "v(out)", "v(in)"])
        self.assertAlmostEqual(df["v(out)"].iloc[4], 0.4)

    def test_setter_keeps_columns_in_sync(self):
        wf = WaveFile(self.csv, xaxis="time")
        new = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        wf.df = new
        self.assertEqual(list(wf.getWaveNames()), ["a", "b"])

    def test_virtual_dataframe_is_not_re_read(self):
        df = pd.DataFrame({"time": [0, 1], "v(x)": [0.5, 0.6]})
        wf = WaveFile("virtual.csv", xaxis="time", df=df)
        self.assertIs(wf.df, df)
        self.assertEqual(list(wf.getWaveNames()), ["time", "v(x)"])


if __name__ == "__main__":
    unittest.main()
