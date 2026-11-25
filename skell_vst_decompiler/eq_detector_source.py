"""Verify the exact-build TVB detector scratch-buffer producer and consumer."""
import hashlib
import re
from .disasm import disassemble

SOURCE='cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9'
REGIONS=((0x34ed50,0x34f149),(0x351700,0x35176b),(0x35acf8,0x35ad8d),(0x35b71f,0x35bd80))
CHECKS=(
    (0x34ed8a,'xor','r14d,r14d'),
    (0x34f0fa,'mov','qwordptr[rdi+0x1a038],r14'),
    (0x351731,'lea','rcx,[rdi+0x1a038]'),
    (0x351738,'call','0x180039d00'),
    (0x35acf8,'movsxd','rdx,dwordptr[r14+0x8]'),
    (0x35acfc,'lea','rcx,[rsi+0x1a038]'),
    (0x35ad08,'call','0x180087260'),
    (0x35ba2b,'xorps','xmm6,xmm6'),
    (0x35ba5a,'mov','rbx,qwordptr[rdi+0x1a038]'),
    (0x35ba61,'movd','xmm1,r14d'),
    (0x35ba66,'cvtdq2ps','xmm1,xmm1'),
    (0x35ba70,'movaps','xmm0,xmm6'),
    (0x35ba7d,'mov','r9,qwordptr[r15+0x10]'),
    (0x35ba99,'mov','rax,qwordptr[r9+rcx*8]'),
    (0x35ba9d,'addss','xmm0,dwordptr[rax+r8*4]'),
    (0x35baa8,'addss','xmm0,dwordptr[rax+r8*4]'),
    (0x35bab3,'addss','xmm0,dwordptr[rax+r8*4]'),
    (0x35babe,'addss','xmm0,dwordptr[rax+r8*4]'),
    (0x35bb45,'mov','r9,qwordptr[r15+0x10]'),
    (0x35bb54,'addss','xmm0,dwordptr[rcx+r8*4]'),
    (0x35bb5f,'divss','xmm0,xmm1'),
    (0x35bb66,'movss','dwordptr[rbx+r8*4],xmm0'),
    (0x35bba0,'mov','ecx,0x20'),
    (0x35bbaf,'cmovl','ecx,eax'),
    (0x35bbb2,'mov','rax,qwordptr[rdi+0x1a038]'),
    (0x35bbc0,'mov','r9d,ecx'),
    (0x35bbc9,'lea','rdx,[rax+rdx*4]'),
    (0x35bbcd,'call','0x1805a5090'),
)


def verify(pe, tool='objdump'):
    if pe.sha256!=SOURCE:raise ValueError('Unexpected exact TVB fingerprint')
    if tool not in ('objdump','llvm-objdump'):raise ValueError('Unsupported decoder')
    by={};regions=[]
    for lo,hi in REGIONS:
        for i in disassemble(pe,lo,hi-lo,tool):
            arg=i.operands.split('#',1)[0].split('<',1)[0].lower().replace(' ','').replace('\t','')
            arg=re.sub(r"([1248])\*(r[a-z0-9]+)",r"\2*\1",arg)
            by[i.address-pe.image_base]=(i.mnemonic,arg)
        regions.append({'start_rva':hex(lo),'end_rva_exclusive':hex(hi),'region_sha256':hashlib.sha256(pe.at_rva(lo,hi-lo,executable=True)).hexdigest()})
    for addr,op,args in CHECKS:
        if by.get(addr)!=(op,args):raise ValueError(f'Instruction endpoint mismatch at {addr:#x}: {by.get(addr)}')
    return {'binary_sha256':pe.sha256,'checkpoint_count':len(CHECKS),'regions':regions,
            'finding':'For positive channel count, the selected path sums channel samples from the current buffer and divides by channel count, writes a mono scratch buffer, then passes an offset into it to the dynamic EQ detector with a maximum 32-sample chunk.',
            'limits':'Static local endpoints only. Origin of incoming buffer, zero-channel path, runtime dispatch and actual detector response are not established.'}
