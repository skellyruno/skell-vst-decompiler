import unittest
import numpy as np
from skell_vst_decompiler.interaction_analysis import factorial, history


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.x=np.random.default_rng(83).normal(0,.1,(800,2))

    def cells(self, interaction=0):
        return {k:(x.copy(),x.copy()) for k,x in {'00':self.x,'10':2*self.x,'01':3*self.x,'11':(4+interaction)*self.x}.items()}

    def test_additive(self):
        r=factorial(self.cells()); self.assertEqual(r['status'],'NO_RESOLVED_INTERACTION');self.assertLess(r['additive_relative_error'],1e-14)

    def test_interacting(self):
        r=factorial(self.cells(2));self.assertEqual(r['status'],'INTERACTION');self.assertAlmostEqual(r['additive_relative_error'],1/3)

    def test_noise_and_missing(self):
        c=self.cells(2);c['00'][1][:]+=.01;self.assertEqual(factorial(c)['status'],'UNSTABLE')
        del c['01']
        with self.assertRaises(ValueError):factorial(c)

    def test_alignment_and_nonfinite(self):
        c=self.cells();c['01']=(self.x[:-1],self.x[:-1]);
        with self.assertRaises(ValueError):factorial(c)
        c=self.cells();c['11'][0][0,0]=np.nan
        with self.assertRaises(ValueError):factorial(c)

    def test_silence_no_ratio(self):
        z=np.zeros_like(self.x);r=factorial({k:(z,z) for k in ('00','10','01','11')});self.assertIsNone(r['additive_relative_error']);self.assertEqual(r['status'],'NO_RESOLVED_INTERACTION')

    def history_case(self, end=480):
        a=self.x.copy();b=a.copy();b[:160]*=2
        wet_a=a.copy();wet_b=b.copy();wet_b[160:end]+=.02
        return a,b,{'a':(wet_a,wet_a.copy()),'b':(wet_b,wet_b.copy())}

    def test_history_finite(self):
        a,b,c=self.history_case();r=history(a,b,c,8000,160);self.assertEqual(r['status'],'HISTORY_DETECTED');self.assertEqual(r['last_detected_end_ms'],40);self.assertFalse(r['right_censored'])

    def test_history_censored_and_memoryless(self):
        a,b,c=self.history_case(800);self.assertTrue(history(a,b,c,8000,160)['right_censored'])
        a,b,c=self.history_case(160);self.assertEqual(history(a,b,c,8000,160)['status'],'NO_RESOLVED_HISTORY')

    def test_history_wrong_suffix_and_noise(self):
        a,b,c=self.history_case();b[-1,0]+=.01
        with self.assertRaises(ValueError):history(a,b,c,8000,160)
        a,b,c=self.history_case();c['a'][1][160:]+=.01
        self.assertEqual(history(a,b,c,8000,160)['status'],'UNSTABLE')

    def test_file_factorial(self):
        import tempfile, json
        from pathlib import Path
        import soundfile as sf
        from skell_vst_decompiler.extended_probes import digest
        from skell_vst_decompiler.interaction_analysis import factorial_files
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.wav';sf.write(source,self.x,48000,subtype='FLOAT');folders={}
            for cell,pair in self.cells(2).items():
                folders[cell]=[]
                for i,x in enumerate(pair):
                    f=root/(cell+str(i));f.mkdir();folders[cell].append(f);wet=f/'render.wav';sf.write(wet,x,48000,subtype='FLOAT')
                    m=dict(binary_sha256='a'*64,host_module_sha256='b'*64,plugin='owned fixture',version='1',target_stage='test',host='test',block_size=128,offset_samples=0,alignment_status='declared',backend='installed_vst3',reported_latency_samples=0,reset=True,source_sha256=digest(source),sample_rate=48000,frames=len(x),render_sha256=digest(wet),parameter_readback={'a':int(cell[0]),'b':int(cell[1]),'fixed':.5})
                    (f/'metadata.json').write_text(json.dumps(m))
            self.assertEqual(factorial_files(source,folders,('a','b'))['status'],'INTERACTION')
            path=folders['11'][1]/'metadata.json';m=json.loads(path.read_text());m['parameter_readback']['fixed']=.6;path.write_text(json.dumps(m))
            with self.assertRaises(ValueError):factorial_files(source,folders,('a','b'))
            m['parameter_readback']['fixed']=.5;path.write_text(json.dumps(m));sf.write(folders['11'][1]/'render.wav',self.x,48000,subtype='FLOAT')
            with self.assertRaises(ValueError):factorial_files(source,folders,('a','b'))
