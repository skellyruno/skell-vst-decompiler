import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.precision_audit import audit_scope


@unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE compiler and both decoders')
class PrecisionAuditTests(unittest.TestCase):
    def test_owned_pe(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p/'fixture.s').write_text('''.text
.globl entry
entry:
 subq $8, %rsp
 stmxcsr (%rsp)
 orl $0x8040, %eax
 ldmxcsr (%rsp)
 addps %xmm1, %xmm0
 addpd %xmm1, %xmm0
 addss %xmm1, %xmm0
 addsd %xmm1, %xmm0
 callq leaf
 addq $8, %rsp
 retq
leaf:
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'fixture.s'),'-o',str(p/'fixture.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"fixture.exe"}',str(p/'fixture.obj')],check=True)
            pe = PE(p/'fixture.exe')
            section = pe.section('.text')
            result = audit_scope(pe,pe.sha256,section.rva,section.virtual_size)
            for name in ('stmxcsr','ldmxcsr','addps','addpd','addss','addsd','ftz_daz_mask_or'):
                self.assertEqual(result['counts'][name],1)
            self.assertEqual(len(result['direct_edges']),1)
            with self.assertRaises(PEFormatError):
                audit_scope(pe,'0'*64,section.rva,section.virtual_size)
            with self.assertRaises(ValueError):
                audit_scope(pe,pe.sha256,section.rva,32769)
            # No matching add instructions in a one-byte ret window.
            negative = audit_scope(pe,pe.sha256,section.rva+section.virtual_size-1,1)
            self.assertEqual(negative['selected_byte_backed_sites'],[])
            self.assertEqual(negative['direct_edges'],[])
