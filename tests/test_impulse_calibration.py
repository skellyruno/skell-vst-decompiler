import unittest
import numpy as np
from skell_vst_decompiler.impulse_calibration import inspect_impulse


class ImpulseTests(unittest.TestCase):
    def test_signed_delays_and_cross_channel(self):
        x=np.zeros((1024,2));y=x.copy();x[11,1]=-.5;y[148,1]=-.5;y[285,1]=-.25;y[150,0]=.125
        r=inspect_impulse(x,y,48000,reported_latency=0)
        self.assertEqual(r['outputs'][1]['first_arrival_samples'],137)
        self.assertEqual(r['outputs'][1]['echo_peaks'],[{'offset_samples':137,'gain':1.},{'offset_samples':274,'gain':.5}])
        self.assertEqual(r['outputs'][0]['peak_gain'],-.25)
        self.assertEqual(r['outputs'][0]['first_arrival_samples'],139)

    def test_pre_input_and_silent(self):
        x=np.zeros((64,2));y=x.copy();x[10,0]=.5;y[5,0]=.25
        r=inspect_impulse(x,y,48000,reported_latency=128)
        self.assertEqual(r['outputs'][0]['first_arrival_samples'],-5)
        self.assertEqual(r['outputs'][0]['pre_input_peak'],.5)
        self.assertIsNone(r['outputs'][1]['first_arrival_samples'])
        self.assertEqual(r['reported_latency_samples'],128)

    def test_bad_inputs(self):
        x=np.zeros((64,2));y=x.copy()
        with self.assertRaises(ValueError):inspect_impulse(x,y,48000)
        x[0,0]=.5;x[1,0]=.1
        with self.assertRaises(ValueError):inspect_impulse(x,y,48000)
        x[1,0]=0;y[5,0]=np.nan
        with self.assertRaises(ValueError):inspect_impulse(x,y,48000)


if __name__=='__main__':unittest.main()
