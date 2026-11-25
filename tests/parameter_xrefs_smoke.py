"""Compile our own x64 PE fixture; check both readers against exact known endpoints."""
from pathlib import Path
import subprocess
import tempfile
from skell_vst_decompiler.parameter_xrefs import scan

ASM=r'''
.text
.globl probe
.def probe; .scl 2; .type 32; .endef
.seh_proc probe
probe:
 pushq %r14
 .seh_pushreg %r14
 subq $32,%rsp
 .seh_stackalloc 32
 .seh_endprologue
 movq %rcx,%r14
 leaq key(%rip),%rdx
 movq %rsp,%rcx
 callq string_stub
 movq (%rax),%rdx
 movq %r14,%rcx
 callq value_stub
 movl (%rax),%ecx
 movd %ecx,%xmm0
 addq $32,%rsp
 popq %r14
 retq
.seh_endproc
string_stub:
 movq %rdx,(%rcx)
 movq %rcx,%rax
 retq
value_stub:
 movq %rcx,%rax
 retq
.section .rdata,"dr"
key:
.asciz "ownedGain"
'''


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);source=root/'fixture.s';obj=root/'fixture.obj';dll=root/'fixture.dll'
        source.write_text(ASM)
        subprocess.run(['clang','--target=x86_64-pc-windows-msvc','-c',str(source),'-o',str(obj)],check=True,timeout=30)
        subprocess.run(['lld-link','/dll','/noentry','/nodefaultlib','/export:probe','/out:'+str(dll),str(obj)],check=True,timeout=30)
        report=scan(dll,['ownedGain'])
        assert report['decoder_disagreements']==0 and len(report['references'])==1
        assert len(report['scalar_reader_candidates'])==1
        row=report['scalar_reader_candidates'][0]
        assert row['reader_target_rva']=='0x1037' and row['scalar_load_rva']=='0x1023',report
        assert scan(dll,['absent'])['references']==[]
        print('Owned x64 PE parameter navigation and negative control passed with GNU and LLVM.')


if __name__=='__main__':main()
