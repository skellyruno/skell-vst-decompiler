"""Structural regression for the additional exact-build evidence, no vendor binary needed."""
import copy
import hashlib
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.equations import TVB_SHA256
from skell_vst_decompiler.tvb_limiter_setup import verify


class ReleaseDelayTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1]/'reports/limiter_setup/tvb_release_delay.json'
        self.report = json.loads(path.read_text())

    def test_manifest(self):
        r = self.report
        self.assertEqual(r['binary_sha256'], TVB_SHA256)
        self.assertEqual(len(r['regions']), 7)
        self.assertEqual(sum(len(x['checkpoints']) for x in r['regions']), 170)
        self.assertEqual(sum(len(x['imports']) for x in r['regions']), 13)
        self.assertEqual(len(r['constants']), 20)
        seen = set()
        for region in r['regions']:
            start, end = (int(region[k],16) for k in ('start_rva','end_rva_exclusive'))
            self.assertLess(start,end)
            self.assertRegex(region['sha256'],r'^[0-9a-f]{64}$')
            local = {a for a,_ in region['checkpoints']}
            self.assertEqual(len(local),len(region['checkpoints']))
            self.assertFalse(seen & local)
            seen.update(local)
            self.assertTrue(all(start <= int(a,16) < end for a in local))
            self.assertTrue(all(a in local for a,_ in region['imports']))

    def test_verifier_fixture(self):
        report = copy.deepcopy(self.report)
        pe = Mock(sha256=TVB_SHA256,image_base=0x180000000)
        data = {}
        by_start = {}
        for region in report['regions']:
            start,end = (int(region[k],16) for k in ('start_rva','end_rva_exclusive'))
            data[start] = bytes(end-start)
            region['sha256'] = hashlib.sha256(data[start]).hexdigest()
            by_start[start] = region
        for addr,fmt,value in report['constants']:
            data[int(addr,16)] = struct.pack('<'+fmt,value)
        pe.at_rva.side_effect = lambda r,n,**kw: data[r]
        def decode(_pe,start,length,objdump):
            return [Instruction(pe.image_base+int(a,16),m,'') for a,m in by_start[start]['checkpoints']]
        all_imports = {a:s for reg in report['regions'] for a,s in reg['imports']}
        def imports(_pe,ins):
            return [{'site_rva':a,'symbol':all_imports[a]} for i in ins
                    if (a:=hex(i.address-pe.image_base)) in all_imports]
        with patch('skell_vst_decompiler.tvb_limiter_setup.disassemble',side_effect=decode), patch('skell_vst_decompiler.tvb_limiter_setup.imported_call_sites',side_effect=imports):
            self.assertEqual(verify(pe,report)['checkpoints'],170)
            report['constants'][0][2] = 61.
            with self.assertRaisesRegex(ValueError,'Scalar constant mismatch'):
                verify(pe,report)

    def test_wrong_source(self):
        pe = Mock(sha256='wrong')
        with self.assertRaisesRegex(ValueError,'Unexpected source fingerprint'):
            verify(pe,self.report)
        pe.at_rva.assert_not_called()
