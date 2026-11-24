import unittest
import numpy as np
from skell_vst_decompiler.gated_pitch import estimate
from skell_vst_decompiler.adaptive_research import adaptive_pitch
from skell_vst_decompiler.recovery_alternatives import compare_recovery
from skell_vst_decompiler.alias_measure import measure
from skell_vst_decompiler.saturation_reference import saturate


class ResearchGateTests(unittest.TestCase):
    def test_pitch_gate_and_prefix_causality(self):
        t=np.arange(600)*.01;truth=20+10*t
        noise=np.random.default_rng(500).normal(0,3,len(t))
        flat=truth+noise;c,v,f,s=estimate(flat)
        self.assertTrue(np.all(np.isnan(f[150:])))
        self.assertLess(np.sqrt(np.mean(v[150:]**2)),.1)
        y=truth+25*np.sin(2*np.pi*4.7*t)+noise
        a,b,_=adaptive_pitch(y);c,v,f,s=estimate(y)
        self.assertLess(np.sqrt(np.mean((c[150:]-truth[150:])**2)),np.sqrt(np.mean((a[150:]-truth[150:])**2)))
        self.assertGreater(np.mean(np.isfinite(f[150:])),.95)
        for short,long in zip(estimate(y[:300]),(c,v,f,s)):
            np.testing.assert_allclose(short,long[:300],equal_nan=True)
        y[200:220]=np.nan;c,v,f,s=estimate(y)
        self.assertTrue(np.all(np.isnan(c[200:220])))
        self.assertTrue(np.all(np.isnan(f[220:230])))
        c,v,f,s=estimate([20,20,150,150]);self.assertAlmostEqual(c[2],150.,places=10)

    def test_alternative_recovery(self):
        t=np.arange(0.,1200.,10.);noise=np.random.default_rng(291).normal(0,.03,len(t))
        x=12*np.exp(-(t/180)**.55)+noise;r=compare_recovery(t,x,.03)
        self.assertEqual(r['previous_preference'],'dual_descriptive_preferred')
        self.assertEqual(r['preference'],'dual_not_established')
        self.assertAlmostEqual(r['stretched']['beta'],.55,delta=.02)
        y=7*np.exp(-t/47)+5*np.exp(-t/483)+noise;r=compare_recovery(t,y,.03)
        self.assertEqual(r['preference'],'dual_descriptive_preferred')

    def test_nonharmonic_power(self):
        fs=48000;t=np.arange(fs)/fs
        x=np.sin(2*np.pi*1000*t)+.1*np.sin(2*np.pi*2000*t)+.01*np.sin(2*np.pi*3001*t)
        r=measure(x,fs,1000)
        self.assertAlmostEqual(r['nonharmonic_db'],-40,places=6)
        self.assertAlmostEqual(r['harmonic_distortion_db'],-20,places=6)
        x=.8*np.sin(2*np.pi*7001*t)
        a=measure(saturate(x,4.,antialias=False),fs,7001)
        b=measure(saturate(np.r_[x[-1],x],4.)[1:],fs,7001)
        self.assertLess(b['nonharmonic_db'],a['nonharmonic_db']-10)
        with self.assertRaises(ValueError):measure(x[:101],fs,7001)


if __name__=='__main__':unittest.main()
