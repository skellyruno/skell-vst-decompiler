"""Bounded, byte-backed x64 direct conditional branch evidence (not reachability)."""
import hashlib
import re
from .disasm import disassemble
from .pe import PEFormatError

_CONDITIONS = ('o','no','b','ae','e','ne','be','a','s','ns','p','np','l','ge','le','g')
_ALIASES = {'c':'b','nae':'b','nb':'ae','nc':'ae','z':'e','nz':'ne',
            'na':'be','nbe':'a','pe':'p','po':'np','nge':'l','nl':'ge','ng':'le','nle':'g'}


def conditional_target(raw, site, mnemonic):
    """Require the condition opcode and the complete signed displacement."""
    if len(raw) >= 2 and 0x70 <= raw[0] <= 0x7f:
        size, cc = 2, raw[0] - 0x70
    elif len(raw) >= 6 and raw[0] == 0x0f and 0x80 <= raw[1] <= 0x8f:
        size, cc = 6, raw[1] - 0x80
    else:
        return None
    if not mnemonic.startswith('j') or _ALIASES.get(mnemonic[1:], mnemonic[1:]) != _CONDITIONS[cc]:
        return None
    return site + size + int.from_bytes(raw[size-(1 if size == 2 else 4):size], 'little', signed=True)


def audit_branches(pe, expected_sha256, start, length):
    if pe.sha256 != expected_sha256:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1 <= length <= 32768:
        raise ValueError('Invalid bounded scope')
    raw = pe.at_rva(start, length, executable=True)
    left, right = [{i.address-pe.image_base: i for i in disassemble(pe,start,length,tool)
                    if start <= i.address-pe.image_base < start+length}
                   for tool in ('objdump','llvm-objdump')]
    edges = []
    rejected = 0
    for site in sorted(left.keys() | right.keys()):
        a, b = left.get(site), right.get(site)
        def conditional(ins):
            return ins is not None and ins.mnemonic.startswith('j') and _ALIASES.get(ins.mnemonic[1:], ins.mnemonic[1:]) in _CONDITIONS
        if not (conditional(a) or conditional(b)):
            continue
        chunk = raw[site-start:site-start+6]
        def target(ins):
            if not conditional(ins):
                return None
            m = re.match(r'^0x([0-9a-fA-F]+)(?:\s|$)',ins.operands)
            decoded = int(m[1],16)-pe.image_base if m else None
            byte_target = conditional_target(chunk,site,ins.mnemonic)
            return decoded if byte_target is not None and decoded == byte_target else None
        da, db = target(a), target(b)
        if da is None or da != db:
            rejected += 1
            continue
        try:
            pe.at_rva(da,1,executable=True)
        except PEFormatError:
            rejected += 1
            continue
        edges.append({'site':hex(site),'target':hex(da),'direction':'backward' if da < site else 'forward',
                      'target_in_scope':start <= da < start+length})
    return {'start':hex(start),'bytes':length,'scope_sha256':hashlib.sha256(raw).hexdigest(),
            'conditional_edges':edges,'rejected_sites':rejected,
            'limits':'Conditional direct targets only; no runtime branch, loop count or reachability proof.'}
