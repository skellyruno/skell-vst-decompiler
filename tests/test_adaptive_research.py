import unittest
import numpy as np
from skell_vst_decompiler.adaptive_research import adaptive_pitch,assess_recovery
from skell_vst_decompiler.advanced_dsp import split_pitch,recovery_continuous


class AdaptiveResearchTests(unittest.TestCase):
    def test_off_frequency_and_chirp(self):
        t=np.arange(600)*.01;truth=20+10*t;rng=np.random.default_rng(901)
        for f in (3.5,4.,4.7,5.7,6.,7.,7.5):
            v=25*np.sin(2*np.pi*f*t);y=truth+v+rng.normal(0,3,len(t))
            a,b=split_pitch(y);c,d,e=adaptive_pitch(y)
            self.assertLess(np.sqrt(np.mean((c[150:]-truth[150:])**2)),np.sqrt(np.mean((a[150:]-truth[150:])**2)))
            self.assertLess(abs(np.mean(e[150:])-f),.5)
        y=truth+25*np.sin(2*np.pi*(3.5*t+.35*t*t));c,d,e=adaptive_pitch(y)
        self.assertLess(np.sqrt(np.mean((c[150:]-truth[150:])**2)),3.)

    def test_reset_and_no_vibrato(self):
        t=np.arange(400)*.01;truth=20+10*t
        x=truth+np.random.default_rng(8).normal(0,3,len(t));x[180:200]=np.nan
        c,v,f=adaptive_pitch(x)
        self.assertTrue(np.all(np.isnan(c[180:200])))
        self.assertLess(np.sqrt(np.mean(v[250:]**2)),3.)
        c,v,f=adaptive_pitch([20,20,150,150]);self.assertEqual(c[2],150.)
        with self.assertRaises(ValueError):adaptive_pitch([np.inf])

    def test_recovery_gate(self):
        t=np.arange(0.,1200.,10.);rng=np.random.default_rng(20)
        for dual in (False,True):
            y=(7*np.exp(-t/47)+5*np.exp(-t/483) if dual else 12*np.exp(-t/137))+rng.normal(0,.03,len(t))
            got=assess_recovery(recovery_continuous(t,y),.03)
            self.assertEqual(got,'dual_descriptive_preferred' if dual else 'dual_not_established')
        with self.assertRaises(ValueError):assess_recovery({},0)


if __name__=='__main__':unittest.main()
