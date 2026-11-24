import copy
import json
from pathlib import Path
import unittest
from skell_vst_decompiler.verification import reconcile, revenant_metadata, load, digest, canonical

SHA = 'a'*64
OTHER = 'b'*64


def fixture():
    span = {'start_rva':'0x100','end_rva_exclusive':'0x110','bytes':16}
    snapshot = {'schema_version':1,'binaries':[{'binary':'owned.exe','binary_sha256':SHA,'wrappers':[{'wrapper_rva':'0x20','sampled_slots':[{'slot':i,'target_rva':'0x100','unwind_region':span} for i in range(6)],'slot45_atlas_overlap':['a.json::inside']}]}]}
    document = {'schema_version':1,'binary_sha256':SHA,'regions':[{'id':'inside','start_rva':'0x105','end_rva_exclusive':'0x108'},{'id':'adjacent','start_rva':'0x110','end_rva_exclusive':'0x120'}]}
    return snapshot, [('a.json',document,digest(canonical(document)))]


class VerificationTest(unittest.TestCase):
    def test_half_open_and_fingerprint(self):
        snapshot, inputs = fixture()
        other = dict(inputs[0][1],binary_sha256=OTHER)
        result = reconcile(snapshot,inputs+[('other.json',other,digest(canonical(other)))])
        self.assertEqual(result['checks'][0]['status'],'consistent')
        self.assertEqual(result['checks'][0]['overlap_count'],1)

    def test_drift_and_dependency_key(self):
        snapshot, inputs = fixture()
        old = reconcile(snapshot,inputs)
        document = copy.deepcopy(inputs[0][1])
        document['regions'][0]['id'] = 'changed'
        new = reconcile(snapshot,[('a.json',document,digest(canonical(document)))])
        self.assertNotEqual(old['input_key'],new['input_key'])
        self.assertEqual(new['checks'][0]['missing_references'],['a.json::inside'])
        self.assertEqual(new['checks'][0]['additional_references'],['a.json::changed'])
        self.assertEqual(new['checks'][0]['status'],'review_required')

    def test_bad_span(self):
        snapshot, inputs = fixture()
        snapshot['binaries'][0]['wrappers'][0]['sampled_slots'][4]['unwind_region']['bytes'] = 17
        with self.assertRaises(ValueError):
            reconcile(snapshot,inputs)

    def test_duplicate_input(self):
        snapshot, inputs = fixture()
        with self.assertRaises(ValueError):
            reconcile(snapshot,inputs+inputs)

    def test_external_metadata(self):
        report={'sha256':SHA,'function_count':12,'stages_completed':['triage','disasm'],'stages_failed':{'verify':'blocked'},'findings':[{'title':'untrusted'}]}
        result=revenant_metadata(report,SHA)
        self.assertEqual(result['status'],'external_unverified')
        self.assertEqual(result['failed_stage_count'],1)
        self.assertNotIn('findings',result)
        with self.assertRaises(ValueError):
            revenant_metadata(report,OTHER)
        with self.assertRaises(ValueError):
            revenant_metadata(dict(report,function_count=True),SHA)

    def test_input_order_stable(self):
        snapshot, inputs = fixture()
        other=('b.json',{},digest(canonical({})))
        self.assertEqual(reconcile(snapshot,inputs+[other]),reconcile(snapshot,[other]+inputs))

    def test_repository_snapshot(self):
        root = Path(__file__).resolve().parents[1] / 'reports'
        snapshot, _ = load(root/'vmr_variant_navigation.json')
        inputs = [(p.name,*load(p)) for p in root.glob('*.json') if p.name != 'vmr_variant_navigation.json']
        result = reconcile(snapshot,inputs)
        self.assertEqual(len(result['checks']),6)
        self.assertTrue(all(x['status']=='consistent' for x in result['checks']),result['checks'])
        self.assertEqual(sorted(x['overlap_count'] for x in result['checks']),[0,0,0,3,3,6])


if __name__ == '__main__':
    unittest.main()
