import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.disasm import Instruction, disassemble
from skell_vst_decompiler.dispatch_audit import DispatchAudit, canonical, agreement
from skell_vst_decompiler.wrapper_dispatch import inspect_wrapper
from skell_vst_decompiler.navigation import runtime_ranges


class OperandTests(unittest.TestCase):
    def test_narrow_aliases(self):
        def c(op,args):return canonical(Instruction(0,op,args))
        self.assertEqual(c('movsd','QWORD PTR [rax+rsi*1+0x8],xmm1'),c('movsd','qword ptr [rax + rsi + 8], xmm1'))
        self.assertEqual(c('xor','r13,0xffffffffffffffff'),c('xor','r13,-1'))
        self.assertEqual(c('test','ch,0xef'),c('test','ch,-0x11'))
        self.assertNotEqual(c('xor','r13,0xffffffff'),c('xor','r13,-1'))
        self.assertNotEqual(c('mov','rax, qword ptr [rcx+rdx*2]'),c('mov','rax,qword ptr [rcx+rdx]'))
        self.assertNotEqual(c('mov','rax, qword ptr [rcx]'),c('mov','rax,dword ptr [rcx]'))
        self.assertNotEqual(c('xor','eax,-1'),c('xor','ecx,-1'))
        self.assertNotEqual(c('test','al,0x1ff'),c('test','al,-1'))


@unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')),'PE fixture tools required')
class OwnedDispatchTests(unittest.TestCase):
    def test_dispatch_and_wrapper(self):
        asm='''.text
.globl probe
.seh_proc probe
probe:
  .seh_endprologue
  call *readonly_slot(%rip)
  call *mutable_slot(%rip)
  call *__imp_external(%rip)
  call *%rax
  lea table(%rip),%r15
  movslq 0x60(%rax),%rdx
  call *(%r15,%rdx,8)
  .byte 0x66,0x90
  sar $1,%edx
  ret
.seh_endproc
target:
  ret
.section .rdata,"dr"
.p2align 3
readonly_slot:
  .quad target
.data
.p2align 3
mutable_slot:
  .quad target
table:
  .quad target,target,target,target,target,target,target,target
'''
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'probe.s').write_text(asm);(d/'ext.def').write_text('LIBRARY example.dll\nEXPORTS\n external\n')
            subprocess.run(['lld-link','/lib','/def:'+str(d/'ext.def'),'/machine:x64','/out:'+str(d/'ext.lib')],check=True)
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(d/'probe.s'),'-o',str(d/'probe.obj')],check=True)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/export:probe','/out:'+str(d/'probe.dll'),str(d/'probe.obj'),str(d/'ext.lib')],check=True)
            pe=PE(d/'probe.dll');start,end,_=runtime_ranges(pe)[0];a=DispatchAudit(pe);r=a.scope(start,end-start)
            self.assertEqual(r['status_counts'],{'readonly_relocated_candidate':1,'mutable_pointer_candidate':1,'import_boundary':1,'register_dynamic':1,'memory_dynamic':1})
            self.assertEqual(r['remaining_gnu_disagreements'],0)
            w=inspect_wrapper(pe,start,end-start)
            self.assertEqual(len(w['rows']),1);row=w['rows'][0];self.assertEqual(row['selector_offset'],96)
            self.assertEqual(len(row['table_load_candidates']),1);self.assertEqual(row['table_load_candidates'][0]['relocated_code_pointer_prefix'],8);self.assertTrue(row['table_load_candidates'][0]['writable'])
            i=next(x for x in disassemble(pe,start,end-start,'llvm-objdump') if x.mnemonic=='call' and '[rip' in x.operands)
            wrong=Instruction(i.address,'call','qword ptr [rip + 0]')
            self.assertEqual(a.classify(wrong,end)['status'],'rip_encoding_unverified')
            shift=next(x for x in disassemble(pe,start,end-start,'llvm-objdump') if x.mnemonic=='sar')
            self.assertFalse(agreement(pe,Instruction(shift.address,'sar','edx,2'),shift))
