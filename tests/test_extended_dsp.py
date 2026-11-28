import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from skell_vst_decompiler.extended_dsp import verify_extended,verify_vmr_utilities,constants
from skell_vst_decompiler.catalog import search
from skell_vst_decompiler.audio_probe import measure
import struct

class TestExtended(unittest.TestCase):
    def test_hash_guard(self):
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            verify_extended(SimpleNamespace(sha256='wrong'))
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            verify_vmr_utilities(SimpleNamespace(path=Path('FG-116.epl'),sha256='wrong'))
    def test_unsupported_module(self):
        with self.assertRaisesRegex(ValueError,'module name'):
            verify_vmr_utilities(SimpleNamespace(path=Path('unknown.epl')))
    def test_constants(self):
        fake=SimpleNamespace(at_rva=lambda r,n:struct.pack('<f',.125))
        self.assertEqual(constants(fake,[(10,.125)]),{'0xa':.125})
        with self.assertRaises(ValueError):constants(fake,[(10,.25)])
    def test_catalog(self):
        data=json.loads((Path(__file__).resolve().parents[1]/'reports/tvb_extended_dsp.json').read_text())
        self.assertEqual(sum(r['checkpoint_count'] for r in data['regions']),data['checkpoint_count'])
        self.assertEqual(len(search(data,'de-esser')['matches']),3)
        self.assertEqual(len(search(data,'0x34308c')['matches']),1)
    def test_wav_spectrum(self):
        import numpy as np
        from scipy.io import wavfile
        fs=48000;tone=17000;t=np.arange(2*fs)/fs
        x=.5*np.sin(2*np.pi*tone*t)+.01*np.sin(2*np.pi*14000*t)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'probe.wav';wavfile.write(p,fs,x.astype('float32'))
            r=measure(p,tone);c=r['channels'][0]
            self.assertAlmostEqual(c['fundamental_dbfs'],-6.0206,places=3)
            self.assertAlmostEqual(c['unambiguous_alias_candidate_power_dbc'],-33.9794,places=3)
            self.assertIsNone(c['unambiguous_harmonic_power_dbc'])
            with self.assertRaises(ValueError):measure(p,tone,2)
            with self.assertRaises(ValueError):measure(p,24000)
    def test_collision_and_pcm(self):
        import numpy as np
        from scipy.io import wavfile
        fs=48000;t=np.arange(fs)/fs
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'probe.wav';wavfile.write(p,fs,(16384*np.sin(2*np.pi*8000*t)).astype('int16'))
            c=measure(p,8000,0)['channels'][0]
            self.assertAlmostEqual(c['fundamental_dbfs'],-6.021,places=2)
            self.assertTrue(any(x['kind']=='ambiguous' for x in c['components']))
            self.assertIsNone(c['unambiguous_alias_candidate_power_dbc'])
    def test_invalid_samples(self):
        import numpy as np
        from scipy.io import wavfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.wav';wavfile.write(p,48000,np.array([float('nan')],dtype='float32'))
            with self.assertRaises(ValueError):measure(p,1000,0)
