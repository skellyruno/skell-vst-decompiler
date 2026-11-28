import unittest
import itertools
import numpy as np
from skell_vst_decompiler.envelope_research import recovery_models,detector_frequency_models,surfaces3

class Tests(unittest.TestCase):
    def test_depth_dependence(self):
        t=np.linspace(0,1,101);d=np.array([3,6,10,15,20,8])[:,None];y=d*np.exp(-t/(.1*np.exp(.8*d/20)));r=recovery_models(t,y,np.array([1,1,1,1,0,0],bool));self.assertLess(r[3]['heldout_rmse_db'],1e-7);self.assertGreater(r[0]['heldout_rmse_db'],.1)
    def test_db_exponential(self):
        t=np.linspace(0,1,101);d=np.array([3,6,10,15])[:,None];y=d*np.exp(-t/.15);r=recovery_models(t,y,np.array([1,1,0,0],bool));self.assertLess(r[0]['heldout_rmse_db'],1e-8)
    def test_invalid_depth(self):
        with self.assertRaises(ValueError):recovery_models(np.arange(10),np.zeros((4,10)),np.array([1,1,0,0],bool))
    def test_detector(self):
        p=np.tile([.1,.3,.8],8);r=p*np.repeat([.4,.8,.5,.9],6);f=np.repeat([80,200,1000,8000],6);z=np.log2(f/1000);y=-20*np.log10(p)*.6+z*.8+np.log10(p)*z;mask=np.arange(len(p))<18;models=detector_frequency_models(p,r,f,y,mask);self.assertLess(models[2]['heldout_rmse_db'],1e-10);self.assertGreater(models[0]['heldout_rmse_db'],1)
    def test_three_way(self):
        x=np.array(list(itertools.product((-1,0,1),repeat=3)));z=np.array(list(itertools.product((-.5,.5),repeat=3)));f=lambda q: q[:,0]+q[:,1]*q[:,2]+3*np.prod(q,axis=1);r=surfaces3(x,f(x),z,f(z));self.assertLess(r[-1]['heldout_rmse_db'],1e-10);self.assertGreater(r[2]['heldout_rmse_db'],.1)
    def test_overlap(self):
        x=np.array(list(itertools.product((-1,0,1),repeat=3)));y=x[:,0]
        with self.assertRaises(ValueError):surfaces3(x,y,x[:8],y[:8])
if __name__=='__main__':unittest.main()
