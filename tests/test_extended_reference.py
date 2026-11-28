import unittest
import tempfile
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from skell_vst_decompiler.extended_probes import probes,generate,digest
from skell_vst_decompiler.control_replay import compare,compare_files


class ExtendedTests(unittest.TestCase):
    def test_all_rates(self):
        for fs in (44100,48000,96000):
            rows=list(probes(fs,2)); self.assertEqual(len(rows),21)
            self.assertEqual(len({r[0] for r in rows}),21)
            for _,_,x,_ in rows:self.assertTrue(np.isfinite(x).all() and np.max(abs(x))<=1)
            for i,(_,_,x,_) in enumerate(rows[:4]):
                self.assertEqual(np.count_nonzero(x),1);self.assertEqual(x[fs//4,i//2],(.125,-.5)[i%2])
            self.assertTrue(np.all(rows[4][2][fs:]==0))
    def test_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'probes'; m=generate(root,44100,2)
            for row in m['cases']:
                f=root/row['file']; info=sf.info(f)
                self.assertEqual(digest(f),row['sha256']);self.assertEqual(info.frames,row['frames']);self.assertEqual(info.channels,2)
            with self.assertRaises(FileExistsError):generate(root,44100,2)
    def fixture(self):
        a=np.random.default_rng(10).normal(0,.1,(4096,2))
        m={'binary_sha256':'a'*64,'host_module_sha256':'b'*64,'source_sha256':'c'*64,'plugin':'owned example','version':'1','target_stage':'gain','sample_rate':48000,'frames':len(a),'block_size':128,'host':'fixture','offset_samples':0,'alignment_status':'explicit','backend':'installed_vst3','reported_latency_samples':0,'reset':True}
        return [(dict(m,parameter_readback={'gain':g,'other':.5}),x.copy()) for g,x in [(0.,a),(0.,a),(.5,a*.5),(.5,a*.5)]]
    def test_stable(self):
        self.assertEqual(compare(self.fixture(),'gain')['status'],'STABLE_EFFECT')
    def test_unchanged_audio(self):
        r=self.fixture(); r[2][1][:]=r[0][1];r[3][1][:]=r[0][1]
        self.assertEqual(compare(r,'gain')['status'],'NO_RESOLVED_EFFECT')
    def test_unstable(self):
        r=self.fixture();r[1][1][:]+=.01
        self.assertEqual(compare(r,'gain')['status'],'UNSTABLE')
    def test_confounded(self):
        r=self.fixture();r[2][0]['parameter_readback']['other']=.7;r[3][0]['parameter_readback']['other']=.7
        self.assertEqual(compare(r,'gain')['status'],'CONFOUNDED')
    def test_wrong_identity_and_nonfinite(self):
        r=self.fixture();r[3][0]['source_sha256']='d'*64
        with self.assertRaises(ValueError):compare(r,'gain')
        r=self.fixture();r[3][1][0,0]=np.nan
        with self.assertRaises(ValueError):compare(r,'gain')
    def test_same_control(self):
        r=self.fixture();r[2][0]['parameter_readback']['gain']=0;r[3][0]['parameter_readback']['gain']=0
        with self.assertRaises(ValueError):compare(r,'gain')

    def test_file_replay_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'source.wav'; rows=self.fixture(); folders=[]
            sf.write(source,rows[0][1],48000,subtype='FLOAT')
            for i,(meta,x) in enumerate(rows):
                folder=root/str(i);folder.mkdir();folders.append(folder)
                wet=folder/'render.wav';sf.write(wet,x,48000,subtype='FLOAT')
                meta.update(source_sha256=digest(source),render_sha256=digest(wet))
                (folder/'metadata.json').write_text(json.dumps(meta))
            self.assertEqual(compare_files(source,folders,'gain')['status'],'STABLE_EFFECT')
            sf.write(folders[3]/'render.wav',rows[0][1],48000,subtype='FLOAT')
            with self.assertRaises(ValueError):compare_files(source,folders,'gain')
            with self.assertRaises(ValueError):compare_files(source,[folders[0]]*4,'gain')
