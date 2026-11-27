import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.memory_effects import decode_memory, operand_matches, address_class, audit_scope
from skell_vst_decompiler.pe import PE, PEFormatError


class MemoryEffectsTests(unittest.TestCase):
    def test_byte_forms(self):
        d=decode_memory(bytes.fromhex('f30f10448bfc'))
        self.assertEqual(d,('movss','read',4,0,'rbx','rcx',4,-4))
        for expr in ('xmm0, DWORD PTR [rbx+rcx*4-0x4]','xmm0, dword ptr [4*rcx + rbx - 4]'):
            self.assertTrue(operand_matches(Instruction(0,'movss',expr),d))
        for expr in ('xmm0, dword ptr [rbx+rcx*2-4]','xmm1, dword ptr [rbx+rcx*4-4]','dword ptr [rbx+rcx*4-4], xmm0'):
            self.assertFalse(operand_matches(Instruction(0,'movss',expr),d))
        self.assertEqual(decode_memory(bytes.fromhex('f2440f110508000000')),('movsd','write',8,8,'rip',None,1,8))
        self.assertEqual(decode_memory(bytes.fromhex('0f1000'))[0],'movups')
        self.assertEqual(decode_memory(bytes.fromhex('660f2900'))[0],'movapd')
        for v in ('f30f10c0','f30f10448b','f30f10448bfc00','67f30f1000','f30f2800'):
            self.assertIsNone(decode_memory(bytes.fromhex(v)))
        self.assertEqual(address_class('rbp',None),'frame_or_general')

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE toolchain')
    def test_owned_pe(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 movss (%rbx), %xmm0
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 movss (%rsp), %xmm0
 mulss %xmm1, %xmm0
 movss %xmm0, (%rsp)
 movss 4(%rbx), %xmm0
 mulss %xmm1, %xmm0
 movss %xmm0, 8(%rbx)
 movsd (%rbp), %xmm2
 movsd constant(%rip), %xmm1
 movss (%rbx), %xmm0
 mulss %xmm0, %xmm2
 movss %xmm0, (%rbx)
 movss (%rbx), %xmm0
 mulsd %xmm1, %xmm0
 movss %xmm0, (%rbx)
 movups (%rsi), %xmm3
 addps %xmm1, %xmm3
 movups %xmm3, (%rsi)
 retq
.section .rdata,"dr"
constant: .double 1.0
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); s=pe.section('.text')
            r=audit_scope(pe,pe.sha256,s.rva,s.virtual_size)
            self.assertEqual(r['memory_classes'],{'read_general_register':5,'write_general_register':5,'read_stack_pointer':1,'write_stack_pointer':1,'read_frame_or_general':1,'read_rip_relative':1})
            self.assertEqual(r['local_read_arithmetic_write'],2)
            self.assertEqual(r['operand_rejections'],0)
            self.assertEqual(r['selected_fp_sites'],6)
            with self.assertRaises(PEFormatError): audit_scope(pe,'0'*64,s.rva,s.virtual_size)
            with self.assertRaises(ValueError): audit_scope(pe,pe.sha256,s.rva,32769)
            self.assertEqual(audit_scope(pe,pe.sha256,s.rva+s.virtual_size-1,1)['verified_memory_sites'],0)
