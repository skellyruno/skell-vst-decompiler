import unittest
import numpy as np
from scipy.signal import fftconvolve
from skell_vst_decompiler.broadband import stimulus,measure


def render(x,h):
    y=np.zeros_like(x)
    for o in range(2):
        for i in range(2):
            for c in range(2):y[c,:,o]+=fftconvolve(x[c,:,i],h[:,o,i])[:x.shape[1]]
    return y


class Tests(unittest.TestCase):
    def setUp(self):
        self.x=stimulus(1024,2);self.z=stimulus(1024,3,.2)
        self.h=np.random.default_rng(4).normal(0,.01,(128,2,2));self.h[0,0,0]+=.5;self.h[0,1,1]+=.4
    def test_linear(self):
        r=measure(self.x,render(self.x,self.h),self.z,render(self.z,self.h));self.assertEqual(r['status'],'CONSISTENT_OBSERVATION');self.assertLess(r['heldout_relative_rms'],1e-12);self.assertEqual(r['bins'],513)
    def test_nonlinear(self):
        f=lambda x:np.tanh(12*x);r=measure(self.x,f(self.x),self.z,f(self.z));self.assertEqual(r['status'],'HOLDOUT_FAILED')
    def test_unstable(self):
        y=render(self.x,self.h);y[:,-1024:]*=.5;r=measure(self.x,y,self.z,render(self.z,self.h));self.assertEqual(r['status'],'UNSTABLE_PERIODS')
    def test_silent(self):
        r=measure(self.x,np.zeros_like(self.x),self.z,np.zeros_like(self.z));self.assertEqual(r['status'],'UNRESOLVED_SILENCE')
    def test_same_phase(self):
        with self.assertRaises(ValueError):measure(self.x,self.x,self.x*.5,self.x*.5)
    def test_wrong_code(self):
        x=self.x.copy();x[1,7,1]*=-1
        with self.assertRaises(ValueError):measure(x,x,self.z,self.z)
    def test_unexcited(self):
        x=np.zeros_like(self.x)
        with self.assertRaises(ValueError):measure(x,x,self.z,self.z)
    def test_nonfinite(self):
        x=self.x.copy();x[0,0,0]=np.nan
        with self.assertRaises(ValueError):measure(x,x,self.z,self.z)
    def test_file_capture(self):
        import tempfile,json,hashlib
        from pathlib import Path
        import soundfile as sf
        from skell_vst_decompiler.broadband import generate,compare_files
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'probes';m=generate(folder,44100);captures={}
            for row in m['cases']:
                key=row['id'];out=root/key;out.mkdir();captures[key]=out
                x,fs=sf.read(folder/row['file'],always_2d=True);wet=out/'render.wav';sf.write(wet,x*.5,fs,subtype='FLOAT')
                meta=dict(binary_sha256='a'*64,host_module_sha256='b'*64,plugin='owned fixture',version='1',settings='fixed',parameter_readback={'gain':.5},target_stage='output',host='test',block_size=128,alignment_status='declared',reported_latency_samples=0,backend='installed_vst3',reset=True,offset_samples=0,sample_rate=fs,source_sha256=row['sha256'],frames=row['frames'],render_sha256=hashlib.sha256(wet.read_bytes()).hexdigest())
                (out/'metadata.json').write_text(json.dumps(meta))
            self.assertEqual(compare_files(folder,captures)['status'],'CONSISTENT_OBSERVATION')
            meta['settings']='changed';(out/'metadata.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):compare_files(folder,captures)
            meta['settings']='fixed';(out/'metadata.json').write_text(json.dumps(meta));wet.write_bytes(b'tampered')
            with self.assertRaises(ValueError):compare_files(folder,captures)
