"""Compare bounded direct-call observations, not inferred DSP or runtime routes."""
import re
from .disasm import disassemble


def call_observations(pe, lo, size, engine):
    rows = {}
    for ins in disassemble(pe, lo, size, objdump=engine):
        if ins.mnemonic != 'call':
            continue
        match = re.fullmatch(r'0x([0-9a-fA-F]+)(?:\s+<[^<>]+>)?', ins.operands)
        if not match:
            continue  # indirect or unsupported syntax, not a negative observation
        site = ins.address - pe.image_base
        target = int(match[1], 16) - pe.image_base
        if not lo <= site < lo + size or not 0 <= target < 2**32 or site in rows:
            raise ValueError('Invalid or repeated direct call')
        rows[site] = target
    return {'sha256': pe.sha256, 'start': lo, 'size': size, 'calls': rows}


def compare(left, right):
    if any(left[k] != right[k] for k in ('sha256', 'start', 'size')):
        raise ValueError('Source or scope mismatch')
    result = []
    for site in sorted(left['calls'].keys() | right['calls'].keys()):
        a, b = left['calls'].get(site), right['calls'].get(site)
        status = ('single_observation' if a is None or b is None else
                  'agreed_static' if a == b else 'conflict')
        result.append({'site_rva': hex(site), 'left_target': None if a is None else hex(a),
                       'right_target': None if b is None else hex(b), 'status': status})
    return result
