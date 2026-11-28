import math
import unittest
import numpy as np
from skell_vst_decompiler.pitch_reference import estimate


class PitchReferenceTest(unittest.TestCase):
    def test_harmonic_and_missing_fundamental(self):
        for fs in (44100,48000,96000):
            t=np.arange(int(fs*.065))/fs
            for hz in (82.41,110.,220.,440.,880.):
                for harmonics in ((1,2,3),(2,3,4)):
                    x=sum(np.sin(2*np.pi*hz*h*t)/h for h in harmonics)
                    f,c=estimate(x,fs)
                    self.assertIsNotNone(f)
                    self.assertLess(abs(1200*math.log2(f/hz)),2.)
                    self.assertGreater(c,.9)

    def test_unvoiced_and_invalid(self):
        fs=48000
        self.assertEqual(estimate(np.zeros(4096),fs),(None,0.))
        self.assertEqual(estimate(np.random.default_rng(42).normal(size=4096),fs),(None,0.))
        with self.assertRaises(ValueError):estimate([0.,1.],fs)
        with self.assertRaises(ValueError):estimate([float('nan')]*4096,fs)

if __name__=='__main__':unittest.main()
