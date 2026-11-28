"""Bounded local SSE value-flow evidence, not runtime or algorithm recovery."""
import hashlib
import re
from collections import Counter
from .disasm import disassemble
from .memory_effects import FORMS, PREFIX, decode_memory, operand_matches, address_class
from .pe import PEFormatError
from .scope_consensus import reconcile
from .flow_guards import transparent

MOVES = {'movss','movsd','movups','movupd','movaps','movapd'}
BINARY = {0x58,0x59,0x5c,0x5d,0x5e,0x5f}


def decode_register(raw):
    if not raw:
        return None
    i=0; p=0; rex=0
    if raw[i] in (0x66,0xf2,0xf3): p=raw[i]; i+=1
    if i<len(raw) and 0x40<=raw[i]<=0x4f: rex=raw[i]; i+=1
    if len(raw)!=i+3 or raw[i]!=0x0f or raw[i+2]>>6!=3:
        return None
    op,mr=raw[i+1:i+3]
    if op not in BINARY | {0x10,0x11,0x28,0x29,0x51}:
        return None
    if op in (0x28,0x29) and p not in (0,0x66):
        return None
    suffix,width=PREFIX[p]
    dst=((mr>>3)&7)+8*bool(rex&4); src=(mr&7)+8*bool(rex&1)
    if op in (0x11,0x29): dst,src=src,dst
    name=('movu'+suffix if op in (0x10,0x11) and p in (0,0x66) else
          'mova'+suffix if op in (0x28,0x29) else FORMS[op]+suffix)
    return name,width,dst,src


def scan(left,right,raw,va,*,limit=16,entries=(),allow_transparent=False):
    """Count contiguous selected value paths, stopping at every unknown op.

    Tracks only the named scalar lane or complete named packed precision.
    General registers cannot change inside supported instructions. This is
    syntactic possible dependence, not numerical dependence or reachability.
    A memory store is a barrier after its own classification (alias unknown).
    Optional observed entry boundaries clear origins. The transparent mode
    accepts only byte-checked NOP and register-only CMP/TEST. Neither mode
    establishes complete control flow.
    """
    if type(limit) is not int or not 3<=limit<=64:
        raise ValueError('Flow limit must be 3..64')
    entries = set(entries)
    if any(type(x) is not int or not va<=x<va+len(raw) for x in entries):
        raise ValueError("Invalid flow entry boundary")
    reconcile(left,right,va,va+len(raw))  # reject duplicate/unordered addresses
    streams=[[x for x in s if va<=x.address<va+len(raw)] for s in (left,right)]
    maps=[{x.address:(x,y.address) for x,y in zip(s,s[1:])} for s in streams]
    state={}; prev=None; counts=Counter(); depths=Counter(); source_counts=Counter()
    # value = (precision suffix, { (effective-address syntax, load ordinal): depth }).
    # Age each origin independently instead of chopping an arbitrary fixed block.
    for ordinal,site in enumerate(sorted(maps[0].keys() | maps[1].keys())):
        if site!=prev or site in entries:
            state.clear()
        prev=None
        if site not in maps[0] or site not in maps[1]:
            state.clear(); continue
        a,end=maps[0][site]; b,end2=maps[1][site]
        if end!=end2 or not 1<=end-site<=15:
            state.clear(); continue
        chunk=raw[site-va:end-va]
        if allow_transparent and transparent(chunk,a,b):
            prev=end
            continue
        d=decode_memory(chunk); reg=None
        if d is not None:
            if not operand_matches(a,d) or not operand_matches(b,d):
                state.clear(); continue
            op,access,width,dst,base,index,scale,disp=d
            address=(base,index,scale,disp,width) if address_class(base,index)=='general_register' else None
        else:
            reg=decode_register(chunk)
            if reg is None:
                state.clear(); continue
            op,width,dst,src=reg
            args='xmm%d,xmm%d'%(dst,src)
            if any(x.mnemonic!=op or re.sub(r'\s+','',x.operands.split('#',1)[0].lower())!=args for x in (a,b)):
                state.clear(); continue
        precision=op[-2:]
        def get(r):
            v=state.get(r)
            return {k:n for k,n in v[1].items() if ordinal-k[1]<limit} if v and v[0]==precision else {}
        old=get(dst)
        incoming=get(src) if reg else ({(address,ordinal):0} if address is not None else {})
        if d is not None and access=='write':
            transformed={k:n for k,n in old.items() if n>0}
            if address is not None and transformed:
                relation='same_expression' if any(k[0]==address for k in transformed) else 'different_expression'
                counts[relation]+=1
                depths[str(max(transformed.values()))]+=1
                source_counts[str(len({k[0] for k in transformed}))]+=1
            state.clear(); continue
        if op in MOVES:
            origins=incoming
        elif op.startswith('sqrt'):
            origins={k:n+1 for k,n in incoming.items()}
        elif reg and src==dst and op.startswith(('sub','div')):
            # Self subtraction/division can erase numeric dependence. Discard.
            origins={}
        else:
            origins={k:max(old.get(k,-1),incoming.get(k,-1))+1 for k in old.keys()|incoming.keys()}
        if origins:
            state[dst]=(precision,origins)
        else:
            state.pop(dst,None)
        prev=end
    return {'paths':dict(counts),'arithmetic_depths':dict(depths),
            'source_expression_counts':dict(source_counts),'total':sum(counts.values())}


def audit_scope(pe,fingerprint,start,length,*,limit=16):
    if pe.sha256!=fingerprint:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1<=length<=32768:
        raise ValueError('Invalid bounded scope')
    raw=pe.at_rva(start,length,executable=True); va=pe.image_base+start
    a,b=[disassemble(pe,start,length,t) for t in ('objdump','llvm-objdump')]
    result=scan(a,b,raw,va,limit=limit)
    result.update(start=hex(start),bytes=length,scope_sha256=hashlib.sha256(raw).hexdigest(),limit=limit,
                  limits='Contiguous selected SSE forms only; possible local syntactic value dependence, not runtime address identity, audio processing or numerical equivalence.')
    return result
