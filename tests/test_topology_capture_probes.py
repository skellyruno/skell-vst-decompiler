import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf

spec=importlib.util.spec_from_file_location('topology_capture_probes',Path(__file__).resolve().parents[1]/'benchmarks'/'topology_capture_probes.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_probe_relations(self):
        for fs in (44100,48000,96000):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d)/'probes';m=mod.generate(root,fs);self.assertEqual(m,json.loads((root/'manifest.json').read_text()));a={}
                for row in m['cases']:
                    path=root/row['file'];x,sr=sf.read(path,always_2d=True,dtype='float32');self.assertEqual(sr,fs);self.assertEqual(x.shape,(row['frames'],2));self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),row['sha256']);self.assertLessEqual(float(np.max(abs(x))),1.);a[row['id']]=x
                self.assertEqual(len(a),11)
                for left,right in [('base','repeat'),('quiet_left','quiet_right'),('loud_right','loud_left')]:
                    np.testing.assert_array_equal(a[left],a[right] if left=='base' else a[right][:,::-1])
                np.testing.assert_array_equal(a['half'],.5*a['base']);np.testing.assert_array_equal(a['sum'],a['base']+a['other'])
                np.testing.assert_array_equal(a['alternate_prefix'][fs//2:],a['base'][fs//2:]);np.testing.assert_array_equal(a['shifted'][fs//20:],a['base'][:-fs//20]);self.assertTrue(np.all(a['shifted'][:fs//20]==0))
                np.testing.assert_array_equal(a['quiet_left'][:,0],a['loud_right'][:,0]);np.testing.assert_array_equal(a['quiet_right'][:,1],a['loud_left'][:,1])
                with self.assertRaises(FileExistsError):mod.generate(root,fs)
