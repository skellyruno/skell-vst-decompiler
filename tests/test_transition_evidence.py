import copy
import hashlib
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.deep_signal_graph import verify

class TransitionEvidenceTests(unittest.TestCase):
    def test_manifest(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'reports/native_scoped/gem_output_vcc_transitions.json').read_text())
        self.assertEqual(len(r['regions']),21)
        self.assertEqual(sum(len(x['checks']) for x in r['regions']),643)
        self.assertEqual(len(r['calls']),6)
        self.assertEqual(len(r['transition_tables']),8)

    def test_table_provenance_and_target_classes(self):
        p=Mock(path=Path('owned.dll'),sha256='fixture',image_base=0x180000000)
        raw=struct.pack('<2Q',p.image_base+0x2000,p.image_base+0x3000)
        regions=[dict(file=p.path.name,binary_sha256=p.sha256,id=id,start=hex(addr),end=hex(addr+1),sha256=hashlib.sha256(b'\xc3').hexdigest(),checks=[[hex(addr),'ret']]) for id,addr in [('countdown_dispatch_fixture',0x1000),('transition_reset_fixture',0x2000),('no_op',0x3000)]]
        table=dict(file=p.path.name,binary_sha256=p.sha256,dispatch_rva='0x1000',table_rva='0x4000',target_count=2,table_sha256=hashlib.sha256(raw).hexdigest())
        r=dict(schema_version=1,type='verified_static_signal_paths',regions=regions,transition_tables=[table])
        p.at_rva.side_effect=lambda addr,n,**kw:raw if addr==0x4000 else b'\xc3'
        with patch('skell_vst_decompiler.deep_signal_graph.disassemble',side_effect=lambda pe,start,n,tool:[Instruction(pe.image_base+start,'ret','')]):
            self.assertEqual(verify(p,r)['transition_tables'],1)
            bad=copy.deepcopy(r);bad['transition_tables'][0]['table_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'hash mismatch'):verify(p,bad)
            bad=copy.deepcopy(r);bad['regions'][1]['id']='unrelated'
            with self.assertRaisesRegex(ValueError,'target class'):verify(p,bad)
            bad=copy.deepcopy(r);bad['transition_tables'][0]['binary_sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'identity'):verify(p,bad)
