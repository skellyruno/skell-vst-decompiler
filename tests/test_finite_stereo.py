import unittest
import numpy as np
from scipy.signal import fftconvolve
from skell_vst_decompiler.finite_stereo import codes,measure,probes


def render(x,h):
    y=np.zeros_like(x)
    for c in range(len(x)):
        for o in range(2):
            for i in range(2):y[c,:,o]+=fftconvolve(x[c,:,i],h[:,o,i])[:x.shape[1]]
    return y


class Tests(unittest.TestCase):
    def setUp(self):
        self.fs=44100;self.x,self.z,self.tail=probes(self.fs,1,1024)
        self.h=np.zeros((2000,2,2));self.h[0,0,0]=.4;self.h[17,1,0]=.1;self.h[29,0,1]=-.2;self.h[1900,1,1]=.6
    def evaluate(self,h):
        y=render(self.x,h);return measure(self.x,y,y[0],self.z,render(self.z,h),self.fs,self.tail)
    def test_orthogonality(self):
        a=np.fft.rfft(codes(1024,.04),4096,axis=1);g=np.einsum('cfi,cfj->fij',a.conj(),a);np.testing.assert_allclose(g,np.broadcast_to(np.eye(2)*2*1024*.04**2,g.shape),atol=1e-12)
    def test_four_routes(self):
        r=self.evaluate(self.h);self.assertEqual(r['status'],'CONSISTENT_FINITE_OBSERVATION');self.assertLess(r['holdout_relative'],1e-12);self.assertEqual([q['peak_sample'] for q in r['routes']],[0,29,17,1900])
    def test_late_tail(self):
        h=np.zeros((self.tail+2000,2,2));h[0,0,0]=.2;h[-1,0,0]=.6;self.assertEqual(self.evaluate(h)['status'],'TAIL_NOT_CONTAINED')
    def test_nonlinearity(self):
        f=lambda a: np.tanh(40*a);y=f(self.x);r=measure(self.x,y,y[0],self.z,f(self.z),self.fs,self.tail);self.assertEqual(r['status'],'HOLDOUT_OR_FIT_FAILED')
    def test_repeat(self):
        y=render(self.x,self.h);self.assertEqual(measure(self.x,y,y[0]*.8,self.z,render(self.z,self.h),self.fs,self.tail)['status'],'UNSTABLE_REPEAT')
    def test_invalid(self):
        y=render(self.x,self.h);self.x[0,0,0]*=-1
        with self.assertRaises(ValueError):measure(self.x,y,y[0],self.z,render(self.z,self.h),self.fs,self.tail)
    def test_long_delay(self):
        x,z,tail=probes(self.fs,3,1024);h=np.zeros((2*self.fs+123,2,2));h[-1,0,0]=.5;h[-1,1,1]=.5;y=render(x,h);r=measure(x,y,y[0],z,render(z,h),self.fs,tail);self.assertEqual(r['status'],'CONSISTENT_FINITE_OBSERVATION');self.assertEqual(r['routes'][0]['peak_sample'],len(h)-1)
    def test_host_files(self):
        import tempfile,json,hashlib
        from pathlib import Path
        import soundfile as sf
        from skell_vst_decompiler.finite_stereo import generate,compare_host
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'probes';m=generate(folder,44100,1,1024);captures={}
            for row in m['cases']:
                k=row['id'];p=root/k;p.mkdir();captures[k]=p;x,fs=sf.read(folder/row['file']);wet=p/'render.wav';sf.write(wet,x*.5,fs,subtype='FLOAT')
                meta=dict(binary_sha256='a'*64,host_module_sha256='b'*64,plugin='owned fixture',version='1',settings='fixed',parameter_readback={'gain':.5},target_stage='output',host='test',block_size=128,alignment_status='host_compensated_unverified',reported_latency_samples=0,backend='installed_vst3',reset=True,offset_samples=0,sample_rate=fs,frames=len(x),source_sha256=row['sha256'],render_sha256=hashlib.sha256(wet.read_bytes()).hexdigest());(p/'metadata.json').write_text(json.dumps(meta))
            self.assertEqual(compare_host(folder,captures)['status'],'CONSISTENT_FINITE_OBSERVATION')
            meta['settings']='changed';(p/'metadata.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):compare_host(folder,captures)
            meta['settings']='fixed';(p/'metadata.json').write_text(json.dumps(meta));wet.write_bytes(b'tampered')
            with self.assertRaises(ValueError):compare_host(folder,captures)
