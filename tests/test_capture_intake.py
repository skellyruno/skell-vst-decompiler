import json,tempfile,unittest
from pathlib import Path
import numpy as np
import soundfile as sf
from benchmarks.topology_capture_probes import generate
from skell_vst_decompiler.capture_intake import seal,analyze,sources

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.probes=self.root/'probes';generate(self.probes)
        self.wet=self.root/'wet';self.wet.mkdir();self.decl=self.root/'declaration.json';self.session=self.root/'session.json'
        self.d=dict(plugin='owned fixture',version='1',host='test',settings='fixed gain .5',target_stage='output',authorized=True,isolated=True,fresh_reset=True,no_normalization=True,same_settings=True,alignment='owner_verified_active_timeline',alignment_note='analytic aligned fixture',reported_latency_samples=0)
    def prepare(self,fn=lambda x:x*.5,bypass=lambda x:x):
        fs,x,_=sources(self.probes)
        for k,v in x.items():sf.write(self.wet/(k+'.wav'),fn(v),fs,subtype='FLOAT')
        sf.write(self.wet/'bypass.wav',bypass(x['base']),fs,subtype='FLOAT');self.decl.write_text(json.dumps(self.d));seal(self.probes,self.wet,self.decl,self.session)
    def test_linear(self):
        self.prepare();r=analyze(self.probes,self.wet,self.session);self.assertEqual(r['status'],'SCREENED_OWNER_DECLARED');self.assertEqual(r['candidates']['rejected'],[]);self.assertEqual(r['stereo'][0]['difference_rms'],0)
    def test_nonlinear(self):
        self.prepare(lambda x:np.tanh(3*x));r=analyze(self.probes,self.wet,self.session);self.assertIn('linear_time_invariant',r['candidates']['rejected'])
    def test_unverified(self):
        self.d['alignment']='unverified';self.prepare();self.assertEqual(analyze(self.probes,self.wet,self.session)['status'],'REVIEW_REQUIRED')
    def test_shifted_bypass(self):
        self.prepare(bypass=lambda x:np.roll(x,1,axis=0));self.assertEqual(analyze(self.probes,self.wet,self.session)['status'],'REVIEW_REQUIRED')
    def test_latency(self):
        self.d['reported_latency_samples']=64;self.prepare();self.assertEqual(analyze(self.probes,self.wet,self.session)['status'],'REVIEW_REQUIRED')
    def test_tamper(self):
        self.prepare();p=self.wet/'base.wav';x,fs=sf.read(p);sf.write(p,x*.9,fs,subtype='FLOAT')
        with self.assertRaises(ValueError):analyze(self.probes,self.wet,self.session)
    def test_unstable(self):
        self.prepare();p=self.wet/'repeat.wav';x,fs=sf.read(p);sf.write(p,x*.9,fs,subtype='FLOAT');self.session.unlink();seal(self.probes,self.wet,self.decl,self.session);self.assertEqual(analyze(self.probes,self.wet,self.session)['status'],'RECAPTURE')
    def test_wrong_length(self):
        self.prepare();self.session.unlink();p=self.wet/'repeat.wav';x,fs=sf.read(p);sf.write(p,x[:-1],fs,subtype='FLOAT')
        with self.assertRaises(ValueError):seal(self.probes,self.wet,self.decl,self.session)
    def test_missing_authorization(self):
        self.d['authorized']=False
        with self.assertRaises(ValueError):self.prepare()
    def test_scaled_probes(self):
        for scale in (2,4,8):
            root=self.root/str(scale);generate(root,48000,scale);_,a,_=sources(self.probes);_,b,_=sources(root)
            for key in a:np.testing.assert_array_equal(a[key]/scale,b[key])
