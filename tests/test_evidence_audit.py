import json
from pathlib import Path
import unittest
from skell_vst_decompiler.evidence_audit import audit
from skell_vst_decompiler.research_index import records

SHA = 'a' * 64
OTHER = 'b' * 64


def row(name, start, end, calls=(), sha=SHA):
    return {'binary_sha256': sha, 'source': 'fixture', 'report': name + '.json',
            'region': {'id': name, 'start_rva': hex(start), 'end_rva_exclusive': hex(end),
                       'direct_calls': [{'site_rva': hex(s), 'target_rva': hex(t)} for s, t in calls]}}


def summary(address=0x100, sha=SHA):
    return {'schema_version': 1, 'binaries': [
        {'binary': 'fixture', 'binary_sha256': sha,
         'selected_plan': {'binary_sha256': sha, 'targets': [
             {'requested_rva': hex(address), 'unwind_region': {
                 'start_rva': '0x100', 'end_rva_exclusive': '0x120'}}]},
         'classes': [{'type': 'fixture', 'vtables': [
             {'vtable_rva': '0x800', 'subobject_offset': 0,
              'selected_method_rvas': {'5': hex(address)}}]}]}]}


class EvidenceAuditTest(unittest.TestCase):
    def test_dedup_and_fingerprint_isolation(self):
        rows = [row('a', 0x100, 0x110, [(0x101, 0x200)]),
                row('b', 0x100, 0x110, [(0x101, 0x200)]),
                row('foreign', 0x200, 0x210, sha=OTHER)]
        result = audit(rows, summary())['binaries'][0]
        self.assertEqual(result['distinct_call_sites'], 1)
        self.assertEqual(result['uncovered_targets'][0]['distinct_call_sites'], 1)
        self.assertEqual(result['selected_methods'][0]['status'], 'entry_covered')

    def test_unwind_overlap_is_not_entry(self):
        result = audit([row('inner', 0x110, 0x120)], summary())['binaries'][0]
        slot = result['selected_methods'][0]
        self.assertEqual(slot['status'], 'unwind_overlap_only')
        self.assertFalse(slot['entry_evidence'])

    def test_conflicting_calls_not_ranked(self):
        result = audit([row('a', 0x100, 0x110, [(0x101, 0x200)]),
                        row('b', 0x100, 0x110, [(0x101, 0x300)])], summary())['binaries'][0]
        self.assertEqual(len(result['conflicting_call_sites']), 1)
        self.assertFalse(result['uncovered_targets'])

    def test_reject_bad_fingerprint_and_outside_site(self):
        document = summary()
        document['binaries'][0]['selected_plan']['binary_sha256'] = OTHER
        with self.assertRaises(ValueError):
            audit([], document)
        with self.assertRaises(ValueError):
            audit([row('bad', 0x100, 0x110, [(0x111, 0x200)])], summary())

    def test_checked_in_reports(self):
        folder = Path(__file__).resolve().parents[1] / 'reports'
        document = json.loads((folder / 'class_navigation_summary.json').read_text())
        result = audit(records(folder.glob('*.json')), document)
        self.assertGreaterEqual(sum(x['region_count'] for x in result['binaries']), 128)
        self.assertEqual(sum(len(x['selected_methods']) for x in result['binaries']), 23)
        self.assertEqual(result, audit(records(folder.glob('*.json')), document))


if __name__ == '__main__':
    unittest.main()
