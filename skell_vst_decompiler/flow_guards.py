"""Bounded, independently verified direct-entry guards for local analysis.

These are observed entry points, not a complete control-flow graph. Targets
from outside the window and register-dependent transfers are not resolved.
"""
import re
from collections import Counter
from .scope_consensus import reconcile

_CC = ('o','no','b','ae','e','ne','be','a','s','ns','p','np','l','ge','le','g')
_ALIAS = {'c':'b','nae':'b','nb':'ae','nc':'ae','z':'e','nz':'ne','na':'be',
          'nbe':'a','pe':'p','po':'np','nge':'l','nl':'ge','ng':'le','nle':'g'}


def direct_target(raw, site, mnemonic):
    """Only ordinary unprefixed relative CALL/JMP/Jcc with complete bytes."""
    size = len(raw)
    if size == 2 and raw[0] == 0xeb and mnemonic == 'jmp':
        disp = raw[1:]
    elif size == 5 and raw[0] in (0xe8,0xe9) and mnemonic == ('call' if raw[0]==0xe8 else 'jmp'):
        disp = raw[1:]
    elif size == 2 and 0x70 <= raw[0] <= 0x7f and mnemonic.startswith('j') and _ALIAS.get(mnemonic[1:],mnemonic[1:]) == _CC[raw[0]-0x70]:
        disp = raw[1:]
    elif size == 6 and raw[0] == 0x0f and 0x80 <= raw[1] <= 0x8f and mnemonic.startswith('j') and _ALIAS.get(mnemonic[1:],mnemonic[1:]) == _CC[raw[1]-0x80]:
        disp = raw[2:]
    else:
        return None
    return site + size + int.from_bytes(disp,'little',signed=True)


def entry_guards(left,right,raw,va):
    """Reconcile observed direct transfers; report unresolved sites separately."""
    end = va+len(raw)
    reconcile(left,right,va,end)
    maps = [{x.address:(x,y.address) for x,y in zip(s,s[1:])}
            for stream in (left,right) for s in [[x for x in stream if va<=x.address<end]]]
    sites = [{x.address:x for x in stream if va<=x.address<end} for stream in (left,right)]
    entries = set(); counts = Counter()
    def transfer(x):
        return x is not None and (x.mnemonic in ('call','jmp') or x.mnemonic.startswith('j') or x.mnemonic.startswith('loop'))
    for site in sorted(sites[0].keys() | sites[1].keys()):
        a,b = (s.get(site) for s in sites)
        if not (transfer(a) or transfer(b)):
            continue
        if site not in maps[0] or site not in maps[1] or maps[0][site][1]!=maps[1][site][1]:
            counts['unresolved'] += 1; continue
        stop = maps[0][site][1]
        chunk=raw[site-va:stop-va]
        def agrees(i):
            m=re.match(r'^0x([0-9a-fA-F]+)(?:\s|$)',i.operands)
            target=direct_target(chunk,site,i.mnemonic)
            return target if target is not None and m and int(m[1],16)==target else None
        da,db=agrees(a),agrees(b)
        if da is None or da!=db:
            counts['unresolved']+=1; continue
        if not va<=da<end:
            counts['outside_window']+=1
        elif da not in sites[0] or da not in sites[1]:
            counts['in_window_noncommon_boundary']+=1
        else:
            counts['in_window_common_boundary']+=1
            entries.add(da)
    return entries,dict(counts)


def transparent(raw,a,b):
    """Recognize only single-byte NOP and register-only 32/64-bit CMP/TEST.

    They do not modify XMM registers or addressing GPRs. Flags may change;
    every control transfer is still a barrier. No memory operands accepted.
    """
    if raw==b'\x90':
        return all(x.mnemonic=='nop' and not x.operands for x in (a,b))
    i=0; rex=0
    if raw and 0x40<=raw[0]<=0x4f:
        rex=raw[0]; i=1
    if len(raw)!=i+2 or raw[i] not in (0x39,0x3b,0x85) or raw[i+1]>>6!=3:
        return False
    regs=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi')+tuple('r%d'%n for n in range(8,16)) if rex&8 else ('eax','ecx','edx','ebx','esp','ebp','esi','edi')+tuple('r%dd'%n for n in range(8,16))
    mr=raw[i+1]; reg=regs[((mr>>3)&7)+8*bool(rex&4)]; rm=regs[(mr&7)+8*bool(rex&1)]
    op='test' if raw[i]==0x85 else 'cmp'
    operands=(reg+','+rm) if raw[i]==0x3b else (rm+','+reg)
    return all(x.mnemonic==op and re.sub(r'\s+','',x.operands.split('#',1)[0].lower())==operands for x in (a,b))
