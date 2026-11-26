"""Conservative direct backward-branch envelopes, not executed loops."""
import hashlib
import re
from .disasm import disassemble
from .pe import PEFormatError

CC = ('o','no','b','ae','e','ne','be','a','s','ns','p','np','l','ge','le','g')
ALIASES = {'z':'e','nz':'ne','c':'b','nae':'b','nb':'ae','nc':'ae',
           'na':'be','nbe':'a','pe':'p','po':'np','nge':'l','nl':'ge','ng':'le','nle':'g'}


def direct_backedge(raw, site, mnemonic):
    if len(raw) == 2 and 0x70 <= raw[0] <= 0x7f:
        cc = CC[raw[0]-0x70]
    elif len(raw) == 6 and raw[0] == 0x0f and 0x80 <= raw[1] <= 0x8f:
        cc = CC[raw[1]-0x80]
    else:
        return None
    if not mnemonic.startswith('j') or ALIASES.get(mnemonic[1:],mnemonic[1:]) != cc:
        return None
    target = site+len(raw)+int.from_bytes(raw[-(len(raw)- (1 if len(raw)==2 else 2)):], 'little', signed=True)
    return target if target < site else None


def audit_envelopes(pe, fingerprint, start, length):
    if pe.sha256 != fingerprint:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1 <= length <= 32768:
        raise ValueError('Invalid bounded scope')
    raw = pe.at_rva(start,length,executable=True)
    maps = [{i.address-pe.image_base:i for i in disassemble(pe,start,length,t)
             if start <= i.address-pe.image_base < start+length} for t in ('objdump','llvm-objdump')]
    successors = [{a:b for a,b in zip(sorted(m),sorted(m)[1:])} for m in maps]
    common = maps[0].keys() & maps[1].keys()
    edges = []
    for site in sorted(common):
        a,b = (m[site] for m in maps)
        end = successors[0].get(site)
        if end is None or end != successors[1].get(site):
            continue
        target = direct_backedge(raw[site-start:end-start],site,a.mnemonic)
        if target is None or target not in common or direct_backedge(raw[site-start:end-start],site,b.mnemonic) != target:
            continue
        def agrees(i):
            m = re.match(r'^0x([0-9a-fA-F]+)(?:\s|$)',i.operands)
            return m is not None and int(m[1],16)-pe.image_base == target
        if not agrees(a) or not agrees(b):
            continue
        # Only count fully reconciled address sequences in the envelope.
        left,right = ([x for x in sorted(m) if target <= x <= site] for m in maps)
        if left != right:
            continue
        edges.append({'head':hex(target),'latch':hex(site),'sites':len(left)})
    return {'start':hex(start),'bytes':length,'scope_sha256':hashlib.sha256(raw).hexdigest(),
            'envelopes':edges,'limits':'Static backward conditional branch intervals only; no dominance, reachability, loop counts or runtime proof.'}
