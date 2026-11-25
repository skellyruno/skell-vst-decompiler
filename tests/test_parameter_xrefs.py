import unittest
from unittest.mock import Mock
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.parameter_xrefs import local_references, scalar_reader_chains, raw_lea_hits

class ParameterXrefTests(unittest.TestCase):
    def setUp(self):
        self.pe=Mock(image_base=0x180000000)
        self.wanted={0x1000:0x2000}
        self.literals={0x2000:[{'name':'gain','encoding':'ascii'}]}

    def instructions(self,*pairs):
        return [Instruction(self.pe.image_base+0x1000+i*4,op,args) for i,(op,args) in enumerate(pairs)]

    def test_direct_argument_and_reader(self):
        ins=self.instructions(('lea','rdx, [rip + 0x1000] # 0x180002000'),('lea','rcx,[rsp+0x20]'),('call','0x180003000 <ctor>'),('mov','rdx, qword ptr [rax]'),('mov','rcx,r14'),('call','0x180004000 <reader>'),('mov','ecx, DWORD PTR [rax]'),('movd','xmm0,ecx'))
        rows=local_references(self.pe,ins,self.wanted,self.literals)
        self.assertEqual(rows[0]['direct_argument_call']['target_rva'],'0x3000')
        chain=scalar_reader_chains(self.pe,ins,rows)
        self.assertEqual(chain[0]['reader_target_rva'],'0x4000')
        self.assertEqual(chain[0]['scalar_load_rva'],'0x1018')
        bad=list(ins);bad[-1]=Instruction(ins[-1].address,'movd','xmm0,edx')
        self.assertEqual(scalar_reader_chains(self.pe,bad,rows),[])

    def test_clear_on_branch_and_clobber(self):
        for op,arg in [('jne','0x180002000'),('mov','edx,0x0'),('mov','rdx,rax'),('call','qword ptr [rax]')]:
            ins=self.instructions(('lea','rdx,[rip+0x1000] # 0x180002000'),(op,arg),('call','0x180003000'))
            self.assertNotIn('direct_argument_call',local_references(self.pe,ins,self.wanted,self.literals)[0])

    def test_no_raw_only_evidence(self):
        self.assertEqual(local_references(self.pe,self.instructions(('mov','rdx,[rip+0x1000] # 0x180002000')),self.wanted,self.literals),[])
        self.assertEqual(local_references(self.pe,self.instructions(('lea','rdx,[rip+0x1000] # 0x180002010')),self.wanted,self.literals),[])

    def test_raw_lea_displacement(self):
        import struct
        raw=b'\x48\x8d\x15'+struct.pack('<i',0x2000-0x1007)
        self.pe.sections=[Mock(executable=True,rva=0x1000,file_size=len(raw))]
        self.pe.sections[0].name='.text';self.pe.at_rva.return_value=raw
        self.assertEqual(list(raw_lea_hits(self.pe,{0x2000:[]})),[(0x1000,0x2000)])
        self.assertEqual(list(raw_lea_hits(self.pe,{0x2001:[]})),[])
