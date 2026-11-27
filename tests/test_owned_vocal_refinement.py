"""Owned fixture controls; no recordings needed by CI."""
import shutil
import tempfile
import unittest
try:
    import numpy as np
    from benchmarks.owned_vocal_refinement import renderer, presence_checks, color_checks, require_equal
except ModuleNotFoundError:
    np=None


@unittest.skipUnless(np is not None and shutil.which('g++'),'requires NumPy, SciPy, SoundFile and native C++')
class VocalRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.work.cleanup)
        cls.render=staticmethod(renderer(cls.work.name)[0])

    def test_presence_endpoints_and_wet_trim(self):
        for fs in (44100,48000,96000):
            t=np.arange(4096)/fs
            x=np.ascontiguousarray(np.column_stack((.7*np.sin(2*np.pi*3200*t),.3*np.cos(2*np.pi*700*t))))
            report=presence_checks(self.render,x,fs)
            self.assertEqual(report['full_wet_scale_error'],0)
            for row in report['mix_cases']:
                self.assertEqual(row['zero_trim_parity_max_error'],0)
                self.assertLessEqual(row['wet_only_blend_max_error'],1e-12)
            self.assertEqual(report['mix_cases'][0]['trimmed_raw_gain_db'],0)

    def test_contiguous_parity_and_dry_delay(self):
        rng=np.random.default_rng(20261126)
        x=np.ascontiguousarray(rng.uniform(-.8,.8,(4096,2)))
        for fs in (44100,48000,96000):
            for row in color_checks(self.render,x,fs):
                self.assertTrue(all(v['exact'] for v in row['cases']))

    def test_invalid_controls_and_mismatch(self):
        x=np.ones((128,2));out=np.empty_like(x)
        for kind,fs,wet,trim in ((7,44100,1,0),(1,float('nan'),1,0),(1,44100,-1,0),(1,44100,1,19),(0,44100,1,-4)):
            with self.assertRaises(RuntimeError):self.render(kind,fs,wet,trim,x,out)
        with self.assertRaises(RuntimeError):require_equal(x,2*x)
