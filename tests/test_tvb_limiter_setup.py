import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from skell_vst_decompiler.tvb_limiter_setup import verify
from skell_vst_decompiler.equations import TVB_SHA256


class LimiterSetupTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1]/'reports/limiter_setup/tvb_limiter_setup.json'
        self.report = json.loads(path.read_text())

    def test_manifest_counts(self):
        r = self.report
        self.assertEqual(r['binary_sha256'], TVB_SHA256)
        self.assertEqual(sum(len(x['checkpoints']) for x in r['regions']), 67)
        self.assertEqual(sum(len(x['imports']) for x in r['regions']), 4)
        self.assertEqual(len(r['constants']), 20)

    def test_reject_wrong_source_before_disassembly(self):
        pe = Mock(sha256='wrong')
        with patch('skell_vst_decompiler.tvb_limiter_setup.disassemble') as d:
            with self.assertRaises(ValueError):
                verify(pe, self.report)
            d.assert_not_called()
            pe.at_rva.assert_not_called()

    def test_reject_region_hash_mismatch(self):
        pe = Mock(sha256=TVB_SHA256)
        pe.at_rva.return_value = b'wrong'
        with patch('skell_vst_decompiler.tvb_limiter_setup.disassemble') as d:
            with self.assertRaisesRegex(ValueError, 'Code region hash mismatch'):
                verify(pe, self.report)
            d.assert_not_called()

    def test_reject_unbounded_range(self):
        pe = Mock(sha256=TVB_SHA256)
        report = copy.deepcopy(self.report)
        report['regions'][0]['end_rva_exclusive'] = '0xffffffff'
        with self.assertRaisesRegex(ValueError, 'Invalid evidence range'):
            verify(pe, report)
        pe.at_rva.assert_not_called()
