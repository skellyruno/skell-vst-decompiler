import unittest
import numpy as np
from skell_vst_decompiler.heldout_models import compare_surfaces,detector_models,tail_windows

class Tests(unittest.TestCase):
    def test_interaction(self):
        x=np.array([(a,b) for a in (-1,0,1) for b in (-1,0,1)])
        z=np.array([(-.5,.5),(.5,.5),(.5,-.5),(-.5,-.5)])
        f=lambda q: 1+q[:,0]+2*q[:,1]+3*q[:,0]*q[:,1]
        r=compare_surfaces(x,f(x),z,f(z))
        self.assertLess(r[1]['heldout_rmse'],1e-12);self.assertGreater(r[0]['heldout_rmse'],.5)
    def test_leakage(self):
        x=np.array([(a,b) for a in (-1,0,1) for b in (-1,0,1)])
        with self.assertRaises(ValueError):compare_surfaces(x,x[:,0],x[:3],x[:3,0])
    def test_quadratic(self):
        x=np.array([(a,b) for a in (-1,0,1) for b in (-1,0,1)]);z=np.array([(-.5,.5),(.5,.5),(.5,-.5),(-.5,-.5)])
        f=lambda q:q[:,0]**2+q[:,1]**2
        r=compare_surfaces(x,f(x),z,f(z));self.assertLess(r[2]['heldout_rmse'],1e-12)
    def test_detectors(self):
        p=np.tile([.1,.3,.7],4);r=p*np.repeat([.8,.4,.2,.6],3);mask=np.arange(12)<6
        for i,v in enumerate((p,r)):
            z=detector_models(p,r,-.7*20*np.log10(v),mask);self.assertLess(z[i]['heldout_rmse_db'],1e-12);self.assertGreater(z[1-i]['heldout_rmse_db'],1)
    def test_tail(self):
        x=np.zeros((8000,2));x[:800]=.01
        r=tail_windows(x,8000);self.assertEqual(r['last_active_ms'],100);self.assertFalse(r['right_censored'])
        x[-800:]=.01;self.assertTrue(tail_windows(x,8000)['right_censored'])
    def test_bad_input(self):
        with self.assertRaises(ValueError):tail_windows([[np.nan,0]],48000)
        with self.assertRaises(ValueError):detector_models([1]*6,[0]*6,[0]*6,np.array([1,1,1,0,0,0],bool))
    def test_recurrence(self):
        from skell_vst_decompiler.heldout_models import recurrence_models
        t=np.arange(120); a=.8**t+.3*.6**t;b=.4*.8**t-.2*.6**t
        r=recurrence_models(a,b);self.assertLess(r[1]['heldout_relative_error'],1e-10);self.assertGreater(r[0]['heldout_relative_error'],.01)
    def test_rounding_and_rank(self):
        from skell_vst_decompiler.heldout_models import recurrence_models
        t=np.arange(120);r=recurrence_models(.8**t,.5*.8**t)
        self.assertEqual(r[1]['status'],'UNIDENTIFIABLE')
        p=np.tile([.1,.3,.7],2);r=p*(1+1e-15)
        self.assertEqual(len(detector_models(p,r,p,np.arange(6)<3)),2)
