import unittest
import numpy as np
from experiments.parallel_identification import predict,select,delayed,fit_echo

class Tests(unittest.TestCase):
    def test_parallel(self):
        a,b=np.random.default_rng(1).uniform(-.8,.8,(2,2048));p=[2500.,4.,.4,.5]
        r=select([(a,predict(a,48000,'parallel',p),48000)],[(b,predict(b,48000,'parallel',p),48000)])
        self.assertEqual(r['selected']['kind'],'parallel')
    def test_split(self):
        a,b=np.random.default_rng(2).uniform(-.8,.8,(2,2048));p=[2500.,4.,.4,1.4,.5]
        r=select([(a,predict(a,48000,'split',p),48000)],[(b,predict(b,48000,'split',p),48000)])
        self.assertEqual(r['selected']['kind'],'split')
    def test_echo(self):
        a,b=np.random.default_rng(4).uniform(-.8,.8,(2,2048));imp=np.zeros(2048);imp[0]=.8
        for k in ('linear','inside','outside'):
            f=lambda x:delayed(x,71,.72,3.,k)
            self.assertEqual(fit_echo(f(imp),[(a,f(a))],[(b,f(b))])['selected']['kind'],k)
    def test_reject(self):
        a,b=np.random.default_rng(3).uniform(-.8,.8,(2,2048))
        self.assertIsNone(select([(a,np.roll(a,100),48000)],[(b,np.roll(b,100),48000)])['selected'])
    def test_invalid(self):
        with self.assertRaises(ValueError):delayed([1.],0,.4,1.,'inside')
        with self.assertRaises(ValueError):predict([1.],48000,'wet',[0.,1.,1.])
