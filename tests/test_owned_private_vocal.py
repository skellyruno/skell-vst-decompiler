"""Analytical controls for the private-audio measurement harness."""
import unittest
try:
    import numpy as np
    from benchmarks.owned_private_vocal import compare,match,rms,estimate_peak
except ModuleNotFoundError:
    np=None


@unittest.skipUnless(np is not None,'requires NumPy, SciPy and SoundFile')
class PrivateVocalMetricTests(unittest.TestCase):
    def test_identity(self):
        t=np.arange(8192)/48000
        x=np.column_stack((.4*np.sin(2*np.pi*1000*t),.2*np.cos(2*np.pi*3000*t)))
        m=compare(x,x,48000)
        self.assertAlmostEqual(m['raw_gain_db'],0,places=10)
        self.assertAlmostEqual(m['matched_peak_delta_db'],0,places=10)
        self.assertTrue(all(abs(v)<1e-10 for v in m['matched_band_delta_db']))
        self.assertLess(m['matched_null_db'],-250)
        self.assertEqual(m['raw_samples_over_full_scale'],0)

    def test_level_matching_and_clipping_count(self):
        x=np.array([[.8,.2],[-.6,.3],[.4,-.2],[-.1,.1]]*1024)
        y=2*x;m=compare(x,y,44100)
        self.assertAlmostEqual(m['raw_gain_db'],6.020599913,places=8)
        self.assertAlmostEqual(rms(match(y,x)),rms(x),places=12)
        self.assertEqual(m['raw_samples_over_full_scale'],2048)
        self.assertLess(m['matched_null_db'],-250)
        self.assertGreater(estimate_peak(y),1)

    def test_silence_rejected(self):
        with self.assertRaises(ValueError):match(np.zeros((128,2)),np.ones((128,2)))
