import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from skell_vst_decompiler.pe import PE
from skell_vst_decompiler.navigation import runtime_ranges
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.unwind_index import chain_index, direct_edges, redundant_rex_agreement


@unittest.skipUnless(all(shutil.which(t) for t in ('clang', 'lld-link', 'objdump', 'llvm-objdump')), 'PE fixture tools required')
class UnwindIndexTests(unittest.TestCase):
    def test_owned_chain_and_edges(self):
        asm = '''.text
.globl probe
probe:
  .byte 0x40,0x55
  call child
  jmp child
primary_end:
child:
  .byte 0x48,0xff,0xa0,0xd0,0x01,0,0
child_end:
.section .xdata,"dr"
.p2align 2
primary_info:
  .byte 1, 0, 0, 0
child_info:
  .byte 33, 0, 0, 0
  .rva probe, primary_end, primary_info
.section .pdata,"dr"
  .rva probe, primary_end, primary_info
  .rva child, child_end, child_info
'''
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / 'probe.s').write_text(asm)
            subprocess.run(['clang', '--target=x86_64-pc-windows-msvc', '-c', str(d / 'probe.s'), '-o', str(d / 'probe.obj')], check=True)
            subprocess.run(['lld-link', '/dll', '/noentry', '/nodefaultlib', '/export:probe', '/out:' + str(d / 'probe.dll'), str(d / 'probe.obj')], check=True)
            pe = PE(d / 'probe.dll')
            rows = runtime_ranges(pe)
            root, end, _ = rows[0]
            child, child_end, _ = rows[1]
            census, roots = chain_index(pe)
            self.assertEqual(census['resolved_chain_edges'], 1)
            self.assertEqual(census['records_in_multi_range_families'], 2)
            self.assertEqual(roots, {root: root, child: root})
            edge = direct_edges(pe, root, end - root, roots)
            self.assertEqual([(x['op'], x['target'], x['family_root']) for x in edge['direct_edges']], [('call', hex(child), hex(root)), ('jmp', hex(child), hex(root))])
            address = pe.image_base + root
            a = Instruction(address, 'rex', 'push rbp')
            self.assertTrue(redundant_rex_agreement(pe, a, Instruction(address, 'push', 'rbp')))
            self.assertFalse(redundant_rex_agreement(pe, a, Instruction(address, 'push', 'rbx')))
            address = pe.image_base + child
            a = Instruction(address, 'rex.', 'W jmp QWORD PTR [rax+0x1d0]')
            self.assertTrue(redundant_rex_agreement(pe, a, Instruction(address, 'jmp', 'qword ptr [rax + 0x1d0]')))
            self.assertFalse(redundant_rex_agreement(pe, a, Instruction(address, 'jmp', 'qword ptr [rax + 0x1d8]')))
            self.assertEqual(direct_edges(pe, child, child_end - child, roots)['indirect_sites'], 1)
