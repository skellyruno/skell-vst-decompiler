import math
import struct
import unittest
from types import SimpleNamespace
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.coloration import sos_summary,nearest_rate,lookup_slots,verify_coloration
from skell_vst_decompiler.parameter_mapping import indexed_slot_names,verify_parameter_mapping

class ColorTests(unittest.TestCase):
    def test_identity_and_gain(self):
        data=struct.pack('<10d',1,0,0,0,0,2,0,0,0,0)
        r=sos_summary(data,(48000,),2)
        self.assertEqual(r['coefficient_count'],10)
        self.assertTrue(r['rate_summaries'][0]['stable'])
        self.assertAlmostEqual(r['rate_summaries'][0]['linear_response_db']['1000'],20*math.log10(2),places=5)
        self.assertNotIn('coefficients',r)
    def test_unstable_poles(self):
        data=struct.pack('<5d',1,0,0,-1.1,0)
        self.assertFalse(sos_summary(data,(48000,),1)['rate_summaries'][0]['stable'])
    def test_first_order_and_nyquist(self):
        r=sos_summary(struct.pack('<5d',.5,-.5,0,-.9,0),(16000,),1)
        self.assertNotIn('10000',r['rate_summaries'][0]['linear_response_db'])
        self.assertAlmostEqual(r['rate_summaries'][0]['max_pole_radius'],.9)
    def test_bad_data(self):
        for data,rates,stages in [(b'',(48000,),1),(struct.pack('<5d',math.nan,0,0,0,0),(48000,),1),(bytes(40),(0,),1),(bytes(40),(48000,),65)]:
            with self.assertRaises(ValueError):sos_summary(data,rates,stages)
    def test_nearest_tie(self):
        self.assertEqual(nearest_rate((40000,60000),50000),0)
        self.assertEqual(nearest_rate((40000,60000),50001),1)
        with self.assertRaises(ValueError):nearest_rate((48000,),math.nan)

class BindingTests(unittest.TestCase):
    def test_lookup_pattern(self):
        p=SimpleNamespace(image_base=0,cstring_rva=lambda a,n:'comp_ratio')
        ins=[Instruction(i,op,args) for i,(op,args) in enumerate([('lea','rdx,[rip+0x20] # 0x1000'),('lea','rcx,[rbp+0x10]'),('call','0x2000'),('mov','rdx,QWORD PTR [rax]'),('mov','rcx,r12'),('call','0x3000'),('mov','QWORD PTR [r15+0x30],rax')])]
        r=lookup_slots(p,ins);self.assertEqual(r[0]['slot_offset'],'0x30');self.assertEqual(r[0]['literal_base'],'r15')
        ins[4]=Instruction(4,'mov','rcx,r13');self.assertEqual(lookup_slots(p,ins),[])
    def test_indexed_slots(self):
        p=SimpleNamespace(image_base=0,cstring_rva=lambda a,n:'param_'+str(a))
        ins=[Instruction(i,op,args) for i,(op,args) in enumerate([('lea','rax,[rip+0x20] # 0x1000'),('mov','QWORD PTR [rbp+0x90],rax'),('lea','rax,[rip+0x20] # 0x2000'),('mov','QWORD PTR [rbp+0x98],rax')])]
        self.assertEqual([r['slot_offset'] for r in indexed_slot_names(p,ins,0x90,0xe80,2)],['0xe80','0xe88'])
        with self.assertRaises(ValueError):indexed_slot_names(p,ins[:2],0x90,0xe80,2)
        with self.assertRaises(ValueError):indexed_slot_names(p,ins+ins,0x90,0xe80,2)
    def test_wrong_binary(self):
        for fn in (verify_coloration,verify_parameter_mapping):
            with self.assertRaises(ValueError):fn(SimpleNamespace(sha256='wrong'))
