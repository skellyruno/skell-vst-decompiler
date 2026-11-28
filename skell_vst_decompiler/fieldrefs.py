"""Bounded static operand index. No alias analysis or inferred execution."""
import re
from .disasm import disassemble

_REG = re.compile(r'^(?:r(?:ax|bx|cx|dx|si|di|sp|bp|[89]|1[0-5]))$')
_MEM = re.compile(r'\[([^\[\]]+)\]')
_READ = {'cmp','test','comiss','ucomiss','call','jmp','push'}
_MOVE = {'mov','movss','movsd','movaps','movups','movd','movq','movzx','movsx','movsxd','movdqa','movdqu','pop'}


def field_refs(ins, image_base, base, offset):
    """Match literal base+displacement operands only, including indexed forms.

    Reports syntactic access roles, not reaching definitions. The base register
    must be verified by the caller; aliases and register changes are not traced.
    """
    if not _REG.fullmatch(base) or not isinstance(offset,int) or abs(offset)>=2**31:
        raise ValueError('Expected x64 register and signed 32-bit displacement')
    out=[]
    for i in ins:
        operands=i.operands.split('#',1)[0].strip().split(',')
        for n,operand in enumerate(operands):
            m=_MEM.search(operand)
            if not m:continue
            address=m[1].replace(' ','')
            if not re.match(r'^'+base+r'(?:$|[+-])',address):continue
            tail=address[len(base):]
            # Only a trailing literal displacement; do not mistake an index scale for it.
            d=re.search(r'([+-])(0x[0-9a-f]+|[0-9]+)$',tail)
            disp=(1 if d[1]=='+' else -1)*int(d[2],0) if d else 0
            if disp!=offset:continue
            if i.mnemonic=='lea':role='address'
            elif n>0 or i.mnemonic in _READ:role='read'
            elif i.mnemonic in _MOVE:role='write'
            elif i.mnemonic in {'add','sub','inc','dec','and','or','xor','shl','shr','sar','addss','subss','mulss','divss'}:role='read-write'
            else:role='unknown'
            out.append({'site_rva':hex(i.address-image_base),'mnemonic':i.mnemonic,'operand_index':n,'access':role,'indexed':bool(re.search(r'\br(?:ax|bx|cx|dx|si|di|sp|bp|[89]|1[0-5])\b',tail))})
    return out


def field_report(pe,start,length,base,offset,objdump='objdump'):
    refs=field_refs(disassemble(pe,start,length,objdump),pe.image_base,base,offset)
    return {'binary_sha256':pe.sha256,'start_rva':hex(start),'scan_bytes':length,'base':base,'offset':hex(offset),'references':refs,'limits':'Literal operand index only; not a proof of object identity, aliasing, runtime reachability or read/write dataflow.'}
