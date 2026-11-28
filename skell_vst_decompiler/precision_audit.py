"""Read-only, byte-backed floating-point path census. Not runtime dataflow."""
import hashlib
import re
from collections import Counter
from .disasm import disassemble
from .pe import PEFormatError


def audit_scope(pe, expected_sha256, start, length):
    if pe.sha256 != expected_sha256:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1 <= length <= 32768:
        raise ValueError('Invalid bounded scope')
    raw = pe.at_rva(start, length, executable=True)
    maps = [{i.address-pe.image_base: i for i in disassemble(pe, start, length, tool)
             if start <= i.address-pe.image_base < start+length}
            for tool in ('objdump', 'llvm-objdump')]
    left, right = maps
    counts = Counter()
    sites, edges = [], []
    for site in sorted(left.keys() & right.keys()):
        a, b = left[site], right[site]
        op = a.mnemonic
        if op != b.mnemonic:
            continue
        counts['mnemonic_agreement'] += 1
        code = raw[site-start:site-start+15]
        # Narrow opcode checks only. Do not infer operands, path or state aliasing.
        prefix = code[:1]
        tail = code[1:] if prefix in (b'\x66', b'\xf2', b'\xf3') else code
        if tail and 0x40 <= tail[0] <= 0x4f:
            tail = tail[1:]
        label = None
        kinds = {b'\x66':'addpd', b'\xf2':'addsd', b'\xf3':'addss'}
        if tail[:2] == b'\x0f\x58' and len(tail) >= 3 and op == kinds.get(prefix,'addps'):
            label = op
        elif len(tail) >= 3 and tail[:2] == b'\x0f\xae' and tail[2] < 0xc0:
            group = (tail[2] >> 3) & 7
            if (op, group) in (('ldmxcsr',2), ('stmxcsr',3)):
                label = op
        elif op == 'or' and (code.startswith(b'\x48\x0d\x40\x80\x00\x00') or code.startswith(b'\x0d\x40\x80\x00\x00')):
            label = 'ftz_daz_mask_or'
        if label:
            counts[label] += 1
            sites.append({'site':hex(site),'kind':label})
        if op not in ('call','jmp') or len(code) < 5 or code[0] != (0xe8 if op == 'call' else 0xe9):
            continue
        dest = site+5+int.from_bytes(code[1:5],'little',signed=True)
        def target(ins):
            m = re.match(r'^0x([0-9a-fA-F]+)(?:\s|$)',ins.operands)
            return int(m[1],16)-pe.image_base if m else None
        if target(a) != dest or target(b) != dest:
            continue
        try:
            pe.at_rva(dest,1,executable=True)
        except PEFormatError:
            continue
        edges.append({'site':hex(site),'target':hex(dest),'op':op})
    return {'start':hex(start),'bytes':length,'scope_sha256':hashlib.sha256(raw).hexdigest(),
            'gnu_sites':len(left),'llvm_sites':len(right),'counts':dict(counts),
            'selected_byte_backed_sites':sites,'direct_edges':edges,
            'limits':'Mnemonic plus selected opcode/relative-target agreement; no complete operand, reachability, or audio-role proof.'}
