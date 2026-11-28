import unittest
import numpy as np
from skell_vst_decompiler.topology_gate import screen,knee_models,knee_curve,release_signature,stereo_intervention,candidate_gate
class Tests(unittest.TestCase):
    def test_screen(self):
        x=np.random.default_rng(1).uniform(-.5,.5,(1024,2));z=x[::-1].copy();a=x.copy();a[:512]*=2
        for f,expected in [(lambda v:v,[]),(lambda v:v**3,['linear']),(lambda v:np.cumsum(v,axis=0),['memoryless'])]:
            y=[f(v) for v in (x,x,.5*x,z,x+z,a)];self.assertEqual(screen(y,512)['rejected'],expected)
    def test_repeat(self):
        x=np.ones((100,2));self.assertIn('deterministic_fixed_state',screen([x,x*.8,x*.5,x,x*2,x],50)['rejected'])
    def test_knee(self):
        x=np.arange(-50.,0,1);m=np.arange(len(x))%3!=1
        for width in (0,12):
            r=knee_models(x,knee_curve(x,-24,.75,width),m);self.assertLess(r[bool(width)]['holdout_rmse_db'],1e-7)
            if width:self.assertGreater(r[0]['holdout_rmse_db'],.1)
    def test_release(self):
        t=np.arange(100)*.01;v=np.stack([6*np.exp(-t/.1),12*np.exp(-np.maximum(t-.2,0)/.3)])
        r=release_signature(v,.01);self.assertEqual(r[0]['t50_seconds'],.07);self.assertGreater(r[1]['first_10pct_drop_seconds'],.2)
    def test_stereo(self):
        x=np.ones((100,2));y=x.copy();y[:,1]*=.5;self.assertEqual(stereo_intervention(x,y,0),0);self.assertAlmostEqual(stereo_intervention(x,y,1),-6.020599913,8)
    def test_invalid(self):
        with self.assertRaises(ValueError):screen(np.zeros((6,32,2)),32)
        with self.assertRaises(ValueError):release_signature(np.zeros((2,32)),.01)
    def test_gate(self):
        r=dict(silent=False,rejected=['memoryless'],threshold=.001)
        self.assertEqual(candidate_gate(r,.1)['eligible'],['linear_time_varying','nonlinear_stateful'])
        r['rejected']=['deterministic_fixed_state'];self.assertEqual(candidate_gate(r,0)['action'],'RECAPTURE')
