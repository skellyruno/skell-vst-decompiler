"""Bounded read-only intraprocedural flow audit, not source reconstruction.

Only agreeing, source-verified instruction spans are admitted. Calls are
observed but not followed; continuation assumes a returning call. Both arms
of conditional branches are possible, not proven executable paths.
"""
import bisect
from collections import Counter
import hashlib
import re

LINE = re.compile(r'^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)(\S+)(?:\s|$)')


def _parse(text, start, data):
    rows = {}
    for line in text.splitlines():
        match = LINE.match(line)
        if not match:
            continue
        va = int(match[1], 16)
        raw = bytes.fromhex(match[2]); op = match[3].lower()
        offset = va - start
        if offset < 0 or offset+len(raw) > len(data) or not 1 <= len(raw) <= 15:
            continue
        if data[offset:offset+len(raw)] != raw:
            raise ValueError('Decoder bytes disagree with source')
        if op.startswith('.') or op in ('(bad)', '<unknown>', 'unknown'):
            continue
        if va in rows:
            raise ValueError('Duplicate instruction start')
        rows[va] = raw, op
    return rows


def _classify(raw, a, b, bits):
    """Recognize unprefixed relative branches; stop on unsupported control forms."""
    op = raw[0]; n = len(raw)
    # GNU may print a redundant REX token before a stack operation.
    # Admit only the exact two-byte x64 push/pop encoding, not arbitrary prefixes.
    if bits==64 and n==2 and 0x40<=op<=0x4f and 0x50<=raw[1]<=0x5f:
        stack='push' if raw[1]<0x58 else 'pop'
        if (a=='rex' and b.startswith(stack)) or (b=='rex' and a.startswith(stack)):
            return 'fallthrough', None
    def both(prefix):
        return a.startswith(prefix) and b.startswith(prefix)
    def delta(offset):
        return int.from_bytes(raw[offset:], 'little', signed=True)
    if op == 0xe8 and n == 5 and both('call'):
        return 'direct_call', delta(1)
    if ((op == 0xe9 and n == 5) or (op == 0xeb and n == 2)) and both('jmp'):
        return 'jump', delta(1)
    if ((0x70 <= op <= 0x7f and n == 2) or (op == 0x0f and n == 6 and 0x80 <= raw[1] <= 0x8f)) and both('j') and not a.startswith('jmp') and not b.startswith('jmp'):
        return 'conditional', delta(n-1 if n == 2 else 2)
    if 0xe0 <= op <= 0xe3 and n == 2 and (both('loop') or both('j')):
        return 'conditional', delta(1)
    if op == 0xff and n >= 2 and both('call') and (raw[1] >> 3) & 7 == 2:
        return 'indirect_call', None
    if op == 0xff and n >= 2 and both('jmp') and (raw[1] >> 3) & 7 == 4:
        return 'indirect_jump', None
    if ((op == 0xc3 and n == 1) or (op == 0xc2 and n == 3)) and both('ret'):
        return 'return', None
    # Do not assume fallthrough for interrupt, system, prefix-only, far or
    # decoder-disputed control transfer. Unsupported paths stay explicit.
    if op in (0xcc,0xcd,0xce,0xcf,0xf1,0xf4,0xea,0x9a,0xca,0xcb) or raw[:2] in (b'\x0f\x05',b'\x0f\x07',b'\x0f\x0b',b'\x0f\x34',b'\x0f\x35'):
        return 'barrier', None
    prefixes=('j','call','ret','loop','int','iret','sys','ud','hlt','rep','lock','data','addr','rex','bnd','xbegin','xabort','rsm','vmcall','vmmcall')
    if (op in (0xe8,0xe9,0xeb,0xc2,0xc3) or 0x70<=op<=0x7f or 0xe0<=op<=0xe3 or
        (op==0x0f and n>=2 and 0x80<=raw[1]<=0x8f) or
        (op==0xff and n>=2 and ((raw[1]>>3)&7) in (2,3,4,5)) or
        a.startswith(prefixes) or b.startswith(prefixes)):
        return 'barrier', None
    return 'fallthrough', None


def summarize(data, start, left, right, seeds, *, bits=32):
    """Aggregate possible intraprocedural paths under explicitly stated assumptions.

    Output contains counts only, no instructions, targets, or proprietary code.
    A seed may be a research-range start, not an established function entry.
    """
    if not isinstance(data,bytes) or not 0<len(data)<=262144 or type(start) is not int or start<0:
        raise ValueError('Invalid bounded scope')
    if bits not in (32,64):raise ValueError('Unsupported instruction mode')
    seeds=tuple(seeds)
    if not 1<=len(seeds)<=4096 or any(type(v) is not int or not start<=v<start+len(data) for v in seeds) or len(set(seeds))!=len(seeds):
        raise ValueError('Invalid seed set')
    a,b=_parse(left,start,data),_parse(right,start,data)
    agreed={va:(a[va][0],a[va][1],b[va][1]) for va in a.keys()&b.keys() if a[va][0]==b[va][0]}
    addresses=sorted(agreed)
    # Overlap is an ambiguous boundary, never silently admitted.
    if any(va+len(agreed[va][0])>nxt for va,nxt in zip(addresses,addresses[1:])):
        raise ValueError('Overlapping agreed instruction spans')
    def location(va):
        if not start<=va<start+len(data):return 'outside_scope'
        if va in agreed:return 'agreed_start'
        j=bisect.bisect_right(addresses,va)-1
        if j>=0 and va<addresses[j]+len(agreed[addresses[j]][0]):return 'interior_of_span'
        return 'unverified_boundary'
    edges=Counter(); calls=Counter(); kinds=Counter(); seen=set(); todo=list(seeds); seed_status=Counter(location(v) for v in seeds)
    def edge(va):
        where=location(va);edges[where]+=1
        if where=='agreed_start' and va not in seen:todo.append(va)
    while todo:
        va=todo.pop()
        if va in seen or va not in agreed:continue
        seen.add(va);raw,op1,op2=agreed[va];next_va=va+len(raw)
        kind,delta=_classify(raw,op1,op2,bits);kinds[kind]+=1
        if kind=='direct_call':
            calls[location(next_va+delta)]+=1;edge(next_va)
        elif kind in ('fallthrough','indirect_call'):edge(next_va)
        elif kind in ('conditional','jump'):
            edge(next_va+delta)
            if kind=='conditional':edge(next_va)
    return {'scope_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'bits':bits,'agreed_spans':len(agreed),
            'seed_status':dict(seed_status),'possible_reached_spans':len(seen),'possible_reached_bytes':sum(len(agreed[v][0]) for v in seen),
            'not_reached_in_model':len(agreed)-len(seen),'instruction_categories':dict(kinds),'flow_destinations':dict(edges),
            'direct_call_destinations_not_followed':dict(calls),
            'limits':'Bounded static paths only; no call traversal, indirect resolution, exception flow or runtime proof.'}
