import re, shutil, subprocess, tempfile, unittest
from pathlib import Path
from skell_vst_decompiler.indirect_address_evidence import verify_indirect_memory, decode_address

class IndirectAddressEvidenceTests(unittest.TestCase):
    def test_known_forms_and_mutations(self):
        cases=[('ff542408','call','rsp+8','rsp+9'),('41ff55f8','call','r13-8','r13+8'),
               ('42ff54a020','call','rax+4*r12+32','rax+4*rsp+32'),
               ('43ff24c8','jmp','r8+r9*8','r8+r9*4'),('ff1510000000','call','rip+16','rax+16'),
               ('ff242578563412','jmp','0x12345678','0x12345679'),
               ('ff148d78563412','call','rcx*4+0x12345678','rcx*8+0x12345678'),
               ('ff10','call','rax','rbx')]
        for raw,mnemonic,good,bad in cases:
            data=bytes.fromhex(raw)
            with self.subTest(raw=raw):
                self.assertTrue(verify_indirect_memory(data,mnemonic,f'QWORD PTR [{good}]'))
                self.assertFalse(verify_indirect_memory(data,mnemonic,f'QWORD PTR [{bad}]'))
                self.assertFalse(verify_indirect_memory(data,mnemonic,f'DWORD PTR [{good}]'))
                self.assertFalse(verify_indirect_memory(data,'jmp' if mnemonic=='call' else 'call',f'QWORD PTR [{good}]'))
                self.assertFalse(verify_indirect_memory(data+b'\x90',mnemonic,f'QWORD PTR [{good}]'))
        self.assertTrue(verify_indirect_memory(bytes.fromhex('ff242578563412'),'jmp','QWORD PTR ds:0x12345678'))
    def test_conservative_exclusions(self):
        for raw in ('','ff','67ff10','64ff10','66ff10','ff18','ffd0','4040ff10','ff5424'):
            self.assertIsNone(decode_address(bytes.fromhex(raw),'call'))
        for s in ('qword ptr [rax]+1','qword ptr [rax+-1]','qword ptr [eax]','qword ptr [rax-rax]','qword ptr [rax*3]','qword ptr [rax] junk'):
            self.assertFalse(verify_indirect_memory(bytes.fromhex('ff10'),'call',s))
    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')),'requires owned PE toolchain')
    def test_owned_dual_decoder_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'f.s').write_text('''.text
.globl entry
entry:
 callq *8(%rsp)
 callq *-8(%r13)
 callq *32(%rax,%r12,4)
 jmpq *(%r8,%r9,8)
 callq *16(%rip)
 jmpq *0x12345678
 callq *0x12345678(,%rcx,4)
 callq *(%rax)
 callq *%r8
 retq
''')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            for tool in ('objdump','llvm-objdump'):
                args=[tool,'-d','-M','intel'];args+=['--insn-width=15'] if tool=='objdump' else []
                out=subprocess.check_output(args+[str(p/'f.exe')],text=True);count=0
                for line in out.splitlines():
                    m=re.match(r'^\s*[0-9a-f]+:\s+((?:[0-9a-f]{2} +)+)\s*(call|jmp)\s+(.+)$',line,re.I)
                    if not m or 'ptr' not in m[3].lower(): continue
                    self.assertTrue(verify_indirect_memory(bytes.fromhex(m[1]),m[2],m[3]),line);count+=1
                self.assertEqual(count,8,tool)

    @unittest.skipUnless(all(shutil.which(t) for t in ('clang','lld-link','objdump','llvm-objdump')),'requires owned PE toolchain')
    def test_generated_address_matrix(self):
        regs=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi')+tuple(f'r{i}' for i in range(8,16))
        forms=[]
        for base in regs:
            for index in ('rax','r9','r12'):
                for scale in (1,2,4,8):
                    for displacement in (-129,-1,0,127,128):
                        forms.append(f'callq *{displacement}(%{base},%{index},{scale})')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'f.s').write_text('.text\n.globl entry\nentry:\n '+'\n '.join(forms)+'\n retq\n')
            subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(p/'f.s'),'-o',str(p/'f.obj')],check=True)
            subprocess.run(['lld-link','/entry:entry','/subsystem:console','/nodefaultlib',f'/out:{p/"f.exe"}',str(p/'f.obj')],check=True)
            for tool in ('objdump','llvm-objdump'):
                args=[tool,'-d','-M','intel'];args+=['--insn-width=15'] if tool=='objdump' else []
                out=subprocess.check_output(args+[str(p/'f.exe')],text=True);count=0
                for line in out.splitlines():
                    m=re.match(r'^\s*[0-9a-f]+:\s+((?:[0-9a-f]{2} +)+)\s*(call)\s+(.+)$',line,re.I)
                    if not m: continue
                    data=bytes.fromhex(m[1]);self.assertTrue(verify_indirect_memory(data,m[2],m[3]),line)
                    # Append a nonzero displacement to the printed address, without changing bytes.
                    mutant=m[3].replace(']','+1]',1)
                    self.assertNotEqual(mutant,m[3]);self.assertFalse(verify_indirect_memory(data,m[2],mutant),line);count+=1
                self.assertEqual(count,len(forms),tool)
