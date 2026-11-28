"""Read-only x64 unwind-chain census and narrowly checked decoder aliases.
No vendor execution. Chain families describe unwind metadata, not DSP completeness.
"""
from collections import Counter
import struct
import re
from .navigation import runtime_ranges
from .pe import PEFormatError
from .scoped_trace import normalized


def chain_index(pe):
    rows = runtime_ranges(pe)
    directory = {r[0]: r for r in rows}
    parent = {}
    versions = Counter()
    unresolved = Counter()
    for start, end, info in rows:
        version_flags, _, count, _ = pe.at_rva(info, 4)
        version, flags = version_flags & 7, version_flags >> 3
        versions[version] += 1
        if not flags & 4:
            continue
        if version not in (1, 2) or flags & 3:
            unresolved['unsupported_flags_or_version'] += 1
            continue
        try:
            triple = struct.unpack('<III', pe.at_rva(info + 4 + 2 * ((count + 1) & ~1), 12))
        except PEFormatError:
            unresolved['unbacked_parent'] += 1
            continue
        if directory.get(triple[0]) != triple:
            unresolved['parent_not_exact_directory_entry'] += 1
            continue
        parent[start] = triple[0]
    roots = {}
    depth = {}
    for start in directory:
        path = []
        seen = set()
        node = start
        while node not in roots and node in parent:
            if node in seen or len(path) >= 64:
                raise PEFormatError('Cyclic or excessive chain')
            seen.add(node)
            path.append(node)
            node = parent[node]
        if node not in roots:
            roots[node], depth[node] = node, 0
        for child in reversed(path):
            roots[child] = roots[node]
            depth[child] = depth[node] + 1
            node = child
    sizes = Counter(roots.values())
    return {'records': len(rows), 'resolved_chain_edges': len(parent),
            'multi_range_families': sum(n > 1 for n in sizes.values()),
            'records_in_multi_range_families': sum(n for n in sizes.values() if n > 1),
            'largest_family_records': max(sizes.values(), default=0),
            'max_chain_depth': max(depth.values(), default=0),
            'versions': dict(versions), 'unresolved': dict(unresolved)}, roots


def redundant_rex_agreement(pe, left, right):
    """Only accept exact redundant REX forms of push rbp/rbx and near JMP [rax+disp32].
    Check original instruction bytes; never globally strip REX or merge mnemonics.
    """
    if left.address != right.address:
        return False
    if normalized(left) == normalized(right):
        return True
    for a, b in ((left, right), (right, left)):
        rva = a.address - pe.image_base
        try:
            if a.mnemonic == 'rex' and a.operands.lower() in ('push rbp', 'push rbx'):
                reg = a.operands.split()[1].lower()
                if pe.at_rva(rva, 2, executable=True) == bytes((0x40, {'rbp': 0x55, 'rbx': 0x53}[reg])) and normalized(b) == ('push', reg):
                    return True
            if a.mnemonic == 'rex.' and a.operands.lower().startswith('w jmp '):
                raw = pe.at_rva(rva, 7, executable=True)
                if raw[:3] != b'\x48\xff\xa0':
                    continue
                disp = struct.unpack_from('<i', raw, 3)[0]
                if disp < 0:
                    continue
                expected = ('jmp', 'qwordptr[rax+' + str(disp) + ']')
                # Match the explicitly decoded operand to the byte-derived target.
                from .disasm import Instruction
                reconstructed = Instruction(a.address, 'jmp', a.operands[6:])
                if normalized(reconstructed) == expected == normalized(b):
                    return True
        except PEFormatError:
            continue
    return False


def direct_edges(pe, start, length, roots=None):
    """Agreed direct CALL/JMP sites with byte-derived targets and metadata class.

    Bounded linear decode, not reachability. Intra-family jumps are retained;
    indirect dispatches are counted, not guessed.
    """
    from bisect import bisect_right
    from .disasm import disassemble
    if roots is None:
        _, roots = chain_index(pe)
    rows = runtime_ranges(pe)
    starts = [r[0] for r in rows]
    maps = [{i.address - pe.image_base: i for i in disassemble(pe, start, length, tool)}
            for tool in ('objdump', 'llvm-objdump')]
    a, b = maps
    result = []
    indirect = disagreements = 0
    for site, left in a.items():
        right = b.get(site)
        if right is None or not redundant_rex_agreement(pe, left, right):
            disagreements += 1
            continue
        if right.mnemonic not in ('call', 'jmp'):
            continue
        m = re.match(r'^0x([0-9a-fA-F]+)(?:\s|$)', right.operands)
        if not m:
            indirect += 1
            continue
        dest = int(m[1], 16) - pe.image_base
        if not start <= site < start + length:
            continue
        op = pe.at_rva(site, 1, executable=True)[0]
        size = 5 if op in (0xe8, 0xe9) else 2 if op == 0xeb else 0
        if not size or site + size > start + length or (right.mnemonic == 'call') != (op == 0xe8):
            continue
        raw = pe.at_rva(site, size, executable=True)
        if site + size + int.from_bytes(raw[1:], 'little', signed=True) != dest:
            continue
        idx = bisect_right(starts, dest) - 1
        region = rows[idx] if idx >= 0 and dest < rows[idx][1] else None
        try:
            pe.at_rva(dest, 1, executable=True)
            kind = ('unwind_entry' if region[0] == dest else 'unwind_interior') if region else 'executable_uncovered'
        except PEFormatError:
            kind = 'outside_file_backed_executable'
        result.append({'site': hex(site), 'target': hex(dest), 'kind': kind, 'op': right.mnemonic,
                       'family_root': hex(roots[region[0]]) if region else None})
    return {'start': hex(start), 'bytes': length, 'direct_edges': result,
            'indirect_sites': indirect, 'decoder_disagreements': disagreements}
