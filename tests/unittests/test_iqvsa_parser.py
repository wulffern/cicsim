"""Unit tests for the LitePoint .iqvsa parser in cicsim.wavefiles."""

import os
import struct
import tempfile
import unittest

import numpy as np

from cicsim.wavefiles import (
    WaveFile,
    _iqvsa_parse_module_config,
    read_iqvsa,
)


def _make_iqvsa_bytes(I, Q, fs=160e6, fc=2.412e9, capture_time=20e-3,
                      header_extras=""):
    """Build a minimal but well-formed LitePoint .iqvsa byte blob."""
    assert len(I) == len(Q)
    n = len(I)
    header = (
        '<LPHeader version="0.3">'
        '<General>'
        '<FileType>LitePoint VSA capture file</FileType>'
        '<DataFormat>IQ</DataFormat>'
        '<IDN>LitePoint,IQXEL-test,SN0,1.0</IDN>'
        '<DateTime>2026/05/07 09:00:00</DateTime>'
        '</General>'
        '<DataInfo>'
        f'<SamplingRate>{int(fs)}</SamplingRate>'
        f'<SampleCount>{n}</SampleCount>'
        '</DataInfo>'
        '<ModuleConfiguration module="VSA1">\n'
        'VSA1;\n'
        f'FREQuency:CENTer {fc:.6e};\n'
        f'CAPTure:TIME {capture_time:.6e};\n'
        f'{header_extras}'
        '</ModuleConfiguration>'
        '</LPHeader>'
    )
    iq = np.empty(2 * n, dtype='<f4')
    iq[0::2] = I
    iq[1::2] = Q
    return header.encode('ascii') + iq.tobytes()


class IQVSAParserTest(unittest.TestCase):

    def setUp(self):
        # Tone we can verify exactly.
        self.fs = 160e6
        self.n = 1024
        t = np.arange(self.n) / self.fs
        f0 = 1e6
        self.I = (0.01 * np.cos(2 * np.pi * f0 * t)).astype(np.float32)
        self.Q = (0.01 * np.sin(2 * np.pi * f0 * t)).astype(np.float32)
        self.tmp = tempfile.NamedTemporaryFile(
            suffix='.iqvsa', delete=False)
        self.tmp.write(_make_iqvsa_bytes(self.I, self.Q, fs=self.fs))
        self.tmp.close()
        self.path = self.tmp.name

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_columns_and_shape(self):
        df = read_iqvsa(self.path)
        self.assertEqual(list(df.columns), ['time', 'I (V)', 'Q (V)', 'mag (V)'])
        self.assertEqual(len(df), self.n)

    def test_time_axis_matches_sampling_rate(self):
        df = read_iqvsa(self.path)
        self.assertAlmostEqual(df['time'].iloc[0], 0.0)
        self.assertAlmostEqual(df['time'].iloc[1], 1.0 / self.fs)
        self.assertAlmostEqual(
            df['time'].iloc[-1], (self.n - 1) / self.fs)

    def test_iq_values_round_trip(self):
        df = read_iqvsa(self.path)
        np.testing.assert_array_equal(df['I (V)'].to_numpy(), self.I)
        np.testing.assert_array_equal(df['Q (V)'].to_numpy(), self.Q)
        # |I + jQ| = 0.01 for the unit tone.
        np.testing.assert_allclose(
            df['mag (V)'].to_numpy(), 0.01 * np.ones(self.n),
            rtol=0, atol=1e-6)

    def test_metadata_attrs(self):
        df = read_iqvsa(self.path)
        meta = df.attrs.get('cicsim_iqvsa')
        self.assertIsNotNone(meta)
        self.assertEqual(meta['sampling_rate_hz'], self.fs)
        self.assertEqual(meta['sample_count'], self.n)
        self.assertAlmostEqual(meta['center_freq_hz'], 2.412e9)
        self.assertAlmostEqual(meta['capture_time_s'], 20e-3)
        self.assertIn('LitePoint', meta['idn'])
        self.assertIn('FREQuency:CENTer', meta['config'])

    def test_dispatch_via_wavefile(self):
        wf = WaveFile(self.path, xaxis=None)
        self.assertIn('time', wf.getWaveNames())
        self.assertIn('I (V)', wf.getWaveNames())
        wave = wf.getWave('I (V)')
        self.assertEqual(wave.xunit, 's')
        self.assertEqual(wave.yunit, 'V')
        np.testing.assert_array_equal(wave.y, self.I)

    def test_rejects_missing_header(self):
        bad = tempfile.NamedTemporaryFile(suffix='.iqvsa', delete=False)
        try:
            bad.write(b'not an LP header at all')
            bad.close()
            with self.assertRaises(ValueError):
                read_iqvsa(bad.name)
        finally:
            os.unlink(bad.name)

    def test_rejects_payload_size_mismatch(self):
        # Declare 1024 samples but write only enough bytes for 100.
        truncated = tempfile.NamedTemporaryFile(
            suffix='.iqvsa', delete=False)
        try:
            blob = _make_iqvsa_bytes(self.I, self.Q, fs=self.fs)
            # Drop the trailing samples to break the size invariant.
            truncated.write(blob[:-2000])
            truncated.close()
            with self.assertRaises(ValueError):
                read_iqvsa(truncated.name)
        finally:
            os.unlink(truncated.name)


class IQVSAModuleConfigParseTest(unittest.TestCase):

    def test_basic_floats_and_strings(self):
        text = (
            "VSA1;\n"
            "FREQuency:CENTer 2.412000e+09;\n"
            "RLEVel 0.000000e+00;\n"
            "INTernal:PORT:NAME RF1A;\n"
            "TRIGger:MODE SSHot;\n"
        )
        cfg = _iqvsa_parse_module_config(text)
        self.assertAlmostEqual(cfg['FREQuency:CENTer'], 2.412e9)
        self.assertAlmostEqual(cfg['RLEVel'], 0.0)
        self.assertEqual(cfg['INTernal:PORT:NAME'], 'RF1A')
        self.assertEqual(cfg['TRIGger:MODE'], 'SSHot')


if __name__ == '__main__':
    unittest.main()
