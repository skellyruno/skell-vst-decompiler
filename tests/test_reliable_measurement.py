import tempfile,time,unittest
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from skell_vst_decompiler.reliable_measurement import harmonic_levels,repeated_spectrum,static_descriptions,SingleFlightCache

class Tests(unittest.TestCase):
    def test_cubic(self):
        fs=48000;x=.3*np.sin(2*np.pi*1000*np.arange(fs)/fs);y=x+2*x**3;r=harmonic_levels(x,y,fs,1000)
        self.assertAlmostEqual(r['harmonic_peak'][0],.3+1.5*.3**3,12);self.assertAlmostEqual(r['harmonic_peak'][2],.5*.3**3,12);self.assertLess(r['other_ac_rms'],1e-12)
    def test_impure(self):
        fs=48000;x=.3*np.sin(2*np.pi*1000*np.arange(fs)/fs)
        with self.assertRaises(ValueError):harmonic_levels(x+x*x,x,fs,1000)
    def test_repeats(self):
        x=np.random.default_rng(2).normal(0,.1,48000);self.assertEqual(repeated_spectrum(x,[x*.5,x*.5],48000)['status'],'CONSISTENT');self.assertEqual(repeated_spectrum(x,[x*.5,x*.7],48000)['status'],'UNRELIABLE')
    def test_models(self):
        x=np.linspace(-1,1,10001);r=np.random.default_rng(3);v,z=r.uniform(-.9,.9,(2,2000));f=lambda a:a+.4*a**3
        q=static_descriptions(x,f(x),v,f(v),z,f(z));self.assertLess(q['final_test_rms'],1e-10);self.assertGreater(q['linear_final_test_rms'],.01)
    def test_cache(self):
        with tempfile.TemporaryDirectory() as d:
            cache=SingleFlightCache(d);identity=dict(source_sha256='a'*64,implementation_sha256='b'*64,settings={},versions={});calls=[]
            def work():calls.append(1);time.sleep(.03);return {'result':1}
            with ThreadPoolExecutor(4) as pool:r=list(pool.map(lambda _:cache.get(identity,work),range(12)))
            self.assertEqual(len(calls),1);self.assertEqual(sum(hit for _,hit in r),11);self.assertEqual(cache._locks,{})
    def test_failed_cache_retries(self):
        with tempfile.TemporaryDirectory() as d:
            c=SingleFlightCache(d);k=dict(source_sha256='a'*64,implementation_sha256='b'*64,settings={},versions={})
            with self.assertRaises(ZeroDivisionError):c.get(k,lambda:1/0)
            self.assertEqual(c.get(k,lambda:2),(2,False));self.assertEqual(c._locks,{})
