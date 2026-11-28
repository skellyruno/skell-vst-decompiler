import json,tempfile,unittest
from pathlib import Path
import numpy as np
from skell_vst_decompiler.measurement_lab import *

class Tests(unittest.TestCase):
    def test_sweep(self):
        x,inv,L=sweep();a=harmonic_windows(x,x,inv,L,48000);b=harmonic_windows(x,x+2*x*x+3*x**3,inv,L,48000)
        self.assertLess(a[1]['relative_window_db'],-35);self.assertGreater(b[1]['relative_window_db'],a[1]['relative_window_db']+20);self.assertGreater(b[2]['relative_window_db'],a[2]['relative_window_db']+20)
    def test_coherence(self):
        r=np.random.default_rng(2);x=r.normal(0,.1,48000);a=coherence_gate(x,x*.5,48000);b=coherence_gate(x,r.normal(0,.1,len(x)),48000);self.assertGreater(a['pass_fraction'],.99);self.assertLess(b['pass_fraction'],.01)
    def test_models(self):
        r=np.random.default_rng(3);a,b=r.uniform(-.5,.5,(2,2000));f=lambda x: .5*x+2*x**3+.5*np.roll(x,1)**2
        q=model_screen(a,f(a),b,f(b));self.assertLess(q[-1]['holdout_rms'],1e-12);self.assertGreater(q[1]['holdout_rms'],.01)
        with self.assertRaises(ValueError):model_screen(a,f(a),a,f(a))
    def test_sampling(self):
        x=np.array([(a,b) for a in np.linspace(-1,1,9) for b in np.linspace(-1,1,9)]);z=np.array([[.1,.2],[-.2,.3]]);calls=[]
        def f(p):calls.append(p.copy());return p[0]+p[1]
        ids,y=sample_surface(x,f,z,budget=15);self.assertEqual(len(set(ids)),15);self.assertEqual(len(calls),15);np.testing.assert_allclose(y,z.sum(axis=1),atol=1e-9)
    def test_cache(self):
        with tempfile.TemporaryDirectory() as d:
            k=dict(source_sha256='a'*64,implementation_sha256='b'*64,settings={'a':1},versions={'numpy':'test'});self.assertEqual(cached(d,k,lambda:{'v':2}),({'v':2},False));self.assertEqual(cached(d,k,lambda:1/0),({'v':2},True));p=next(Path(d).glob('*.json'));r=json.loads(p.read_text());r['payload']['v']=3;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):cached(d,k,lambda:0)
    def test_parallel(self):
        self.assertEqual(parallel_measure(list(range(20)),lambda i:i*i,4),[i*i for i in range(20)])
