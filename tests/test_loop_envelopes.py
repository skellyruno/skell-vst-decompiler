import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.loop_envelopes import direct_backedge, audit_envelopes


class EnvelopeTests(unittest.TestCase):
    def test_encodings(self):
        self.assertEqual(direct_backedge(bytes.fromhex('75fc'),0x100,'jnz'),0xfe)
        self.assertEqual(direct_backedge(bytes.fromhex('0f85f0ffffff'),0x100,'jne'),0xf6)
        for raw,op in [('7502','jne'),('75fc','je'),('0f85f0ffff','jne'),('ebfc','jne')]:
            self.assertIsNone(direct_backedge(bytes.fromhex(raw),0x100,op))

    @unittest.skipUnless(all(shutil.which(x) for x in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE toolchain')
    def test_owned_nested_loops(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 movl $2, %ecx
outer:
 movl $3, %eax
inner:
 decl %eax
 jne inner
 decl %ecx
 jne outer
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); s=pe.section('.text')
            rows=audit_envelopes(pe,pe.sha256,s.rva,s.virtual_size)['envelopes']
            self.assertEqual(len(rows),2)
            self.assertLess(int(rows[1]['head'],16),int(rows[0]['head'],16))
            self.assertGreater(rows[1]['sites'],rows[0]['sites'])
            with self.assertRaises(PEFormatError): audit_envelopes(pe,'0'*64,s.rva,s.virtual_size)
            with self.assertRaises(ValueError): audit_envelopes(pe,pe.sha256,s.rva,32769)
            self.assertFalse(audit_envelopes(pe,pe.sha256,s.rva+s.virtual_size-1,1)['envelopes'])
