import copy
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.deep_signal_graph import verify

class DeepSignalGraphTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]
        self.manifest=json.loads((self.root/'reports/native_scoped/gem_vcc_deeper_signal_graph.json').read_text())

    def test_manifest_coverage(self):
        self.assertEqual(len(self.manifest['regions']),8)
        self.assertEqual(sum(len(r['checks']) for r in self.manifest['regions']),267)
        self.assertEqual(len(self.manifest['calls']),12)
        self.assertEqual(len(self.manifest['constants']),5)
        self.assertEqual([r['triplets'] for r in self.manifest['vcc_tables']],[8,8])
        for row in self.manifest['regions']:
            self.assertEqual(len(row['sha256']),64)
            self.assertTrue(0<int(row['end'],16)-int(row['start'],16)<=32768)
            self.assertEqual(len(set(a for a,_ in row['checks'])),len(row['checks']))

    def test_wrong_fingerprint_rejected_before_decoding(self):
        pe=Mock(path=Path('Gem Dopamine-64.vst3'),sha256='mismatch')
        with patch('skell_vst_decompiler.deep_signal_graph.disassemble') as analyzer:
            with self.assertRaisesRegex(ValueError,'source fingerprint'):
                verify(pe,self.manifest)
            analyzer.assert_not_called()

    def test_fixture_verified_and_tampering_rejected(self):
        # An owned, non-vendor synthetic PE-like interface proves the parser
        # checks region bytes, calls, floating literals and indirect table hashes.
        me=Mock(path=Path('fixture.dll'),sha256='owned',image_base=0x180000000)
        region={'file':'fixture.dll','binary_sha256':'owned','id':'test','start':'0x1000',
                'end':'0x1005','checks':[['0x1000','call']]}
        region['sha256']=hashlib.sha256(b'\xe8\x00\x00\x00\x00').hexdigest()
        raw=struct.pack('<3Q',*(me.image_base+x for x in (0x2000,0x2008,0x2000)))
        report={'schema_version':1,'type':'verified_static_signal_paths','regions':[region],
                'calls':[{'file':'fixture.dll','site':'0x1000','target':'0x1005'}],
                'constants':[{'file':'fixture.dll','rva':'0x3000','f32':3.0}],
                'vcc_tables':[{'file':'fixture.dll','binary_sha256':'owned','rva':'0x4000',
                               'entries':3,'triplets':1,'unique_targets':2,'sha256':hashlib.sha256(raw).hexdigest()}]}
        samples={0x1000:b'\xe8\x00\x00\x00\x00',0x3000:struct.pack('<f',3.0),0x4000:raw}
        me.at_rva.side_effect=lambda r,n,**kw:samples[r] if r in samples else b'\x90'
        code=[Instruction(me.image_base+0x1000,'call',hex(me.image_base+0x1005))]
        with patch('skell_vst_decompiler.deep_signal_graph.disassemble',return_value=code):
            result=verify(me,report)
            self.assertEqual((result['direct_calls'],result['dispatch_tables'],result['scalar_constants']),(1,1,1))
            with patch('skell_vst_decompiler.deep_signal_graph.disassemble',return_value=[Instruction(me.image_base+0x1000,'call',hex(me.image_base+0x1005)+' <owned+0x1>')]):
                self.assertEqual(verify(me,report)['direct_calls'],1)
            bad=copy.deepcopy(report);bad['calls'][0]['target']='0x1006'
            with self.assertRaisesRegex(ValueError,'call target'):verify(me,bad)
            bad=copy.deepcopy(report);bad['constants'][0]['f32']=4.0
            with self.assertRaisesRegex(ValueError,'scalar'):verify(me,bad)
            bad=copy.deepcopy(report);bad['vcc_tables'][0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'table hash'):verify(me,bad)
            bad=copy.deepcopy(report);bad['regions'][0]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'region hash'):verify(me,bad)

if __name__=='__main__':unittest.main()
