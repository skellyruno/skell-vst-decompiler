import struct
import unittest
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.navigation import runtime_ranges,containing_range,scan_refs
from skell_vst_decompiler.curve_provenance import immediate_initializer,summary,verify_curves
from skell_vst_decompiler.pe import PEFormatError

class Fixture:
    image_base=0x180000000
    exception_directory=(0x3000,24)
    def at_rva(self,rva,size,executable=False):
        if rva==0x3000:return struct.pack('<IIIIII',0x1000,0x1100,0x4000,0x1200,0x1240,0x4010)
        return bytes(size)

class NavigationTests(unittest.TestCase):
    def test_runtime_lookup_and_gaps(self):
        ranges=runtime_ranges(Fixture())
        self.assertEqual(len(ranges),2)
        self.assertEqual(containing_range(ranges,0x10ff)['start_rva'],'0x1000')
        self.assertIsNone(containing_range(ranges,0x1100))
        self.assertEqual(containing_range(ranges,0x1200)['bytes'],64)
    def test_bad_directory(self):
        p=Fixture();p.exception_directory=(0x3000,23)
        with self.assertRaises(PEFormatError):runtime_ranges(p)
    def test_xref_and_range(self):
        p=Fixture();ins=[Instruction(p.image_base+0x1010,'lea','rcx,[rip+0x1] # 0x180003000'),Instruction(p.image_base+0x1201,'call','0x180003004'),Instruction(p.image_base+0x1206,'mov','eax,0x3000')]
        found=scan_refs(p,ins,0x3000,8,runtime_ranges(p))
        self.assertEqual(len(found),2);self.assertEqual(found[0]['containing_range']['start_rva'],'0x1000')
        self.assertEqual(found[1]['kind'],'direct-control-flow')
    def test_initializer_complete(self):
        ins=[Instruction(i,op,args) for i,(op,args) in enumerate([('xor','eax,eax'),('mov','QWORD PTR [rcx],rax'),('mov','DWORD PTR [rcx+0x8],0x3f800000'),('mov','rax,rcx'),('ret','')])]
        b=immediate_initializer(ins,12)
        self.assertEqual(struct.unpack('<fff',b),(0,0,1))
        self.assertTrue(summary(b,1,3)['all_finite'])
    def test_initializer_rejects_missing_overlap_unknown_nan(self):
        cases=[ [('mov','DWORD PTR [rcx],eax'),('ret','')], [('xor','eax,eax'),('mov','DWORD PTR [rcx],eax'),('mov','DWORD PTR [rcx],eax'),('ret','')], [('mov','DWORD PTR [rcx],0x7fc00000'),('ret','')], [('ret','')], [('jmp','0x123'),('ret','')]]
        for seq in cases:
            with self.subTest(seq=seq),self.assertRaises(ValueError):immediate_initializer([Instruction(i,*x) for i,x in enumerate(seq)],4)
    def test_wrong_binary_refused(self):
        p=Fixture();p.sha256='wrong'
        with self.assertRaises(ValueError):verify_curves(p)
