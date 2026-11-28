import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from skell_vst_decompiler.pe import PE, PEFormatError
from skell_vst_decompiler.local_call_contracts import audit_scope


@unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')), 'requires PE compiler and two decoders')
class ContractTests(unittest.TestCase):
    def test_owned_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'f.s').write_text('''.text
.globl entry
entry:
 mulss (%rbx), %xmm1
 movq (%rcx), %rax
 callq *8(%rax)
 movss %xmm0, (%rbx)
 movq (%rcx), %rax
 mulss (%rbx), %xmm1
 callq *8(%rax)
 leaq 4(%rbx), %rax
 movss %xmm0, (%rbx)
 # Negative: unrelated output address.
 mulss (%rbx), %xmm1
 movq (%rcx), %rax
 callq *8(%rax)
 movss %xmm0, (%rsi)
 # Negative: wrong input register.
 mulss (%rbx), %xmm2
 movq (%rcx), %rax
 callq *8(%rax)
 movss %xmm0, (%rbx)
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            pe=PE(p/'f.exe'); s=pe.section('.text')
            result=audit_scope(pe,pe.sha256,s.rva,s.virtual_size)
            self.assertEqual(len(result['candidates']),2)
            self.assertEqual([x['table_byte_offset'] for x in result['candidates']],[8,8])
            self.assertEqual([len(x['sites']) for x in result['candidates']],[4,5])
            with self.assertRaises(PEFormatError): audit_scope(pe,'0'*64,s.rva,s.virtual_size)
            with self.assertRaises(ValueError): audit_scope(pe,pe.sha256,s.rva,32769)
            self.assertFalse(audit_scope(pe,pe.sha256,s.rva+s.virtual_size-1,1)['candidates'])
