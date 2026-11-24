import math
import unittest
import numpy as np
from skell_vst_decompiler.historical_pitch_reference import estimate,period_error
from skell_vst_decompiler.gain_response import gain_blocks,fit_relaxation


class HistoricalPitchTests(unittest.TestCase):
    def test_energy_identity(self):
        x=np.array([1.,2.,3.,4.,5.,6.])
        a,b=x[:3],x[3:]
        expected=1-2*np.dot(a,b)/(np.dot(a,a)+np.dot(b,b))
        self.assertAlmostEqual(period_error(x,3),expected)
        self.assertEqual(period_error(np.tile(a,2),3),0.)

    def test_stationary_and_missing_fundamental(self):
        for fs in (44100,48000,96000):
            t=np.arange(int(fs*.065))/fs
            for hz in (82.41,110.,220.,440.,880.):
                for hs in ((1,2,3),(2,3,4)):
                    x=sum(np.sin(2*np.pi*hz*h*t)/h for h in hs)
                    f,c=estimate(x,fs)
                    self.assertIsNotNone(f)
                    self.assertLess(abs(1200*math.log2(f/hz)),3.)
                    self.assertGreater(c,.9)

    def test_reject_unvoiced(self):
        self.assertEqual(estimate(np.zeros(4096),48000),(None,0.))
        self.assertEqual(estimate(np.random.default_rng(42).normal(size=4096),48000),(None,0.))
        with self.assertRaises(ValueError):estimate(np.zeros(10),48000)


class GainResponseTests(unittest.TestCase):
    def test_known_stereo_gain_and_residual(self):
        t=np.arange(4800)/48000
        x=np.column_stack((np.sin(2*np.pi*500*t),.5*np.sin(2*np.pi*500*t)))
        rows=gain_blocks(x,.25*x,48000)
        self.assertEqual(len(rows),10)
        for r in rows:
            self.assertAlmostEqual(r['scalar_gain'],.25)
            self.assertAlmostEqual(r['rms_gain_db'],20*math.log10(.25))
            self.assertLess(r['residual_relative_rms'],1e-12)
        self.assertEqual(gain_blocks(np.zeros(4800),np.zeros(4800),48000),[])
        with self.assertRaises(ValueError):gain_blocks(x,x[:-1],48000)

    def test_recovery_fit(self):
        t=np.arange(20)*10.
        y=1-.8*np.exp(-t/75.)
        r=fit_relaxation(t,y,1.)
        self.assertAlmostEqual(r['tau_ms'],75.)
        self.assertLess(r['rmse'],1e-12)
        self.assertIsNone(fit_relaxation(t,np.ones(len(t)),1.))

if __name__=='__main__':unittest.main()
