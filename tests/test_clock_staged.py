import unittest
import numpy as np
from experiments.phase_clock import interpolate,infer_delay
from experiments.staged_color import staged,response,design
from experiments.multirate_diagnostic import color,signature
class Tests(unittest.TestCase):
    def test_interpolate(self):
        x=np.arange(128,dtype=float);d=np.full(len(x),3.5);np.testing.assert_allclose(interpolate(x,d)[4:],x[4:]-3.5)
    def test_track(self):
        x=np.random.default_rng(13).uniform(-1,1,(6,4096));d=7.5+.8*np.sin(np.arange(4096)*.01);y=np.stack([interpolate(v,d) for v in x]);a,b=infer_delay(x,y,d+.3,3);np.testing.assert_allclose(a[32:],d[32:],atol=1e-11);self.assertLess(np.max(b[32:]),1e-12)
    def test_bad(self):
        with self.assertRaises(ValueError):interpolate(np.ones(32),np.full(32,-1.))
        with self.assertRaises(ValueError):infer_delay(np.ones((2,32)),np.ones((2,32)),np.ones(32))
    def test_filter(self):
        r=response(641,.49);self.assertLess(r['stop_max_db'],-100);self.assertLess(r['pass_ripple_db'],.001);self.assertFalse(design(641,.49).flags.writeable)
    def test_staged_tone(self):
        fs=48000;hz=8161;x=.7*np.sin(2*np.pi*hz*np.arange(3*fs)/fs);a=signature(color(x,4,span=200)[fs:2*fs],fs,hz);b=signature(staged(x)[fs:2*fs],fs,hz);self.assertLess(b['nonharmonic_db'],a['nonharmonic_db']+3);self.assertLess(abs(b['fundamental_peak']-a['fundamental_peak']),.0001)
