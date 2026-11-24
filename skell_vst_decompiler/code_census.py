"""Aggregate cross-disassembler instruction evidence, without exporting code bytes.

Static linear disassembly, not runtime reachability or source recovery.
"""
import hashlib
import re

LINE = re.compile(r'^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)(\S+)(?:\s|$)')
SIMD = re.compile(r'^(?:v)?(?:add|sub|mul|div|min|max|sqrt|rsqrt|rcp|cmp|ucomi|comi|hadd|hsub)(?:ss|sd|ps|pd)$')


def parse(text, start, data):
    """Return verified complete instruction observations for a bounded byte range."""
    if not isinstance(data, bytes) or not 0 < len(data) <= 262144 or start < 0:
        raise ValueError('Invalid bounded code scope')
    rows = {}
    for line in text.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        va = int(m[1], 16)
        raw = bytes.fromhex(m[2])
        op = m[3].lower()
        offset = va - start
        if offset < 0 or offset + len(raw) > len(data) or not 1 <= len(raw) <= 15:
            continue
        if data[offset:offset+len(raw)] != raw:
            raise ValueError('Disassembly bytes differ from source')
        if op.startswith('.') or op in ('(bad)', '<unknown>', 'unknown'):
            continue
        if va in rows:
            raise ValueError('Duplicate instruction location')
        rows[va] = (raw, op)
    return rows


def fwait_equivalences(a, b):
    """Count exact known x87 WAIT + clear/init aliases split by one decoder.

    This is supplementary evidence; do not silently change span counts.
    """
    equivalent = set()
    for fused, split in ((a,b),(b,a)):
        for va,(raw,op) in fused.items():
            if (raw,op) not in ((b"\x9b\xdb\xe2","fclex"),(b"\x9b\xdb\xe3","finit")):
                continue
            first = split.get(va)
            second = split.get(va+1)
            if (first in ((b"\x9b","wait"),(b"\x9b","fwait")) and
                second == (raw[1:],"fnclex" if op=="fclex" else "fninit")):
                equivalent.add(va)
    return len(equivalent)


def compare(data, start, left, right):
    """Summarize agreeing byte spans and selected unprefixed x86 instruction families."""
    a,b = parse(left,start,data),parse(right,start,data)
    matched = {va: a[va] for va in a.keys() & b.keys() if a[va][0] == b[va][0]}
    direct = set()
    x87 = simd = indirect = ret = conditional = 0
    for va,(raw,op) in matched.items():
        other = b[va][1]
        if raw[0] == 0xe8 and len(raw) == 5 and op.startswith('call') and other.startswith('call'):
            direct.add((va, va+5+int.from_bytes(raw[1:], 'little', signed=True)))
        elif op.startswith('call') and other.startswith('call'):
            indirect += 1  # includes uncommon non-E8 calls; not necessarily indirect
        x87 += 0xd8 <= raw[0] <= 0xdf and op.startswith('f') and other.startswith('f')
        simd += bool(SIMD.fullmatch(op) and SIMD.fullmatch(other))
        ret += op.startswith('ret') and other.startswith('ret')
        conditional += op.startswith('j') and not op.startswith('jmp') and other.startswith('j') and not other.startswith('jmp')
    return {'scope_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
            'gnu_decoded':len(a),'llvm_decoded':len(b),'exact_span_agreement':len(matched),
            'gnu_only_locations':len(a.keys()-b.keys()),'llvm_only_locations':len(b.keys()-a.keys()),
            'different_span_at_shared_location':len(a.keys() & b.keys())-len(matched),
            'fwait_equivalent_pairs':fwait_equivalences(a,b),
            'agreed_instruction_bytes':sum(len(raw) for raw,_ in matched.values()),
            'direct_rel32_calls':len(direct),'unique_direct_targets':len({t for _,t in direct}),
            'direct_targets_at_agreed_scope_locations':len({t for _,t in direct if t in matched}),
            'other_call_encodings':indirect,'x87_unprefixed':int(x87),'simd_fp_arithmetic':simd,
            'return_mnemonics':int(ret),'conditional_jump_mnemonics':int(conditional)}
