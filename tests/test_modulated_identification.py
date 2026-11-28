import unittest
import numpy as np
from experiments.modulated_identification import predict,select
from experiments.multirate_diagnostic import color,signature
class Tests(unittest.TestCase):
    def test_integer(self):
        x=np.arange(100)/100.;p=[1,0,1,0,1]
        for k in ('linear','cubic'):np.testing.assert_allclose(predict(x,8000,p,k),np.r_[np.zeros(8),x[:-8]],atol=1e-14)
    def test_fractional(self):
        x=np.arange(100)/100.;p=[1.0625,0,1,0,1];a=predict(x,8000,p,'linear');np.testing.assert_allclose(a[10:],(np.arange(10,100)-8.5)/100)
    def test_invalid(self):
        with self.assertRaises(ValueError):predict(np.zeros(100),48000,[1,2,1,0,1],'linear')
    def test_alias(self):
        fs=48000;hz=9973;t=np.arange(3*fs)/fs;x=.6*np.sin(2*np.pi*hz*t)
        a=signature(color(x,1)[fs:2*fs],fs,hz);b=signature(color(x,8)[fs:2*fs],fs,hz);self.assertLess(b['nonharmonic_db'],a['nonharmonic_db']-30)
    def test_tone(self):
        fs=48000;y=.5*np.sin(2*np.pi*997*np.arange(fs)/fs);r=signature(y,fs,997);self.assertAlmostEqual(r['fundamental_peak'],.5,10);self.assertLess(r['nonharmonic_db'],-200)
    def test_select(self):
        a=np.random.default_rng(9).uniform(-.5,.5,48000);b=np.random.default_rng(10).uniform(-.5,.5,44100);p=[7.4,.8,.91,.4,.73]
        for k in ('linear','cubic'):
            r=select((a,predict(a,48000,p,k),48000),(b,predict(b,44100,p,k),44100));self.assertEqual(r['selected']['kind'],k)
    def test_span(self):
        fs=48000;hz=8161;x=.7*np.sin(2*np.pi*hz*np.arange(3*fs)/fs)
        a=signature(color(x,4,span=10)[fs:2*fs],fs,hz);b=signature(color(x,4,span=200)[fs:2*fs],fs,hz);self.assertLess(b['nonharmonic_db'],a['nonharmonic_db']-60)
