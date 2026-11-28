import unittest
import numpy as np
from skell_vst_decompiler.adaptive_behavior import envelope_features,predict,fit_envelopes,bandlimited_tone,isolated_echoes
class Tests(unittest.TestCase):
    def test_projection(self):
        x=np.random.default_rng(1).normal(0,.1,(4800,2));r=envelope_features(x,x*.5,48000);self.assertTrue(np.all(r['valid']));np.testing.assert_allclose(r['gain_db'],20*np.log10(.5),atol=1e-12)
    def test_known_adaptive(self):
        p=[-24,.7,.01,.08,.3,.6,1.5];rng=np.random.default_rng(2);rows=[]
        for _ in range(3):
            peak=np.repeat(rng.uniform(.01,.9,20),20);rows.append(dict(peak=peak,dt=.005,gain_db=predict(peak,.005,p,'adaptive'),valid=np.ones(len(peak),bool)))
        r=fit_envelopes(rows[:2],rows[2:]);self.assertLess(r[-1]['holdout_rmse_db'],1e-6);self.assertGreater(r[0]['holdout_rmse_db'],.01)
    def test_bandlimited(self):
        for fs in (44100,48000,96000):
            y=bandlimited_tone(fs,4000,.5);z=np.abs(np.fft.rfft(y))/fs;z[[4000,8000,12000]]=0;self.assertLess(max(z),1e-10)
        with self.assertRaises(ValueError):bandlimited_tone(48000,9000,0)
    def test_echoes(self):
        x=np.zeros(48000);x[[480,9600,19200]]=[.5,-.3,.2];r=isolated_echoes(x,48000);self.assertEqual([v['sample'] for v in r],[480,9600,19200]);self.assertEqual(r[1]['signed_peak'],-.3)
    def test_invalid(self):
        with self.assertRaises(ValueError):predict([.5],.005,[-24,.7,0,.1],'single')
        with self.assertRaises(ValueError):isolated_echoes([np.nan],48000)
        with self.assertRaises(ValueError):envelope_features(np.zeros((10,2)),np.zeros((10,1)),48000)
