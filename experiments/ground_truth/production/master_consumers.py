"""Source-known Master: bounded downstream operand checkpoints, not a full CFG proof."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from skell_vst_decompiler.disasm import parse_disassembly
EXPECTED='82edf9789d1f2632f6f707ee9739f9d1e54f9e5e0781d829a9016ddc513876c3'
# Source checkout 7a6b512: MasteringEngine::processFrame.
CHECKS=((0x13a6ac,'movsd','qwordptr[r14+0x80],xmm0'),
        (0x13a70a,'movsd','qwordptr[r14+0x98],xmm2'),
        (0x13aad4,'movsd','qwordptr[rsp+0xe0],xmm1'),
        (0x13aadd,'movsd','qwordptr[r14+0x140],xmm1'),
        (0x13ac9a,'movsd','xmm5,qwordptr[rsp+0x48]'),
        (0x13aca9,'mulsd','xmm5,xmm0'),
        (0x13acba,'mulsd','xmm0,qwordptr[rsp]'),
        (0x13acc8,'movsd','qwordptr[rsp+0x60],xmm5'),
        (0x13acce,'movsd','qwordptr[rsp+0x18],xmm0'),
        (0x13ad07,'comisd','xmm2,xmm4'),
        (0x13ad17,'movsd','xmm3,qwordptr[rsp+0x60]'),
        (0x13ad1d,'movsd','xmm0,qwordptr[rsp+0x18]'),
        (0x13ad2d,'maxsd','xmm3,xmm0'),
        (0x13c8a7,'movsd','xmm6,qwordptr[rsp+0xe0]'),
        (0x13c8c2,'mulsd','xmm2,xmm6'),
        (0x13c8c6,'mulsd','xmm6,xmm5'))

def verify(path,tool):
    path=Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Wrong owned artifact')
    if tool not in ('objdump','llvm-objdump'):raise ValueError('Unknown decoder')
    cmd=[tool,'-d','--no-show-raw-insn','--start-address=0x13a610','--stop-address=0x14041d']+(['-M','intel'] if tool=='objdump' else ['--x86-asm-syntax=intel'])+[str(path)]
    by={i.address:i for i in parse_disassembly(subprocess.check_output(cmd,text=True,timeout=30))}
    for va,op,arg in CHECKS:
        i=by[va];actual=re.sub(r'\s+','',i.operands.split('#')[0].lower())
        if (i.mnemonic,actual)!=(op,arg):raise ValueError(f'Consumer checkpoint mismatch {va:#x}: {i}')
    return {'module_sha256':EXPECTED,'checkpoint_count':len(CHECKS),'source_ids':['input','drive','output'],
            'sites':[hex(x[0]) for x in CHECKS],
            'limits':'Source-known local consumer endpoints; not a general or complete reaching-definition proof. Drive branch and stereo peak computation are observed, complete nonlinear mapping remains open.'}
if __name__=='__main__':
    a=verify(sys.argv[1],'objdump');b=verify(sys.argv[1],'llvm-objdump');assert a==b;print(json.dumps(a,indent=2))
