import unittest
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.function_roles import role_evidence


def seq(*ops):
    return [Instruction(0x1000+i*4,op,args) for i,(op,args) in enumerate(ops)]


class FunctionRoleTests(unittest.TestCase):
    def test_processing(self):
        s=seq(('movss','xmm0,dword ptr [rcx+rax*4]'),('mulss','xmm0,xmm1'),('addss','xmm0,xmm2'),('movss','dword ptr [rcx+rax*4],xmm0'),('jne','0x1000 <loop>'))
        self.assertEqual(role_evidence(s)['role'],'PROCESSING_CANDIDATE')

    def test_stack_and_out_of_scope_branch(self):
        s=seq(('movsd','xmm0,qword ptr [rsp+0x20]'),('mulsd','xmm0,xmm1'),('addsd','xmm0,xmm2'),('movsd','qword ptr [rsp+0x28],xmm0'),('jne','0x800'))
        r=role_evidence(s);self.assertEqual(r['role'],'UNRESOLVED');self.assertEqual(r['features'].get('back_edges',0),0)

    def test_byte_candidate_not_dsp(self):
        s=seq(('movzx','eax,byte ptr [rcx]'),('mov','byte ptr [rdx],al'),('jne','0x1000'))
        self.assertEqual(role_evidence(s)['role'],'BYTE_PROCESSING_CANDIDATE')

    def test_empty_and_scalar(self):
        self.assertEqual(role_evidence([])['role'],'UNRESOLVED')
        self.assertEqual(role_evidence(seq(('mulss','xmm0,xmm0'),('addss','xmm0,xmm1')))['role'],'UNRESOLVED')
