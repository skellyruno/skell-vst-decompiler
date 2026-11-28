import math
import unittest
import numpy as np
from skell_vst_decompiler.pitch_control import RetuneControl
from skell_vst_decompiler.topology_probes import stereo_cases,topology_levels,harmonic_levels


class PublicBehaviorTests(unittest.TestCase):
    def test_stereo_polarity_discrimination(self):
        rows={k:topology_levels(x) for k,x in stereo_cases().items()}
        self.assertAlmostEqual(rows['opposite']['pre_detection_mean_rms'],0.)
        self.assertAlmostEqual(rows['opposite']['channel_power_rms'],rows['in_phase']['channel_power_rms'])
        self.assertAlmostEqual(rows['quadrature']['pre_detection_mean_rms'],.1)

    def test_harmonics_known_source(self):
        fs=48000;t=np.arange(fs)/fs;phase=2*np.pi*1000*t
        r=harmonic_levels(np.sin(phase)+.1*np.sin(2*phase)+.01*np.cos(3*phase),fs,1000)
        self.assertAlmostEqual(r['relative_harmonics_db'][0],-20.)
        self.assertAlmostEqual(r['relative_harmonics_db'][1],-40.)
        self.assertAlmostEqual(r['selected_thd_ratio'],math.hypot(.1,.01))
        with self.assertRaises(ValueError):harmonic_levels(np.ones(100),fs,1000)

    def test_sustain_control_compatibility_and_reset(self):
        old=RetuneControl(retune_ms=0);new=RetuneControl(retune_ms=0,sustain_ms=150)
        for i in range(15):
            f=440*2**(.2/12)
            self.assertEqual(old.step(f,1.,10),new.step(f,1.,10))
        for i in range(40):new.step(f,1.,10)
        shifted=440*2**(.35/12)
        self.assertLess(abs(new.step(shifted,1.,10)[1]+20),15.)
        self.assertEqual(new.step(None,0.,10),(None,0.))
        self.assertEqual(new.step(shifted,1.,10),old.step(shifted,1.,10))

if __name__=='__main__':unittest.main()
