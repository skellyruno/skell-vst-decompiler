import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.rip_float_audit import decode_reference, audit_scope


class RipFloatAuditTests(unittest.TestCase):
    def test_decode(self):
        self.assertEqual(decode_reference(bytes.fromhex('f30f1005fcffffff'),0x100),('movss',4,0x104,'read'))
        self.assertEqual(decode_reference(bytes.fromhex('f2440f110508000000'),0x100),('movsd',8,0x111,'write'))
        for bad in ('f30f10','f30f1004fcffffff','f30f1005fcffffff00','f30f7005fcffffff'):
            self.assertIsNone(decode_reference(bytes.fromhex(bad),0x100))

    @unittest.skipUnless(all(shutil.which(x) for x in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE compiler and decoders')
    def test_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 movss constant(%rip), %xmm0
 mulss constant(%rip), %xmm0
 movsd %xmm1, state(%rip)
 movsd state(%rip), %xmm1
 retq
.section .rdata,"dr"
constant: .float 1.0
.data
state: .double 0.0
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); s=pe.section('.text')
            result=audit_scope(pe,pe.sha256,s.rva,s.virtual_size)
            self.assertEqual(result['counts'],{'read_readonly':2,'write_writable':1,'read_writable':1})
            self.assertEqual(result['rejected'],0)
            with self.assertRaises(PEFormatError): audit_scope(pe,'0'*64,s.rva,s.virtual_size)
            with self.assertRaises(ValueError): audit_scope(pe,pe.sha256,s.rva,32769)
            self.assertFalse(audit_scope(pe,pe.sha256,s.rva+s.virtual_size-1,1)['references'])
