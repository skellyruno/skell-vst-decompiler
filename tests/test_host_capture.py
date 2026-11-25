import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import soundfile as sf
from skell_vst_decompiler.host_capture import bundle_hash, validate, capture, run_matrix
from skell_vst_decompiler.reference_lab import digest, measure
from skell_vst_decompiler.divergence import first_difference


def probe(root):
    root.mkdir();x=np.zeros((4800,2),np.float32);x[0,0]=.5;x[1200:2000,1]=.25
    p=root/'test.wav';sf.write(p,x,48000,subtype='FLOAT')
    (root/'manifest.json').write_text(json.dumps({'schema':1,'sample_rate':48000,'cases':[{'id':'test','file':'test.wav','family':'linear','sha256':digest(p),'frames':len(x),'windows':[]}]}));return x


def spec(block=256):return {'backend':'fixture','name':'Gain','parameters':{'gain_db':-6},'block_size':block,'target_stage':'output'}


class HostTests(unittest.TestCase):
    def test_validate_and_external_gate(self):
        self.assertEqual(validate(spec())['name'],'Gain')
        for s in (dict(spec(),block_size=0),dict(spec(),parameters={'gain_db':float('nan')}),dict(spec(),name='load_plugin'),dict(spec(),backend='installed_vst3')):
            with self.assertRaises(ValueError):validate(s)

    def test_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'Owned.vst3';p.mkdir();(p/'a').write_bytes(b'a');a=bundle_hash(p)
            (p/'b').write_bytes(b'b');self.assertNotEqual(a,bundle_hash(p))
            (p/'b').unlink();self.assertEqual(a,bundle_hash(p))
            (p/'a').unlink();p.rmdir();p.write_bytes(b'test');self.assertEqual(bundle_hash(p),digest(p))

    def test_native_capture_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);x=probe(p/'probes');meta=capture(p/'probes','test',spec(),p/'out')
            y,_=sf.read(p/'out'/'render.wav',always_2d=True)
            np.testing.assert_allclose(y,x*10**(-6/20),atol=1e-7)
            self.assertEqual(meta['evidence'],'EXEC: fixture');self.assertEqual(meta['render_sha256'],digest(p/'out'/'render.wav'))
            self.assertAlmostEqual(measure(p/'probes','test',p/'out'/'render.wav',meta)['gain_curve'][0]['gain_db'],-6,places=5)
            with self.assertRaises(FileExistsError):capture(p/'probes','test',spec(),p/'out')
            (p/'probes'/'test.wav').write_bytes(b'changed')
            with self.assertRaises(ValueError):capture(p/'probes','test',spec(),p/'other')

    def test_matrix_fresh_process_and_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);probe(p/'probes');plan=[{'id':'a','case':'test','spec':spec(64)},{'id':'bad','case':'missing','spec':spec()},{'id':'b','case':'test','spec':spec(1024)}]
            r=run_matrix(p/'probes',plan,p/'out')
            self.assertEqual([i['status'] for i in r],['captured','failed','captured'])
            a,_=sf.read(p/'out/a/render.wav',always_2d=True);b,_=sf.read(p/'out/b/render.wav',always_2d=True)
            self.assertIsNone(first_difference(a,b,48000,atol=0,rtol=0)['first_difference'])
            with self.assertRaises(FileExistsError):run_matrix(p/'probes',plan,p/'out')
            with self.assertRaises(ValueError):run_matrix(p/'probes',plan+plan,p/'other')


if __name__=='__main__':unittest.main()
