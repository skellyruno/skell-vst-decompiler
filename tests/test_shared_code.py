import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from skell_vst_decompiler.shared_code import annotate, scan_modules


class SharedCodeTests(unittest.TestCase):
    def test_summary_and_hint_do_not_reclassify(self):
        # No vendor bytes are required: bounded owned fixtures substitute here.
        class StubPE:
            def __init__(self, path):
                self.path=Path(path)
                self.data=self.path.read_bytes()
                self.sha256=__import__('hashlib').sha256(self.data).hexdigest()
            def at_rva(self, start,n,executable=False):
                return self.data[start:start+n]
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            # Same first function across three files; different second functions.
            for index in range(3):
                (d/f'engine{index}.epl').write_bytes(b'Z'*64 + bytes([index+1])*64)
            with patch('skell_vst_decompiler.shared_code.PE',StubPE),\
                 patch('skell_vst_decompiler.shared_code.runtime_ranges',return_value=[(0,64,1),(64,128,1)]):
                result=scan_modules(d,min_region=32,max_region=4096)
            self.assertEqual(result['report']['total_scoped_regions'],6)
            self.assertEqual(result['report']['fingerprints_in_all_modules'],1)
            self.assertEqual(result['report']['distinct_region_fingerprints'],4)
            row=result['modules'][0]
            candidates=[{'start_rva':'0x0','end_rva_exclusive':'0x40','status':'CANDIDATE','score':50},
                        {'start_rva':'0x40','end_rva_exclusive':'0x80','status':'CANDIDATE','score':25},
                        {'start_rva':'0x40','end_rva_exclusive':'0x70','status':'UNRESOLVED'}]
            tagged=annotate(result,row['sha256'],candidates)
            self.assertEqual([r['cross_module_evidence']['module_frequency'] for r in tagged[:2]],[3,1])
            self.assertEqual(tagged[2]['cross_module_evidence']['status'],'UNRESOLVED_SCOPE')
            self.assertEqual([r['status'] for r in tagged],['CANDIDATE','CANDIDATE','UNRESOLVED'])
            self.assertEqual([r['score'] for r in tagged[:2]],[50,25])

    def test_expected_inventory_prevents_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            (d/'a.epl').write_bytes(b'Z'*64)
            (d/'b.epl').write_bytes(b'Z'*64)
            with self.assertRaisesRegex(ValueError,'names differ'):
                scan_modules(d,{'a.epl':{'size':64,'sha256':'0'*64}})
            with self.assertRaisesRegex(ValueError,'size differs'):
                scan_modules(d,{x:{'size':63,'sha256':'0'*64} for x in ('a.epl','b.epl')})
            (d/'link.epl').symlink_to(d/'a.epl')
            with self.assertRaisesRegex(ValueError,'Symlink'):
                scan_modules(d)

    def test_budgets_and_missing_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)
            (d/'a.epl').write_bytes(b'Z'*64)
            (d/'b.epl').write_bytes(b'Z'*64)
            with self.assertRaisesRegex(ValueError,'bounded region'):
                scan_modules(d,min_region=0)
            with patch('skell_vst_decompiler.shared_code.PE') as pe:
                pe.return_value.sha256='nope'
                with self.assertRaisesRegex(ValueError,'SHA-256 differs'):
                    scan_modules(d,{x:{'size':64,'sha256':'0'*64} for x in ('a.epl','b.epl')})
