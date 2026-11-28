"""Bounded dual-decoder coverage and conservative instruction-family census."""
import hashlib
import re
from collections import Counter
from .disasm import disassemble
from .pe import PEFormatError


FP = re.compile(r'v?(?:add|sub|mul|div|min|max|sqrt|rsqrt|rcp|hadd|hsub|addsub|fmadd\d*|fmsub\d*|fnmadd\d*|fnmsub\d*)(ss|sd|ps|pd)$')
X87 = re.compile(r'f(?:add|sub|subr|mul|div|divr|sqrt|scale|yl2x|2xm1|sin|cos|ptan|patan)(?:p)?$')


def family(mnemonic):
    match = FP.fullmatch(mnemonic)
    if match:
        return {'ss':'scalar32','sd':'scalar64','ps':'packed32','pd':'packed64'}[match[1]]
    if X87.fullmatch(mnemonic):
        return 'x87'
    return None


def reconcile(left, right, start, stop):
    """Require matching start and next decoded address; exclude last sites.

    A next address alone is not an independent proof of instruction length.
    Never accept zero-length, overlong, duplicate, or out-of-window spans.
    """
    def index(stream):
        rows = [x for x in stream if start <= x.address < stop]
        if any(a.address >= b.address for a,b in zip(rows,rows[1:])):
            raise ValueError('Duplicate or unordered instruction addresses')
        return {x.address:(x,y.address-x.address) for x,y in zip(rows,rows[1:])}, {x.address:x for x in rows}
    a, aa = index(left); b, bb = index(right)
    counts = Counter(); kinds = Counter(); outside = Counter(); verified = []
    for site in sorted(aa.keys() | bb.keys()):
        if site not in aa or site not in bb:
            counts['one_decoder_only'] += 1
        elif site not in a or site not in b:
            counts['terminal_unbounded'] += 1
        elif a[site][1] != b[site][1] or not 1 <= a[site][1] <= 15:
            counts['span_disagreement'] += 1
        elif a[site][0].mnemonic != b[site][0].mnemonic:
            counts['mnemonic_disagreement'] += 1
        else:
            counts['agreed_sites'] += 1
            counts['agreed_span_bytes'] += a[site][1]
            k = family(a[site][0].mnemonic)
            if k:
                kinds[k] += 1
                verified.append(site)
            continue
        for k, data in [('left',aa),('right',bb)]:
            if site in data and family(data[site].mnemonic):
                outside[k] += 1
    return {'counts':dict(counts),'fp_families':dict(kinds), 'excluded_fp_by_decoder':dict(outside)}, verified


def audit_scope(pe, fingerprint, start, length):
    if pe.sha256 != fingerprint:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1 <= length <= 32768:
        raise ValueError('Invalid bounded scope')
    raw = pe.at_rva(start,length,executable=True)
    va = pe.image_base+start
    a,b = [disassemble(pe,start,length,t) for t in ('objdump','llvm-objdump')]
    row, sites = reconcile(a,b,va,va+length)
    row.update(start=hex(start),bytes=length,scope_sha256=hashlib.sha256(raw).hexdigest(),
               fp_sites=[hex(x-pe.image_base) for x in sites],
               limits='Linear decoding and matching inferred spans only; not runtime, operand, or DSP semantics proof.')
    return row
