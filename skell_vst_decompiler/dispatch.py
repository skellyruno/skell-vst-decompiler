"""Bounded static indexed jump-table inspection, never chooses a runtime target."""
import re
import struct
from .disasm import disassemble
from .pe import PEFormatError

def trace_dispatch(pe, rva, entries=4, objdump='objdump'):
    if not isinstance(entries,int) or not 1<=entries<=32:
        raise ValueError('Inspect 1..32 candidate slots; not the inferred table length')
    ins=disassemble(pe,rva,32,objdump)
    if len(ins)<3: raise ValueError('Missing dispatcher instructions')
    a,b,c=ins[:3]
    if (a.mnemonic,b.mnemonic,c.mnemonic)!=('movsxd','lea','jmp') or not a.operands.startswith('rax,DWORD PTR [rip') or not b.operands.startswith('r11,[rip') or c.operands!='QWORD PTR [r11+rax*8]':
        raise ValueError('Unsupported indexed dispatch pattern')
    def rip(i):
        m=re.search(r'#\s*0x([0-9a-fA-F]+)',i.operands)
        if not m: raise ValueError('No RIP target')
        return int(m.group(1),16)-pe.image_base
    selector,table=rip(a),rip(b)
    targets=[]
    for j in range(entries):
        va=struct.unpack('<Q',pe.at_rva(table+8*j,8))[0]
        target=va-pe.image_base
        try: pe.at_rva(target,1,executable=True); executable=True
        except PEFormatError: executable=False
        targets.append({'slot':j,'target_rva':hex(target) if executable else None,'executable_file_backed':executable})
    try: pe.at_rva(selector,4); selector_backed=True
    except PEFormatError: selector_backed=False
    return {'binary_sha256':pe.sha256,'source':pe.path.name,'dispatcher_rva':hex(rva),'selector_rva':hex(selector),'selector_file_backed':selector_backed,'table_rva':hex(table),'sampled_slots':targets,'status':'static candidate targets only; table extent, runtime choice and DSP semantics unverified'}
