import unittest
from unittest.mock import Mock
from skell_vst_decompiler.eq_detector_source import verify, CHECKS, REGIONS

class EqDetectorEvidenceTests(unittest.TestCase):
    def test_wrong_source(self):
        with self.assertRaisesRegex(ValueError,'fingerprint'):
            verify(Mock(sha256='wrong'))

    def test_checkpoints_covered(self):
        self.assertEqual(len(CHECKS),28)
        self.assertEqual(len({a for a,_,_ in CHECKS}),28)
        self.assertTrue(all(any(lo<=a<hi for lo,hi in REGIONS) for a,_,_ in CHECKS))
