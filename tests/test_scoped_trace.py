import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.navigation import runtime_ranges
from skell_vst_decompiler.scoped_trace import unwind_family, checkpoint_report


@unittest.skipUnless(all(shutil.which(t) for t in ('clang', 'lld-link', 'objdump', 'llvm-objdump')), 'PE fixture tools required')
class ScopedTraceTests(unittest.TestCase):
    def test_owned_chained_ranges(self):
        asm = '''.text
.globl probe
probe:
  nop
  ret
primary_end:
child:
  xor %eax, %eax
  ret
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
            self.assertEqual(len(rows), 2)
            root, end, _ = rows[0]
            child, child_end, _ = rows[1]
            family = unwind_family(pe, root)
            self.assertEqual(len(family), 2)
            self.assertEqual(family[1]['parent'], hex(root))
            report = checkpoint_report(pe, pe.sha256, [(root, child_end - root, [root, child])])
            self.assertEqual(report['scopes'][0]['verified_sites'], [hex(root), hex(child)])
            with self.assertRaises(PEFormatError):
                checkpoint_report(pe, '0' * 64, [(root, end - root, [root])])
            with self.assertRaises(ValueError):
                checkpoint_report(pe, pe.sha256, [(root, end - root, [end])])
