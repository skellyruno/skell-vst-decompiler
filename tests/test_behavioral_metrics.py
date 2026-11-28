import unittest
import numpy as np
from skell_vst_decompiler.behavioral_metrics import block_gain,tone_products,sidebands

class RenderMetrics(unittest.TestCase):
    def test_known_gain_and_residual(self):
        fs=48000;t=np.arange(fs)/fs
        x=np.sin(2*np.pi*1000*t);a=np.column_stack((x,x));b=a.copy();b[:,0]*=.5;b[:,1]*=.25
        b[:,0]+=.1*np.cos(2*np.pi*1000*t)
        r=block_gain(fs,a,b)
        np.testing.assert_allclose(r['gain'],np.tile([.5,.25],(100,1)),atol=1e-12)
        np.testing.assert_allclose(np.array(r['residual_rms'])[:,0],.1/np.sqrt(2),atol=1e-12)
    def test_silence_and_tail(self):
        a=np.zeros((481,2));r=block_gain(48000,a,a)
        self.assertEqual(r['discarded_samples'],1);self.assertEqual(r['gain'],[[None,None]])
    def test_fold_and_collision(self):
        fs=48000;t=np.arange(fs)/fs;x=np.sin(2*np.pi*11000*t)+.1*np.sin(2*np.pi*15000*t)
        r={v['hz']:v for v in tone_products(fs,11000,np.column_stack((x,x)))}
        self.assertAlmostEqual(r[15000]['amplitude'][0],.1)
        self.assertTrue(r[15000]['origins'][0]['fold_candidate'])
        r=tone_products(fs,12000,np.column_stack((x,x)))
        self.assertTrue(any(v['ambiguous'] for v in r))
    def test_am_sidebands(self):
        fs=44100;t=np.arange(fs)/fs;x=np.sin(2*np.pi*1000*t)*(1+.4*np.cos(2*np.pi*4*t))
        r={v['order']:v for v in sidebands(fs,1000,4,np.column_stack((x,x)))}
        self.assertAlmostEqual(r[-1]['amplitude'][0],.2);self.assertAlmostEqual(r[1]['amplitude'][0],.2)
        self.assertAlmostEqual(r[0]['amplitude'][0],1.)
    def test_validation(self):
        a=np.zeros((8000,2))
        with self.assertRaises(ValueError):block_gain(8000,a,a[:-1])
        with self.assertRaises(ValueError):tone_products(8000,4000,a)
        with self.assertRaises(ValueError):sidebands(8000,3999,2,a)
        a[0,0]=np.nan
        with self.assertRaises(ValueError):block_gain(8000,a,a)
