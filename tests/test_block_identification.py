import unittest
import numpy as np
from skell_vst_decompiler.block_identification import predict,fit_candidates,fit_orders

class Tests(unittest.TestCase):
    def test_order(self):
        x=np.random.default_rng(72).uniform(-.5,.5,4096);p=np.log([4.,1.,2000.]);self.assertGreater(np.linalg.norm(predict(x,48000,'pre',p)-predict(x,48000,'post',p)),.1)
    def test_selection(self):
        a,b=np.random.default_rng(14).uniform(-.8,.8,(2,4096));p=np.log([4.,.8,3200.]);res=fit_candidates([(a,predict(a,48000,'post',p),48000)],[(b,predict(b,48000,'post',p),48000)],models=('static','pre','post'));self.assertEqual(res['selected'],'post')
    def test_reject(self):
        a,b=np.random.default_rng(14).uniform(-.8,.8,(2,4096));res=fit_candidates([(a,np.roll(a,8),48000)],[(b,np.roll(b,8),48000)],models=('static',));self.assertIsNone(res['selected'])
    def test_duplicate(self):
        x=np.ones(4096)*.1
        with self.assertRaises(ValueError):fit_candidates([(x,x,48000)],[(x,x,48000)])
    def test_invalid(self):
        with self.assertRaises(ValueError):predict([np.nan],48000,'static',np.zeros(2))

    def test_order_selection(self):
        a,b=np.random.default_rng(19).uniform(-.8,.8,(2,4096));p=np.log([4.,.8,3200.]);r=fit_orders([(a,predict(a,48000,'post',p,2),48000)],[(b,predict(b,48000,'post',p,2),48000)]);self.assertEqual(r['selected']['order'],2);self.assertEqual(r['selected']['model'],'post')
