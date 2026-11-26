import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.branch_evidence import conditional_target, audit_branches


class BranchEvidenceTests(unittest.TestCase):
    def test_byte_forms(self):
        self.assertEqual(conditional_target(bytes.fromhex('75fc'), 0x100, 'jnz'), 0xfe)
        self.assertEqual(conditional_target(bytes.fromhex('0f8500010000'), 0x100, 'jne'), 0x206)
        self.assertIsNone(conditional_target(bytes.fromhex('75fc'), 0x100, 'je'))
        self.assertIsNone(conditional_target(bytes.fromhex('0f85000100'), 0x100, 'jne'))
        self.assertIsNone(conditional_target(bytes.fromhex('ebfc'), 0x100, 'jne'))
        self.assertIsNone(conditional_target(bytes.fromhex('6675fc'), 0x100, 'jne'))

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE compiler and both decoders')
    def test_owned_pe(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p/'fixture.s').write_text('''.text
.globl entry
entry:
 movl $3, %eax
loop:
 subl $1, %eax
 jne loop
 je faraway
 .space 160, 0x90
faraway:
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'fixture.s'),'-o',str(p/'fixture.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"fixture.exe"}',str(p/'fixture.obj')],check=True)
            pe = PE(p/'fixture.exe')
            s = pe.section('.text')
            result = audit_branches(pe,pe.sha256,s.rva,s.virtual_size)
            self.assertEqual([x['direction'] for x in result['conditional_edges']],['backward','forward'])
            self.assertEqual(result['rejected_sites'],0)
            self.assertEqual(result['conditional_edges'][0]['target'],hex(s.rva+5))
            self.assertEqual(result['conditional_edges'][1]['target'],hex(s.rva+s.virtual_size-1))
            with self.assertRaises(PEFormatError):
                audit_branches(pe,'0'*64,s.rva,s.virtual_size)
            with self.assertRaises(ValueError):
                audit_branches(pe,pe.sha256,s.rva,32769)
