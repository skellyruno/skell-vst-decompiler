import shutil, subprocess, tempfile, unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.boundary_paths import BoundaryAudit, adjacent_import_load, transfer
from skell_vst_decompiler.disasm import Instruction, disassemble
from skell_vst_decompiler.navigation import runtime_ranges


@unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'PE fixture tools required')
class ImportCandidateTests(unittest.TestCase):
    def test_prefix_and_adjacent_candidates(self):
        asm='''.text
.globl probe
.seh_proc probe
probe:
 .seh_endprologue
 .byte 0x48
 call *__imp_external(%rip)
 mov __imp_external(%rip),%rax
 call *%rax
 mov __imp_external(%rip),%r11
 call *%r11
 mov __imp_external(%rip),%rax
 xor %eax,%eax
 call *%rax
 mov __imp_external(%rip),%r10
 call *%r11
 .byte 0x48
 jmp *__imp_external(%rip)
.seh_endproc
'''
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'probe.s').write_text(asm);(d/'ext.def').write_text('LIBRARY example.dll\nEXPORTS\n external\n')
            subprocess.run(['lld-link','/lib','/def:'+str(d/'ext.def'),'/machine:x64','/out:'+str(d/'ext.lib')],check=True)
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(d/'probe.s'),'-o',str(d/'probe.obj')],check=True)
            subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/export:probe','/out:'+str(d/'probe.dll'),str(d/'probe.obj'),str(d/'ext.lib')],check=True)
            p=PE(d/'probe.dll');start,end,_=runtime_ranges(p)[0];r=BoundaryAudit(p).scope(start,end-start)
            self.assertEqual(r['counts'],{'import_boundary':2})
            self.assertEqual(r['rejected'],0)
            c=r['adjacent_import_candidates'];self.assertEqual(len(c),2)
            self.assertTrue(all(x['symbol']=='external' and x['status']=='adjacent_import_load_candidate' for x in c))
            self.assertIsNone(transfer(p,start,start+6))
            a=disassemble(p,start,end-start,'llvm-objdump');load,call=a[1:3]
            self.assertIsNone(adjacent_import_load(p,load,Instruction(call.address,'call','rcx'),end))
            self.assertIsNone(adjacent_import_load(p,load,call,call.address-p.image_base+1))
            bad=Instruction(load.address,'mov','rax,qword ptr [rip + 0]')
            self.assertIsNone(adjacent_import_load(p,bad,call,end))
