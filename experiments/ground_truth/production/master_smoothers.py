"""Exact owned Skell Master source-known smoother endpoint verification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from skell_vst_decompiler.disasm import parse_disassembly

EXPECTED='82edf9789d1f2632f6f707ee9739f9d1e54f9e5e0781d829a9016ddc513876c3'
# Source checkout 7a6b512, MasteringEngine.h lines 32-46, 965-985, 1031-1041.
# ID, parameter struct offset, target field, setter read/store, process recurrence start.
ROWS=(('input',0x0,0x88,0x139e22,0x139e89,0x13a680),
      ('drive',0x8,0xa0,0x139e91,0x139ec5,0x13a6de),
      ('glue',0x10,0xb8,0x139ecd,0x139f31,0x13a72b),
      ('dynamics',0x18,0xd0,0x139ee8,0x139f3e,0x13a77d),
      ('lows',0x20,0xe8,0x139f39,0x139f5c,0x13a7cf),
      ('highs',0x28,0x100,0x139f64,0x139f7f,0x13a81e),
      ('sauce',0x30,0x118,0x139f87,0x139fa7,0x13a86d),
      ('transients',0x50,0x130,0x13a04d,0x13a068,0x13a8bc),
      ('output',0x58,0x148,0x13a070,0x13a0bf,0x13aaa8))


def inspect(path,tool):
    path=Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Wrong exact owned module')
    if tool not in ('objdump','llvm-objdump'):raise ValueError('Unsupported decoder')
    def read(lo,hi):
        cmd=[tool,'-d','--no-show-raw-insn',f'--start-address={lo:#x}',f'--stop-address={hi:#x}']+(['-M','intel'] if tool=='objdump' else ['--x86-asm-syntax=intel'])+[str(path)]
        return parse_disassembly(subprocess.check_output(cmd,text=True,timeout=30))
    def args(i):return i.operands.split('#',1)[0].lower().replace(' ','').replace('\t','')
    def match(i,op,pattern):return i.mnemonic==op and re.fullmatch(pattern,args(i)) is not None
    setter=read(0x139dd0,0x13a60c);frame=read(0x13a610,0x13ab2c+9)
    by={i.address:i for i in setter+frame}
    for va,want in ((0x139dd9,'rbp,rsi'),(0x139ddd,'rbx,rdi'),(0x13a624,'r14,rdi')):
        if not match(by[va],'mov',want):raise ValueError('Object argument anchor mismatch')
    rows=[]
    for name,field,target,read_site,store_site,start in ROWS:
        if not match(by[read_site],'movsd',rf'xmm\d+,qwordptr\[rbp(?:\+0x{field:x})?\]' if not field else rf'xmm\d+,qwordptr\[rbp\+0x{field:x}\]'):
            raise ValueError('Parameter struct read mismatch: '+name)
        if not match(by[store_site],'movsd',rf'qwordptr\[rbx\+0x{target:x}\],xmm\d+'):
            raise ValueError('Target store mismatch: '+name)
        window=[i for i in frame if start<=i.address<start+64]
        if len(window)<7:raise ValueError('Incomplete recurrence')
        current=target-8;coefficient=target+8
        # Exact register linkage: target load, current load, copy target, subtract
        # current, multiply coefficient, add current, write same current field.
        a=re.fullmatch(r'(xmm\d+),qwordptr\[r14\+0x'+f'{target:x}'+r'\]',args(window[0]))
        b=re.fullmatch(r'(xmm\d+),qwordptr\[r14\+0x'+f'{current:x}'+r'\]',args(window[1]))
        if not a or not b or window[0].mnemonic!='movsd' or window[1].mnemonic!='movsd':raise ValueError('Smoother loads mismatch')
        copy=re.fullmatch(r'(xmm\d+),'+a[1],args(window[2]))
        if not copy or window[2].mnemonic!='movapd':raise ValueError('Smoother copy mismatch')
        acc=copy[1];cur=b[1];ops=[('subsd',acc+','+cur),('mulsd',acc+rf',qwordptr\[r14\+0x{coefficient:x}\]'),('addsd',acc+','+cur),('movsd',rf'qwordptr\[r14\+0x{current:x}\],'+acc)]
        sequence=[];pos=3
        for op,pattern in ops:
            while pos<len(window) and not match(window[pos],op,pattern):
                # Only flag comparison and stack spill are allowed in this known span.
                if window[pos].mnemonic!='ucomisd' and not match(window[pos],'movsd',r'qwordptr\[rsp\+0x[0-9a-f]+\],'+acc):raise ValueError('Unexpected intervening instruction '+name)
                pos+=1
            if pos==len(window):raise ValueError('Missing recurrence step '+name)
            sequence.append(hex(window[pos].address));pos+=1
        rows.append({'source_id':name,'parameter_struct_offset':hex(field),'target_offset':hex(target),'current_offset':hex(current),'coefficient_offset':hex(coefficient),'setter_read':hex(read_site),'setter_store':hex(store_site),'recurrence_start':hex(start),'recurrence_steps':sequence})
    return {'module_sha256':EXPECTED,'rows':rows,'limits':'Source-known setter member endpoints and local register-linked smoother recurrence. Not all control-flow paths, coefficients, or downstream audio consumption.'}


if __name__=='__main__':
    a=inspect(sys.argv[1],'objdump');b=inspect(sys.argv[1],'llvm-objdump')
    if a!=b:raise ValueError('Decoder disagreement')
    print(json.dumps(a,indent=2))
