"""Read-only dual-decoder checkpoints and x64 chained-unwind navigation."""
import hashlib
import re
import struct
from .pe import PEFormatError
from .navigation import runtime_ranges
from .disasm import disassemble


def unwind_family(pe, root):
    """Return metadata-linked ranges, not guessed adjacent function boundaries."""
    rows = runtime_ranges(pe)
    starts = {r[0]: r for r in rows}
    if root not in starts:
        raise PEFormatError('Root lacks an unwind entry')
    parents = {}
    for row in rows:
        version_flags, _, count, _ = pe.at_rva(row[2], 4)
        flags = version_flags >> 3
        if flags & 4:
            if version_flags & 7 not in (1, 2) or flags & 3:
                raise PEFormatError('Invalid chained unwind flags')
            offset = 4 + ((count + 1) & ~1) * 2
            parent = struct.unpack('<III', pe.at_rva(row[2] + offset, 12))
            if starts.get(parent[0]) != parent:
                raise PEFormatError('Unwind parent does not match directory')
            parents[row[0]] = parent[0]
    family = []
    for row in rows:
        node = row[0]
        seen = set()
        while node in parents:
            if node in seen or len(seen) >= 64:
                raise PEFormatError('Cyclic or excessive unwind chain')
            seen.add(node)
            node = parents[node]
        if node == root:
            family.append({'start': hex(row[0]), 'end': hex(row[1]),
                           'unwind': hex(row[2]), 'parent': hex(parents[row[0]]) if row[0] in parents else None})
    return family


def normalized(ins):
    args = ins.operands.split('#', 1)[0].split('<', 1)[0].lower()
    args = re.sub(r'(?<![a-z0-9])(?:0x[0-9a-f]+|[0-9]+)(?![a-z0-9])',
                  lambda m: str(int(m[0], 16 if m[0].startswith('0x') else 10)), args)
    args = re.sub(r'\s+', '', args)
    # Intel syntax permits either scale*index or index*scale.
    args = re.sub(r'(?<![a-z0-9])([1248])\*([a-z][a-z0-9]+)', r'\2*\1', args)
    args = re.sub(r'\+0(?=\])', '', args)
    return ins.mnemonic, args


def checkpoint_report(pe, expected_sha256, scopes):
    """Disclose locations and agreement, never instruction text or coefficient bytes."""
    if pe.sha256 != expected_sha256:
        raise PEFormatError('Binary fingerprint mismatch')
    if not 1 <= len(scopes) <= 64:
        raise ValueError('Expected 1..64 scopes')
    result = []
    for start, length, sites in scopes:
        if len(sites) > 128 or any(not start <= s < start + length for s in sites):
            raise ValueError('Checkpoint outside scope or excessive count')
        maps = []
        for tool in ('objdump', 'llvm-objdump'):
            decoded = disassemble(pe, start, length, tool)
            maps.append({i.address - pe.image_base: normalized(i) for i in decoded})
        a, b = maps
        agreed = {s for s in a.keys() & b.keys() if a[s] == b[s]}
        result.append({'start': hex(start), 'bytes': length,
                       'scope_sha256': hashlib.sha256(pe.at_rva(start, length, executable=True)).hexdigest(),
                       'gnu_instructions': len(a), 'llvm_instructions': len(b),
                       'exact_normalized_agreement': len(agreed),
                       'verified_sites': [hex(s) for s in sites if s in agreed],
                       'unverified_sites': [hex(s) for s in sites if s not in agreed]})
    return {'binary_sha256': pe.sha256, 'scopes': result}
