import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.disasm import Instruction, disassemble
from skell_vst_decompiler.flow_guards import direct_target, entry_guards, transparent
from skell_vst_decompiler.value_flow import scan


class FlowGuardsTests(unittest.TestCase):
    def test_relative_forms(self):
        self.assertEqual(direct_target(bytes.fromhex('75fc'),0x100,'jnz'),0xfe)
        self.assertEqual(direct_target(bytes.fromhex('0f8500010000'),0x100,'jne'),0x206)
        self.assertEqual(direct_target(bytes.fromhex('e8fbffffff'),0x100,'call'),0x100)
        self.assertEqual(direct_target(bytes.fromhex('ebfe'),0x100,'jmp'),0x100)
        for raw,op in [('75fc','je'),('0f85000100','jne'),('ffe0','jmp'),('66ebfc','jmp')]:
            self.assertIsNone(direct_target(bytes.fromhex(raw),0x100,op))

    def test_transparency(self):
        i=Instruction(0,'cmp','r8, r9')
        self.assertTrue(transparent(bytes.fromhex('4d39c8'),i,i))
        self.assertFalse(transparent(bytes.fromhex('4d39c8'),i,Instruction(0,'cmp','r9,r8')))
        self.assertFalse(transparent(bytes.fromhex('483900'),i,i))
        self.assertFalse(transparent(bytes.fromhex('4883c001'),i,i))
        t=Instruction(0,'test','eax,eax')
        self.assertTrue(transparent(bytes.fromhex('85c0'),t,t))

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE toolchain')
    def test_owned_entry_and_transparent_controls(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 jmp middle
 movss (%rbx), %xmm0
middle:
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 movss (%rbx), %xmm0
 nop
 testl %eax, %eax
 cmpq %r9, %r8
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 movss (%rbx), %xmm0
 addq $4, %rbx
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 movss (%rbx), %xmm0
 testl %eax, (%rbx)
 mulss %xmm1, %xmm0
 movss %xmm0, (%rbx)
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); s=pe.section('.text'); va=pe.image_base+s.rva
            raw=pe.at_rva(s.rva,s.virtual_size,executable=True)
            a,b=[disassemble(pe,s.rva,s.virtual_size,t) for t in ('objdump','llvm-objdump')]
            entries,counts=entry_guards(a,b,raw,va)
            self.assertEqual(len(entries),1)
            self.assertEqual(counts,{'in_window_common_boundary':1})
            self.assertEqual(scan(a,b,raw,va)['total'],1)
            self.assertEqual(scan(a,b,raw,va,entries=entries)['total'],0)
            self.assertEqual(scan(a,b,raw,va,entries=entries,allow_transparent=True)['paths'],{'same_expression':1})
            self.assertEqual(scan(a,b,raw,va,allow_transparent=True)['total'],2)
            with self.assertRaises(ValueError): scan(a,b,raw,va,entries=[va-1])
