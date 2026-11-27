import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.disasm import Instruction, disassemble
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.transfer_triage import (parse_raw,raw_decode,relative,indirect_kind,
                                                  target_agrees,boundary_kind,triage)


class TransferTriageTests(unittest.TestCase):
    def test_exact_forms(self):
        self.assertEqual(relative(bytes.fromhex('e3fe'),0x100,'jrcxz'),0x100)
        self.assertEqual(relative(bytes.fromhex('e0fc'),0x100,'loopnz'),0xfe)
        self.assertIsNone(relative(bytes.fromhex('e0fc'),'0x100','loope'))
        self.assertIsNone(relative(bytes.fromhex('e3'),'0x100','jrcxz'))
        self.assertEqual(indirect_kind(bytes.fromhex('41ffd0'),'call','r8'),'indirect_register')
        self.assertIsNone(indirect_kind(bytes.fromhex('41ffd0'),'call','rax'))
        self.assertEqual(indirect_kind(bytes.fromhex('ff248d11223344'),'jmp','qword ptr [rcx*4+0x44332211]'),'indirect_memory')
        self.assertEqual(indirect_kind(bytes.fromhex('ff542408'),'call','qword ptr [rsp+8]'),'indirect_memory')
        self.assertIsNone(indirect_kind(bytes.fromhex('ff5424'),'call','qword ptr [rsp+8]'))
        self.assertIsNone(indirect_kind(bytes.fromhex('ff18'),'call','qword ptr [rax]'))
        self.assertIsNone(indirect_kind(bytes.fromhex('ff20'),'call','qword ptr [rax]'))

    def test_raw_rows_and_boundaries(self):
        raw=bytes.fromhex('eb019090')
        text='100: eb 01 \tjmp 0x103\n102: 90 \tnop\n103: 90 \tnop\n'
        rows=parse_raw(text,raw,0x100)
        self.assertEqual(target_agrees(rows[0x100]),0x103)
        self.assertEqual(boundary_kind(0x101,[rows,rows]),'interior/interior')
        self.assertEqual(boundary_kind(0x103,[rows,{}]),'start/uncovered')
        self.assertEqual(boundary_kind(0x105,[rows,rows]),'uncovered/uncovered')
        with self.assertRaises(PEFormatError):parse_raw(text,bytes.fromhex('eb029090'),0x100)
        with self.assertRaises(ValueError):parse_raw(text+text,raw,0x100)
        self.assertEqual(parse_raw('103: eb 01 \tjmp 0x106',raw,0x100),{})
        self.assertIsNone(target_agrees(parse_raw('100: eb 01 \tjmp 0x102',raw,0x100)[0x100]))

    def test_terminal_and_conflict(self):
        va=0x100;raw=bytes.fromhex('9090ebfc')
        a=[Instruction(va,'nop',''),Instruction(va+1,'nop',''),Instruction(va+2,'jmp','0x100')]
        r=parse_raw('100: 90 \tnop\n101: 90 \tnop\n102: eb fc \tjmp 0x100',raw,va)
        guards,report=triage(a,a,[r,r],raw,va)
        self.assertEqual(guards,{va})
        self.assertEqual(report['baseline'],{'unresolved':1})
        self.assertEqual(report['recovered_direct'],{'common_boundary':1})
        self.assertEqual(report['added_unique_guards'],1)
        _,report=triage(a,a,[r,{}],raw,va)
        self.assertEqual(report['unresolved_classification'],{'raw_span_unreconciled':1})
        # A direct transfer whose destination is interior to another printed row.
        raw=bytes.fromhex('eb01906690c3'); a=[Instruction(va,'jmp','0x103'),Instruction(va+2,'nop',''),Instruction(va+3,'xchg','ax,ax'),Instruction(va+5,'ret','')]
        # Separate synthetic linear rows deliberately hide byte 0x103.
        b=[a[0],Instruction(va+2,'nop',''),Instruction(va+5,'ret','')]
        r=parse_raw('100: eb 01 \tjmp 0x103\n102: 90 66 90 \tnop\n105: c3 \tret',raw,va)
        _,report=triage(b,b,[r,r],raw,va)
        self.assertEqual(report['prior_boundary_conflicts'],{'interior/interior':1})

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE toolchain')
    def test_owned_terminal_and_indirect(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 nop
 callq *%r8
 callq *8(%rsp)
 loop entry
 jmp entry
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe');s=pe.section('.text');va=pe.image_base+s.rva;raw=pe.at_rva(s.rva,s.virtual_size,executable=True)
            l,r=[disassemble(pe,s.rva,s.virtual_size,t) for t in ('objdump','llvm-objdump')]
            maps=[raw_decode(pe,s.rva,s.virtual_size,t) for t in ('objdump','llvm-objdump')]
            guards,report=triage(l,r,maps,raw,va)
            self.assertEqual(report['baseline'],{'unresolved':4})
            self.assertEqual(report['unresolved_classification'],{'indirect_register':1,'indirect_memory':1,'direct_byte_verified':2})
            self.assertEqual(report['recovered_direct'],{'common_boundary':2})
            self.assertEqual(guards,{va})
            self.assertEqual(report['added_unique_guards'],1)
            with self.assertRaises(ValueError): raw_decode(pe,s.rva,s.virtual_size,'bad')
            with self.assertRaises(ValueError): raw_decode(pe,s.rva,32769,'objdump')
