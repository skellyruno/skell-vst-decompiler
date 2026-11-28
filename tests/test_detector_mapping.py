import math
import struct
import unittest
from types import SimpleNamespace
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.fieldrefs import field_refs
from skell_vst_decompiler.detector_mapping import fingerprint_record,verify_detector_mapping

class FieldTests(unittest.TestCase):
    def test_roles_and_signed_offset(self):
        ins=[Instruction(i,op,args) for i,(op,args) in enumerate([
            ('movss','xmm0,DWORD PTR [rbp-0x50]'),
            ('movss','DWORD PTR [rbp-0x50],xmm0'),
            ('addss','DWORD PTR [rbp-0x50],xmm1'),
            ('lea','rax,[rbp-0x50]'),('cmp','DWORD PTR [rbp-0x50],0'),
            ('movss','xmm1,DWORD PTR [rbp-0x500]')])]
        self.assertEqual([x['access'] for x in field_refs(ins,0,'rbp',-80)],['read','write','read-write','address','read'])
    def test_indexed_and_exact_register(self):
        ins=[Instruction(0,'movss','xmm0,DWORD PTR [rsi+rbx*4+0xd18]'),Instruction(1,'movss','xmm0,DWORD PTR [rdi+0xd18]'),Instruction(2,'movss','xmm0,DWORD PTR [rsi+rbx*4]')]
        refs=field_refs(ins,0,'rsi',0xd18)
        self.assertEqual(len(refs),1);self.assertTrue(refs[0]['indexed'])
        self.assertEqual(field_refs(ins,0,'rsi',0)[0]['site_rva'],'0x2')
    def test_bad_queries(self):
        for base,off in [('rip',0),('r16',0),('rsi',2**31),('rsi','2')]:
            with self.assertRaises(ValueError):field_refs([],0,base,off)
    def test_record_fingerprint_no_values(self):
        p=SimpleNamespace(sections=[SimpleNamespace(rva=0x1000,file_size=16,name='.data',characteristics=0x80000000)],at_rva=lambda a,n:struct.pack('<ff',1.,2.))
        r=fingerprint_record(p,0x1000,2)
        self.assertTrue(r['writable']);self.assertEqual(len(r['sha256']),64);self.assertNotIn('values',r)
        p.at_rva=lambda a,n:struct.pack('<ff',math.nan,2.)
        with self.assertRaises(ValueError):fingerprint_record(p,0x1000,2)
    def test_wrong_source_refused(self):
        with self.assertRaises(ValueError):verify_detector_mapping(SimpleNamespace(sha256='wrong'))
