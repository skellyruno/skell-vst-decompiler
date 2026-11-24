import unittest
import numpy as np
from skell_vst_decompiler.advanced_dsp import split_pitch,recovery_continuous,two_tone_imd


class AdvancedTests(unittest.TestCase):
    def test_pitch_center_and_gap(self):
        t=np.arange(400)*.01;truth=20+10*t;v=25*np.sin(2*np.pi*5*t)
        z=truth+v;z[180:200]=np.nan
        c,w=split_pitch(z)
        self.assertTrue(np.all(np.isnan(c[180:200])))
        self.assertLess(np.sqrt(np.mean((c[250:]-truth[250:])**2)),3.)
        self.assertLess(np.sqrt(np.mean((w[250:]-v[250:])**2)),3.)
        a,b=split_pitch([20,20,150,150]);self.assertEqual(a[2],150.)

    def test_off_grid_recovery(self):
        t=np.arange(0.,1200.,10.);y=7*np.exp(-t/47.)+5*np.exp(-t/483.)
        r=recovery_continuous(t,y)
        np.testing.assert_allclose(r['2']['tau_ms'],[47,483],rtol=1e-4)
        self.assertLess(r['2']['heldout_rmse'],1e-5)
        self.assertGreater(r['1']['heldout_rmse'],.05)

    def test_two_tone_products(self):
        fs=48000;t=np.arange(fs)/fs;x=.25*(np.sin(2*np.pi*1700*t)+np.sin(2*np.pi*2300*t))
        a=two_tone_imd(x+.4*x*x,fs);b=two_tone_imd(x+.4*x*x*x,fs)
        self.assertGreater(a['imd2_db'],-40);self.assertLess(a['imd3_db'],-180)
        self.assertGreater(b['imd3_db'],-50);self.assertLess(b['imd2_db'],-180)
        with self.assertRaises(ValueError):two_tone_imd(x[:101],fs)

if __name__=='__main__':unittest.main()
