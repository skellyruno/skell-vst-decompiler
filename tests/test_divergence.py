import unittest
import tempfile
from pathlib import Path
import soundfile as sf
from skell_vst_decompiler.reference_lab import generate, digest
from skell_vst_decompiler.listening_bridge import compare
import numpy as np
from skell_vst_decompiler.divergence import first_difference


class DivergenceTests(unittest.TestCase):
    def test_first_frame_and_channel_across_blocks(self):
        a=np.zeros((1024,2));b=a.copy();b[513,1]=.01;b[514,:]=.02
        r=first_difference(a,b,48000)
        self.assertEqual(r['first_difference']['sample_index'],513)
        self.assertEqual(r['first_difference']['channel_index'],1)
        self.assertEqual(r['first_difference']['block_index'],2)
        self.assertEqual(r['mismatched_frames'],2)
        self.assertEqual(r['mismatched_samples'],3)
        self.assertIsNone(r['relative_residual_db'])

    def test_identical_and_silence(self):
        a=np.ones((10,1))*.25
        r=first_difference(a,a,44100,atol=0,rtol=0)
        self.assertIsNone(r['first_difference']);self.assertEqual(r['rms_error'],0)
        self.assertIsNone(first_difference(a*0,a*0,44100)['relative_residual_db'])

    def test_relative_and_absolute_tolerance(self):
        a=np.array([[0.,.5],[.1,.5]]);b=a+np.array([[1e-7,1e-6],[1e-4,0]])
        r=first_difference(a,b,48000)
        self.assertEqual(r['first_difference']['sample_index'],1)
        self.assertEqual(r['mismatched_samples'],1)

    def test_wav_bridge(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'probes';m=generate(root);c=m['cases'][0]
            a,_=sf.read(root/c['file'],always_2d=True);b=a.copy();b[513,1]=.01
            files=[Path(d)/'r.wav',Path(d)/'c.wav'];meta=[]
            for path,x in zip(files,(a,b)):
                sf.write(path,x,48000,subtype='FLOAT')
                meta.append(dict(plugin='owned',version='1',settings='test',target_stage='output',offset_samples=0,source_sha256=c['sha256'],render_sha256=digest(path)))
            self.assertNotIn('divergence',compare(root,c['id'],*files,*meta))
            r=compare(root,c['id'],*files,*meta,diagnose_first=True)
            self.assertEqual(r['divergence']['first_difference']['sample_index'],513)
            self.assertEqual(r['divergence']['first_difference']['channel_index'],1)
            meta[1]['target_stage']='different'
            with self.assertRaises(ValueError):compare(root,c['id'],*files,*meta,diagnose_first=True)

    def test_invalid_inputs(self):
        a=np.zeros((4,2));b=a.copy();b[3,0]=np.nan
        for args in ((a,b,48000),(a,a[:,0],48000),(a,a,1)):
            with self.assertRaises(ValueError):first_difference(*args)
        with self.assertRaises(ValueError):first_difference(a,a,48000,block=0)
        with self.assertRaises(ValueError):first_difference(a,a,48000,atol=-1)


if __name__=='__main__':unittest.main()
