import unittest
import numpy as np
from skell_vst_decompiler.spectral_probe import probe, measure


class SpectralProbeTests(unittest.TestCase):
    def test_selective_and_broad_gain(self):
        for fs in (44100, 48000, 96000, 192000):
            a = probe(fs, (100, 1000, 9000))
            t = np.arange(fs) / fs
            b = a.copy()
            b[:, 0] -= .125 * np.sin(2 * np.pi * 100 * t)
            b[:, 1] *= .5
            r = measure(fs, (100, 1000, 9000), a, b)
            self.assertAlmostEqual(r['tones'][0]['channels'][0]['gain_db'], 20*np.log10(.25), places=8)
            for row in r['tones'][1:]:
                self.assertAlmostEqual(row['channels'][0]['gain_db'], 0, places=8)
            for row in r['tones']:
                self.assertAlmostEqual(row['channels'][1]['gain_db'], 20*np.log10(.5), places=8)
            self.assertLess(max(r['processed_residual_rms']), 1e-10)

    def test_phase_and_residual(self):
        fs = 48000
        a = probe(fs, (1000,))
        b = np.roll(a, 12, axis=0)
        b[:, 0] += .1 * np.sin(2*np.pi*1500*np.arange(fs)/fs)
        r = measure(fs, (1000,), a, b)
        self.assertAlmostEqual(r['tones'][0]['channels'][0]['phase_deg'], -90)
        self.assertAlmostEqual(r['processed_residual_rms'][0], .1/np.sqrt(2))

    def test_missing_and_silent_tone(self):
        a = probe(8000, (100,))
        a[:, 1] = 0
        r = measure(8000, (100,), a, np.zeros_like(a))
        self.assertIsNone(r['tones'][0]['channels'][1])
        self.assertIsNone(r['tones'][0]['channels'][0]['phase_deg'])
        self.assertEqual(r['tones'][0]['channels'][0]['gain_db'], -240)

    def test_reject_bad_inputs(self):
        a = probe(8000, (100,))
        for f in ((100, 100), (4000,), (0,), (100.5,), ()):
            with self.assertRaises(ValueError): probe(8000, f)
        with self.assertRaises(ValueError): measure(8000, (100,), a[:-1], a)
        a[0, 0] = np.nan
        with self.assertRaises(ValueError): measure(8000, (100,), a, a)
