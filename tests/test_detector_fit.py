import unittest
import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from skell_vst_decompiler.system_id import history,envelope,generate
from skell_vst_decompiler.detector_fit import predict_detector,compare_detector
from skell_vst_decompiler.reference_lab import digest
from skell_vst_decompiler.listening_bridge import compare


class DetectorTests(unittest.TestCase):
    def test_known_detector(self):
        p=[-24,.75,1,8,120];pairs=[]
        for split in (False,True,'test'):
            a=history(48000,split);x,_=envelope(a,a,48000);x=np.round(x,2)
            pairs.append((x,predict_detector(x,p,'amplitude')))
        r=compare_detector(*pairs);self.assertEqual(r['selected_by_validation'],'amplitude')
        self.assertLess(r['models']['amplitude']['test_rmse_db'],1e-6)
        self.assertGreater(r['models']['single']['test_rmse_db'],.1)
        with self.assertRaises(ValueError):compare_detector(([0]*20,[0]*20),*pairs[1:])

    def test_aligned_bridge(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'probes';m=generate(root);c=m['cases'][0];a,_=sf.read(root/c['file'],always_2d=True)
            paths=[Path(d)/'r.wav',Path(d)/'c.wav'];metadata=[]
            for file,x in zip(paths,(a*.5,a*.25)):
                sf.write(file,x,48000,subtype='FLOAT');metadata.append(dict(plugin='owned',version='1',settings='test',offset_samples=0,target_stage='output',source_sha256=c['sha256'],render_sha256=digest(file)))
            r=compare(root,c['id'],*paths,*metadata);self.assertAlmostEqual(r['level_delta_db'],-6.0206,places=4);self.assertAlmostEqual(r['relative_residual_db'],-6.0206,places=4)
            self.assertEqual(r['sound_match']['status'],'not_requested');self.assertEqual(r['fif_ears']['status'],'not_requested')
            metadata[1]['target_stage']='wrong'
            with self.assertRaises(ValueError):compare(root,c['id'],*paths,*metadata)


if __name__=='__main__':unittest.main()
