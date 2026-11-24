import math
import unittest
import numpy as np
from skell_vst_decompiler.pitch_reference import estimate,difference_fft
from skell_vst_decompiler.pitch_control import RetuneControl
from skell_vst_decompiler.saturation_reference import saturate


class IndependentDSPTests(unittest.TestCase):
    def test_fft_difference_identity(self):
        rng=np.random.default_rng(271)
        x=rng.normal(size=1200)
        last=240;width=len(x)-last-1
        direct=np.array([0.]+[np.dot(x[:width]-x[i:i+width],x[:width]-x[i:i+width]) for i in range(1,last+2)])
        np.testing.assert_allclose(difference_fft(x,width,last),direct,rtol=1e-10,atol=1e-9)

    def test_pitch_backend_equivalence(self):
        rng=np.random.default_rng(42)
        for fs in (44100,48000,96000):
            t=np.arange(int(fs*.065))/fs
            for hz in (82.41,220.,880.):
                for noise in (0.,.03,.1):
                    x=sum(np.sin(2*np.pi*hz*h*t)/h for h in (1,2,3))+rng.normal(0.,noise,len(t))
                    a,b=estimate(x,fs),estimate(x,fs,backend='fft')
                    self.assertIsNotNone(a[0])
                    self.assertAlmostEqual(a[0],b[0],places=7)
                    self.assertAlmostEqual(a[1],b[1],places=9)
        noise=rng.normal(size=4096)
        self.assertEqual(estimate(noise,48000,backend='fft'),(None,0.))

    def test_retune_time_and_hysteresis(self):
        hz=lambda m:440*2**((m-69)/12)
        for ms in (0.,20.,100.):
            c=RetuneControl(retune_ms=ms)
            note,offset=c.step(hz(69.25),1.,10.)
            self.assertEqual(note,69)
            self.assertAlmostEqual(offset,-25 if ms==0 else -25*(1-math.exp(-10/ms)))
        c=RetuneControl(retune_ms=0.)
        self.assertEqual(c.step(hz(69.4),1.,10.)[0],69)
        self.assertEqual(c.step(hz(69.55),1.,10.)[0],69)
        self.assertEqual(c.step(hz(69.65),1.,10.)[0],70)
        self.assertEqual(c.step(hz(69.45),1.,10.)[0],70)
        self.assertEqual(c.step(None,0.,10.),(None,0.))
        self.assertEqual(c.step(hz(69.45),1.,10.)[0],69)

    def test_saturation_finite_dc_and_bounds(self):
        for drive in (.1,3.,20.):
            x=np.repeat(.25,256)
            np.testing.assert_allclose(saturate(x,drive),saturate(x,drive,antialias=False),atol=1e-12)
            y=saturate(np.linspace(-1,1,2048),drive)
            self.assertTrue(np.all(np.isfinite(y)))
            self.assertLessEqual(np.max(np.abs(y)),1.+1e-10)
        with self.assertRaises(ValueError):saturate([float('nan')])

if __name__=='__main__':unittest.main()
