import unittest
from skell_vst_decompiler.partitioned_ir import selftest


class PartitionedIRTests(unittest.TestCase):
    def test_six_rates_and_transition(self):
        r = selftest()
        self.assertEqual(r['convolution_cases'], 24)
        self.assertEqual(r['two_tier_cases'], 6)
        self.assertEqual(r['transition_cases'], 12)
        self.assertLess(r['max_error'], 1e-11)


if __name__ == '__main__': unittest.main()
