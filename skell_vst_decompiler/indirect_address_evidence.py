"""Strict operand evidence for ordinary x64 indirect memory call/jump forms.
No target resolution, pointer dereference, or inference of runtime audio role.
"""
from dataclasses import dataclass
import re

_REGS = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi') + tuple(f'r{i}' for i in range(8,16))
_NUM = r'(?:0x[0-9a-f]+|[0-9]+)'
_REG = r'(?:' + '|'.join((*_REGS,'rip')) + r')'

@dataclass(frozen=True)
class AddressEvidence:
    terms: tuple
    displacement: int


def decode_address(raw, mnemonic):
    """Return symbolic effective address for unprefixed/one-REX FF /2,/4 only."""
    if not isinstance(raw, bytes) or not 2 <= len(raw) <= 8:
        return None
    rex = raw[0] if 0x40 <= raw[0] <= 0x4f else 0
    i = int(bool(rex))
    if raw[i] != 0xff or len(raw) < i+2:
        return None
    mr = raw[i+1]; mod = mr >> 6; op = (mr >> 3) & 7; rm = mr & 7
    if mod == 3 or (op,mnemonic) not in ((2,'call'),(4,'jmp')):
        return None
    i += 2; terms = {}; disp_bytes = (0,1,4)[mod]
    def add(reg, scale):
        terms[reg] = terms.get(reg,0) + scale
    if rm == 4:
        if i >= len(raw): return None
        sib = raw[i]; i += 1; idx = (sib >> 3) & 7; base = sib & 7
        if idx != 4 or rex & 2: add(_REGS[idx+8*bool(rex&2)],1 << (sib >> 6))
        if mod == 0 and base == 5: disp_bytes = 4
        else: add(_REGS[base+8*bool(rex&1)],1)
    elif mod == 0 and rm == 5:
        add('rip',1); disp_bytes = 4
    else:
        add(_REGS[rm+8*bool(rex&1)],1)
    if len(raw) != i+disp_bytes: return None
    disp = int.from_bytes(raw[i:],'little',signed=True) if disp_bytes else 0
    return AddressEvidence(tuple(sorted(terms.items())),disp)


def parse_operand(operand):
    """Normalize bounded Intel syntax from GNU/LLVM; refuse unknown forms."""
    if not isinstance(operand,str) or len(operand)>256: return None
    s = operand.split('#',1)[0].strip().lower()
    m = re.fullmatch(r'qword\s+ptr\s+\[([^\[\]]+)\]',s)
    if m: expr = re.sub(r'\s+','',m[1])
    else:
        m = re.fullmatch(r'qword\s+ptr\s+ds:('+_NUM+r')',s)
        if not m: return None
        expr = m[1]
    if not expr: return None
    terms = {}; disp = 0
    if expr[0] not in '+-': expr = '+'+expr
    chunks = re.findall(r'([+-])([^+-]+)',expr)
    if ''.join(s+t for s,t in chunks)!=expr or len(chunks)>4: return None
    for sign,term in chunks:
        if re.fullmatch(_NUM,term):
            value = int(term,16 if term.startswith('0x') else 10)
            disp += value if sign=='+' else -value
            continue
        if sign!='+': return None
        scale=1; reg=term
        m=re.fullmatch('('+_REG+r')\*([1248])',term)
        if m: reg,scale=m[1],int(m[2])
        else:
            m=re.fullmatch(r'([1248])\*('+_REG+')',term)
            if m: reg,scale=m[2],int(m[1])
        if reg not in (*_REGS,'rip') or (reg=='rip' and scale!=1): return None
        terms[reg]=terms.get(reg,0)+scale
    return AddressEvidence(tuple(sorted(terms.items())),disp)


def verify_indirect_memory(raw,mnemonic,operand):
    expected=decode_address(raw,mnemonic)
    return expected is not None and expected==parse_operand(operand)
