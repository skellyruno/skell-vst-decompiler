import unittest
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.dsp_discovery import features,discover

class DiscoveryTests(unittest.TestCase):
    def test_features(self):
        seq=[Instruction(0x1000,'mulss','xmm0,DWORD PTR [rax]'),Instruction(0x1004,'vaddps','xmm1,xmm0,xmm2'),Instruction(0x1008,'jne','0x1000'),Instruction(0x100c,'mov','rax,rbx')]
        self.assertEqual(features(seq),{'arithmetic':2,'vector_memory':1,'backward_branches':1,'score':7})
    def test_no_target(self):
        with self.assertRaises(ValueError):discover('/no/such/module')
