import unittest
import numpy as np
from skell_vst_decompiler.behavior_models import recovery_models,detector_probes,detector_levels
from skell_vst_decompiler.pitch_trajectory import trajectory_cases,score


class BehaviorTests(unittest.TestCase):
    def test_recovery_heldout(self):
        t=np.arange(0.,1000.,10.)
        grid=np.geomspace(5.,2000.,32)
        y=8*np.exp(-t/grid[10])+4*np.exp(-t/grid[23])
        r=recovery_models(t,y)
        self.assertLess(r['dual']['heldout_rmse'],1e-8)
        self.assertGreater(r['single']['heldout_rmse'],.05)
        self.assertEqual(r['heldout_count'],35)
        with self.assertRaises(ValueError):recovery_models(t,-y)

    def test_crest_and_stereo(self):
        p={k:detector_levels(v) for k,v in detector_probes().items()}
        self.assertAlmostEqual(p['sine_dual_mono']['linked_mean_power_rms'],.1)
        self.assertAlmostEqual(p['pulse_dual_mono']['linked_mean_power_rms'],.1)
        self.assertGreater(p['pulse_dual_mono']['linked_peak'],p['sine_dual_mono']['linked_peak'])
        self.assertAlmostEqual(p['sine_left_only']['linked_mean_power_rms'],.1/np.sqrt(2))
        self.assertAlmostEqual(p['sine_left_only']['max_channel_rms'],.1)

    def test_trajectory_accounting(self):
        fs=8000
        x,f,v=trajectory_cases(fs)['step']
        r=score(lambda frame,rate:(None,0.),x,f,v,fs)
        self.assertEqual(r['missed_voiced'],r['voiced_frames'])
        self.assertGreater(r['unvoiced_frames'],0)
        self.assertGreater(r['excluded_transition_frames'],0)
        self.assertEqual(r['false_positive_unvoiced'],0)

if __name__=='__main__':unittest.main()
