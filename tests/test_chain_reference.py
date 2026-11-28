import importlib.util
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf

spec=importlib.util.spec_from_file_location('chain_reference',Path(__file__).resolve().parents[1]/'benchmarks'/'chain_reference.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_known_saturation(self):
        fs=8000;x=np.random.default_rng(4).uniform(-.7,.7,(15*fs,2));y=.8*np.tanh(x*1.5)
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a.wav',Path(d)/'b.wav';sf.write(a,x,fs,subtype='FLOAT');sf.write(b,y,fs,subtype='FLOAT')
            r=mod.compare(a,b);self.assertEqual(r['observed_lag_samples'],0);self.assertLess(r['sections'][-1]['smooth_saturation']['relative_rms'],1e-6);self.assertGreater(r['sections'][-1]['scalar_gain']['relative_rms'],.01)
            sf.write(b,np.roll(y,3,axis=0),fs,subtype='FLOAT')
            with self.assertRaises(ValueError):mod.compare(a,b)
if __name__=='__main__':unittest.main()
