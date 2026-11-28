import unittest
import numpy as np
from skell_vst_decompiler.gated_pitch import estimate as baseline
from skell_vst_decompiler.motion_pitch import estimate as challenger
from skell_vst_decompiler.coloration_compare import compare,oversampled
from skell_vst_decompiler.saturation_reference import saturate


class MotionColorTests(unittest.TestCase):
    def test_slow_motion_and_weak_vibrato(self):
        t=np.arange(600)*.01;truth=20+10*t
        noise=np.random.default_rng(101).normal(0,3,len(t))
        slow=truth+25*np.sin(2*np.pi*1.3*t)
        a,_,_,_=baseline(slow+noise);c,v,f,s=challenger(slow+noise)
        self.assertLess(np.sqrt(np.mean((c[150:]-slow[150:])**2)),2.)
        self.assertGreater(np.sqrt(np.mean((a[150:]-slow[150:])**2)),10.)
        self.assertFalse(np.any(np.isfinite(f[150:])))
        weak=truth+4*np.sin(2*np.pi*4.7*t)+noise
        a,_,_,_=baseline(weak);c,v,f,s=challenger(weak)
        self.assertGreater(np.mean(np.isfinite(f[150:])),.9)
        self.assertLess(np.sqrt(np.mean((c[150:]-truth[150:])**2)),np.sqrt(np.mean((a[150:]-truth[150:])**2)))

    def test_prefix_and_gap(self):
        t=np.arange(300)*.01;y=20+25*np.sin(2*np.pi*5*t);y[100:120]=np.nan
        full=challenger(y)
        for short,long in zip(challenger(y[:170]),full):
            np.testing.assert_allclose(short,long[:170],equal_nan=True)
        self.assertTrue(np.all(np.isnan(full[0][100:120])))
        self.assertTrue(np.all(np.isnan(full[2][120:130])))
        with self.assertRaises(ValueError):challenger([np.inf])

    def test_gain_and_phase_matching(self):
        fs=48000;t=np.arange(fs)/fs
        ref=np.sin(2*np.pi*997*t)+.1*np.sin(2*np.pi*2991*t)
        candidate=.5*np.roll(ref,3)
        r=compare(candidate,ref,fs,997)
        self.assertAlmostEqual(r['fundamental_gain_to_reference_db'],20*np.log10(2),places=9)
        self.assertAlmostEqual(r['phase_equivalent_shift_samples'],-3,places=9)
        self.assertLess(r['matched_error_db'],-180)
        self.assertGreater(r['raw_error_db'],-10)

    def test_oversampling_and_bounds(self):
        fs=48000;f=11003;n=fs*16
        x=.8*np.sin(2*np.pi*f*np.arange(fs)/fs)
        hi=saturate(.8*np.sin(2*np.pi*f*np.arange(n)/n),4,antialias=False)
        spec=np.fft.rfft(hi)[:fs//2+1]/16;spec[-1]=0
        ref=np.fft.irfft(spec,fs)
        a=compare(saturate(x,4,antialias=False),ref,fs,f)
        b=compare(oversampled(x,4,4),ref,fs,f)
        self.assertLess(b['matched_error_db'],a['matched_error_db']-30)
        self.assertEqual(oversampled(np.ones(128)).shape,(128,))
        with self.assertRaises(ValueError):oversampled(x,4,3)
        with self.assertRaises(ValueError):compare(x[:101],ref[:101],fs,f)


if __name__=='__main__':unittest.main()
