import unittest
from skell_vst_decompiler.structural_match import canonical, compare
from skell_vst_decompiler.disasm import Instruction

class StructuralMatchTests(unittest.TestCase):
    def test_prefix_pseudo_instruction(self):
        self.assertEqual(canonical(Instruction(1,'data16','nop WORD PTR [rax]')),'nop')
        self.assertEqual(canonical(Instruction(1,'mulss','xmm0,xmm1')),'mulss')
        self.assertEqual(canonical(Instruction(1,'data16','mov rax,rcx')),'data16')
    def test_reject_unavailable(self):
        with self.assertRaises(ValueError):compare('/absent/a.epl',0,'/absent/b.epl',0)
