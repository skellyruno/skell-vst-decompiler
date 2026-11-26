import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.disasm import Instruction
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.scope_consensus import family, reconcile, audit_scope


class ConsensusTests(unittest.TestCase):
    def test_families(self):
        for m,k in [('mulss','scalar32'),('divsd','scalar64'),('vfmadd231ps','packed32'),('sqrtpd','packed64'),('fmulp','x87'),('movss',None),('paddd',None),('call',None)]:
            self.assertEqual(family(m),k)

    def test_malformed_and_differences(self):
        a=[Instruction(x,m,'') for x,m in [(10,'mulss'),(14,'addsd'),(18,'sqrtps'),(22,'ret')]]
        b=[Instruction(x,m,'') for x,m in [(10,'mulss'),(14,'subsd'),(18,'sqrtps'),(23,'ret')]]
        r,s=reconcile(a,b,10,24)
        self.assertEqual(s,[10]); self.assertEqual(r['counts']['span_disagreement'],1)
        self.assertEqual(r['counts']['mnemonic_disagreement'],1)
        self.assertEqual(r['counts']['one_decoder_only'],2)
        with self.assertRaises(ValueError): reconcile(a+a,b,10,24)
        r,s=reconcile(a,a,10,24)
        self.assertEqual(s,[10,14,18]); self.assertEqual(r['counts']['terminal_unbounded'],1)
        r,s=reconcile(a[:-1],a[:-1],10,24)
        self.assertEqual(s,[10,14]); self.assertEqual(r['excluded_fp_by_decoder'],{'left':1,'right':1})

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE toolchain')
    def test_owned_pe(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 mulss %xmm1, %xmm0
 addsd %xmm1, %xmm0
 sqrtps %xmm1, %xmm0
 addpd %xmm1, %xmm0
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); s=pe.section('.text')
            r=audit_scope(pe,pe.sha256,s.rva,s.virtual_size)
            self.assertEqual(r['fp_families'],{'scalar32':1,'scalar64':1,'packed32':1,'packed64':1})
            self.assertEqual(r['counts']['terminal_unbounded'],1)
            with self.assertRaises(PEFormatError): audit_scope(pe,'0'*64,s.rva,s.virtual_size)
            with self.assertRaises(ValueError): audit_scope(pe,pe.sha256,s.rva,32769)
