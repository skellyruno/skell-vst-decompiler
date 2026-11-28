import struct
import unittest
from unittest.mock import Mock
from skell_vst_decompiler.context_paths import edges,context
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.pe import PEFormatError

class ContextTests(unittest.TestCase):
    def test_relative_and_pointer(self):
        p=Mock(image_base=0x100000)
        raw={0x100:b'\xe8'+struct.pack('<i',0x200-0x105)+b'\x90',0x106:b'\xff\x15'+struct.pack('<i',0x300-0x10c),0x300:struct.pack('<Q',0x100200),0x200:b'\x90'}
        def read(r,n,**kw):
            if r not in raw:raise PEFormatError('bad')
            return raw[r][:n]
        p.at_rva.side_effect=read
        e,n=edges(p,[Instruction(0x100100,'call','100200 <symbol>'),Instruction(0x100106,'call','QWORD PTR [rip+0x1f4]')],0x100,0x10c)
        self.assertEqual(n,0);self.assertEqual(e[0]['target'],0x200);self.assertEqual(e[1]['slot'],0x300)
        with self.assertRaisesRegex(ValueError,'disagreement'):edges(p,[Instruction(0x100100,'call','0x100201')],0x100,0x106)
    def test_context_and_mixed(self):
        rows=[dict(start_rva=i,local_role_evidence={'role':'PROCESSING_CANDIDATE'}) for i in range(5)]
        r=context(rows,[(0,2),(1,3),(2,4),(3,4),(4,4)],{0:'audio',1:'utility'})
        self.assertEqual([x['context_status'] for x in r],['AUDIO_CONTEXT_CANDIDATE','NON_AUDIO_CONTEXT_ONLY','AUDIO_CONTEXT_CANDIDATE','NON_AUDIO_CONTEXT_ONLY','UNRESOLVED'])
        with self.assertRaises(ValueError):context(rows,[],{7:'audio'})
    def test_indirect_unresolved(self):
        p=Mock(image_base=0x100000);p.at_rva.return_value=b'\xff\xd0\x90\x90\x90\x90'
        self.assertEqual(edges(p,[Instruction(0x100100,'call','rax')],0x100,0x106),([],1))
    def test_manifest_shape(self):
        from pathlib import Path
        import tempfile
        from skell_vst_decompiler.context_paths import review_manifest
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.dll';p.write_bytes(b'fixture')
            with self.assertRaises(ValueError):review_manifest(p,{'scopes':[]})
            with self.assertRaises(ValueError):review_manifest(p,{'binary_sha256':'bad','scopes':[True],'roots':[]})
