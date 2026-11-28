import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.value_flow import audit_scope, decode_register, scan


class ValueFlowTests(unittest.TestCase):
    def test_register_encodings(self):
        self.assertEqual(decode_register(bytes.fromhex('f3450f59c1')),('mulss',4,8,9))
        self.assertEqual(decode_register(bytes.fromhex('f30f11c1')),('movss',4,1,0))
        self.assertEqual(decode_register(bytes.fromhex('660f28c1')),('movapd',16,0,1))
        for raw in ('f30f5900','f30f59','f30f59c100','67f30f59c1','f30f28c1'):
            self.assertIsNone(decode_register(bytes.fromhex(raw)))
        with self.assertRaises(ValueError): scan([],[],b'',0,limit=2)

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE toolchain')
    def test_owned_transforms_and_barriers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 # same expression, two arithmetic operations including memory RHS, register copy
 movss (%rbx), %xmm0
 mulss %xmm1, %xmm0
 addss 4(%rbx), %xmm0
 movss %xmm0, %xmm2
 movss %xmm2, (%rbx)
 # different expression, packed arithmetic
 movups (%rsi), %xmm3
 addps %xmm1, %xmm3
 movups %xmm3, (%rdi)
 # unary sqrt reads source, not prior destination
 movsd (%rbx), %xmm4
 sqrtsd %xmm4, %xmm5
 movsd %xmm5, (%rbx)
 # reject a pointer mutation
 movss (%rbx), %xmm0
 mulss %xmm1, %xmm0
 addq $4, %rbx
 movss %xmm0, (%rbx)
 # reject precision crossing
 movss (%rbx), %xmm0
 mulsd %xmm1, %xmm0
 movsd %xmm0, (%rbx)
 # reject self-subtraction
 movss (%rbx), %xmm0
 subss %xmm0, %xmm0
 movss %xmm0, (%rbx)
 # reject pure copy and stack-only source
 movss (%rbx), %xmm0
 movss %xmm0, (%rsi)
 movss (%rsp), %xmm0
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 # reject branch across chain
 movss (%rbx), %xmm0
 jmp next
next:
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 # reject old state across store
 movss (%rbx), %xmm0
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 movss %xmm0, (%rsi)
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); s=pe.section('.text')
            r=audit_scope(pe,pe.sha256,s.rva,s.virtual_size)
            self.assertEqual(r['paths'],{'same_expression':3,'different_expression':1})
            self.assertEqual(r['arithmetic_depths'],{'2':1,'1':3})
            self.assertEqual(r['source_expression_counts'],{'2':1,'1':3})
            short=audit_scope(pe,pe.sha256,s.rva,s.virtual_size,limit=3)
            self.assertEqual(short['paths'],{'same_expression':2,'different_expression':2})
            self.assertEqual(short['arithmetic_depths'],{'1':4})
            with self.assertRaises(PEFormatError): audit_scope(pe,'0'*64,s.rva,s.virtual_size)
            with self.assertRaises(ValueError): audit_scope(pe,pe.sha256,s.rva,32769)
            self.assertEqual(audit_scope(pe,pe.sha256,s.rva+s.virtual_size-1,1)['total'],0)
