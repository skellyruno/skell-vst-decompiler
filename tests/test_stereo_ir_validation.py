import unittest
import numpy as np
from skell_vst_decompiler.stereo_ir_validation import validate_stereo_ir


def fixture():
    rng = np.random.default_rng(199)
    h = np.zeros((2, 2, 128))
    for i in range(2):
        for o in range(2):
            h[i, o, 4 + i*3 + o] = .7 if i == o else -.2
            h[i, o, 37] = .03
    captures = []
    for i in range(2):
        for amp in (.2, -.8):
            x = np.zeros((136, 2)); x[8, i] = amp
            y = np.zeros_like(x); y[8:] = amp*h[i].T
            captures.append((x, y))
    probe = rng.normal(0, .1, (257, 2))
    wet = np.stack([sum(np.convolve(probe[:, i], h[i, o]) for i in range(2)) for o in range(2)], axis=1)
    return captures, probe, wet


class StereoIRTests(unittest.TestCase):
    def test_full_stereo_matrix_and_signed_levels(self):
        c, x, y = fixture(); r = validate_stereo_ir(c, x, y, 48000)
        self.assertTrue(r['passes_observed_gate'])
        self.assertLess(r['held_out_peak_error'], 1e-14)
        self.assertEqual([p['first_arrival'] for p in r['paths']], [4, 5, 7, 8])

    def test_level_dependence(self):
        c, x, y = fixture(); c[1][1][30, 0] = .1
        self.assertFalse(validate_stereo_ir(c, x, y, 48000)['passes_observed_gate'])

    def test_wrong_routing_and_timing(self):
        c, x, y = fixture()
        for bad in (y[:, ::-1], np.roll(y, 1, axis=0), y*.9):
            self.assertFalse(validate_stereo_ir(c, x, bad, 48000)['passes_observed_gate'])

    def test_pre_input_and_truncated_capture(self):
        c, x, y = fixture(); c[0][1][1, 0] = .1
        self.assertFalse(validate_stereo_ir(c, x, y, 48000)['passes_observed_gate'])
        c, x, y = fixture(); c[0][1][-1, 0] = .1; c[1][1][-1, 0] = -.4
        self.assertFalse(validate_stereo_ir(c, x, y, 48000)['capture_tail_quiet'])

    def test_reject_bad_pair(self):
        c, x, y = fixture()
        with self.assertRaises(ValueError): validate_stereo_ir(c, x, y[:-1], 48000)
        with self.assertRaises(ValueError): validate_stereo_ir(c[:3], x, y, 48000)
        x[0, 0] = np.nan
        with self.assertRaises(ValueError): validate_stereo_ir(c, x, y, 48000)

    def test_six_rates(self):
        for fs in (44100, 48000, 88200, 96000, 176400, 192000):
            c, x, y = fixture()
            self.assertTrue(validate_stereo_ir(c, x, y, fs)['passes_observed_gate'])

    def test_silent_output_not_evidence(self):
        c, x, y = fixture()
        for _, wet in c: wet.fill(0)
        y.fill(0)
        self.assertFalse(validate_stereo_ir(c, x, y, 48000)['passes_observed_gate'])

    def test_unexcited_channel(self):
        c, x, y = fixture(); x[:, 1] = 0
        self.assertFalse(validate_stereo_ir(c, x, y, 48000)['both_inputs_excited'])

if __name__ == '__main__': unittest.main()
