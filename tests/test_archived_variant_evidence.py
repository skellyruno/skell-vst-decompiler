"""Regression checks for the immutable historical paired-processor report."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'reports'


class ArchivedVariantEvidenceTest(unittest.TestCase):
    def test_original_report_bytes(self):
        raw = (ROOT / 'vmr_variant_navigation.json').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         'b408003f878e38c0726c761b58e316d96844ce304b638b6939ba7ee98c65857d')

    def test_historical_class_plan_and_dispatch_consistency(self):
        doc = json.loads((ROOT / 'vmr_variant_navigation.json').read_text(encoding='utf-8'))
        classes = json.loads((ROOT / 'class_navigation_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(doc['schema_version'], 1)
        class_by_hash = {x['binary_sha256']: x for x in classes['binaries']}
        self.assertEqual(len(doc['binaries']), 3)
        total = 0
        for item in doc['binaries']:
            plan = class_by_hash[item['binary_sha256']]['selected_plan']
            expected = {x['requested_rva']: x['unwind_region'] for x in plan['targets']}
            self.assertEqual(set(expected), {w['wrapper_rva'] for w in item['wrappers']})
            self.assertEqual(len(item['wrappers']), 2)
            for w in item['wrappers']:
                self.assertEqual(w['wrapper_bytes'], expected[w['wrapper_rva']]['bytes'])
                slots = w['sampled_slots']
                self.assertEqual([x['slot'] for x in slots], list(range(6)))
                self.assertEqual(slots[4]['target_rva'], slots[5]['target_rva'])
                self.assertEqual(slots[4]['unwind_region'], slots[5]['unwind_region'])
                total += len(slots)
        self.assertEqual(total, 36)


if __name__ == '__main__':
    unittest.main()
