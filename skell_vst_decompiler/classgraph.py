"""Read-only MSVC x64 RTTI class graph and independent analyzer reconciliation.

Class/slot identities are static candidates, never runtime dispatch or DSP proof.
No target code is executed, no Ghidra/Rizin source is embedded.
"""
import argparse
import json
from pathlib import Path
import re
import struct
from .pe import PE, PEFormatError
from .navigation import runtime_ranges, containing_range
from .ghidra_bridge import make_plan, run_analysis

MAX_BASES = 256
MAX_SLOTS = 64


def type_name(pe, rva):
    name = pe.cstring_rva(rva + 16, 1024)
    if not name.startswith(('.?AV', '.?AU')) or not name.endswith('@@'):
        raise PEFormatError('Not an MSVC class TypeDescriptor')
    return name


def hierarchy(pe, rva, type_rva):
    sig, flags, count, array = struct.unpack('<4I', pe.at_rva(rva, 16))
    if sig != 0 or not 1 <= count <= MAX_BASES:
        raise PEFormatError('Invalid class hierarchy')
    bases = []
    for (ref,) in struct.iter_unpack('<I', pe.at_rva(array, 4 * count)):
        typ, descendants, mdisp, pdisp, vdisp, attr = struct.unpack('<IIiiiI', pe.at_rva(ref, 24))
        if descendants >= count:
            raise PEFormatError('Invalid hierarchy subtree count')
        bases.append({'type_rva': hex(typ), 'type': type_name(pe, typ), 'contained_bases': descendants,
                      'member_displacement': mdisp, 'vbtable_displacement': pdisp,
                      'virtual_displacement': vdisp, 'attributes': hex(attr)})
    if int(bases[0]['type_rva'], 16) != type_rva:
        raise PEFormatError('Hierarchy root differs from locator type')
    return {'attributes': hex(flags), 'base_records': bases}


def find_all(data, pattern, start, stop):
    while True:
        pos = data.find(pattern, start, stop)
        if pos < 0:
            return
        yield pos
        start = pos + 1


def class_graph(pe, keyword, max_classes=128):
    if not keyword or len(keyword) > 128 or not 1 <= max_classes <= 512:
        raise ValueError('Invalid class keyword or limit')
    entries = runtime_ranges(pe)
    data = pe.data
    sections = [s for s in pe.sections if s.name in ('.data', '.rdata') and not s.executable]
    ro = pe.section('.rdata')
    if ro is None or ro.executable:
        raise PEFormatError('Expected non-executable .rdata')
    lo, hi = ro.file_offset, ro.file_offset + ro.file_size
    rows = []
    # Only exact MSVC class-name prefixes; self-relative COL and validated
    # hierarchy eliminate string-only hits. No scanning code/protection stubs.
    for s in sections:
        for m in re.finditer(rb'\.\?A[VU][ -~]{1,1000}?@@\x00', data[s.file_offset:s.file_offset+s.file_size]):
            name = m.group()[:-1].decode('ascii')
            if keyword.casefold() not in name.casefold() or m.start() < 16:
                continue
            typ = s.rva + m.start() - 16
            if typ % 8:
                continue
            tables = []
            for p in find_all(data, struct.pack('<I', typ), lo + 12, hi - 8):
                pos = p - 12
                col = ro.rva + pos - lo
                if col % 4 or pos + 24 > hi:
                    continue
                sig, offset, ctor, t, h, self_rva = struct.unpack_from('<6I', data, pos)
                if sig != 1 or self_rva != col or t != typ or offset > 0x100000 or ctor > 0x100000:
                    continue
                try:
                    graph = hierarchy(pe, h, typ)
                except PEFormatError:
                    continue
                for slot in find_all(data, struct.pack('<Q', pe.image_base + col), lo, hi):
                    table = ro.rva + slot + 8 - lo
                    if table % 8:
                        continue
                    methods = []
                    for i in range(MAX_SLOTS):
                        loc = slot + 8 + i * 8
                        if loc + 8 > hi:
                            break
                        target = struct.unpack_from('<Q', data, loc)[0] - pe.image_base
                        try:
                            pe.at_rva(target, 1, executable=True)
                        except PEFormatError:
                            break
                        methods.append({'slot': i, 'rva': hex(target), 'unwind_region': containing_range(entries, target)})
                    if methods:
                        tables.append({'locator_rva': hex(col), 'vtable_rva': hex(table), 'subobject_offset': offset,
                                       'constructor_displacement': ctor, 'hierarchy_rva': hex(h),
                                       'hierarchy': graph, 'candidate_slots': methods,
                                       'slot_scan_capped': len(methods) == MAX_SLOTS})
            if tables:
                rows.append({'type': name, 'type_rva': hex(typ), 'vtables': tables})
                if len(rows) == max_classes:
                    break
        if len(rows) == max_classes:
            break
    return {'binary_sha256': pe.sha256, 'keyword': keyword, 'classes': rows,
            'class_limit_reached': len(rows) == max_classes,
            'note': 'Validated RTTI locator/hierarchy records; contiguous executable pointers are candidate slots, not proven table lengths or runtime targets.'}


def class_plan(pe, keyword, exact_type, table_rva, slots):
    """Explicit class/slot selection, freshly validated against the source."""
    if not slots or len(slots) > MAX_SLOTS or any(type(i) is not int or not 0 <= i < MAX_SLOTS for i in slots):
        raise ValueError('Choose 1..64 valid candidate slot indices')
    graph = class_graph(pe, keyword)
    matches = [t for c in graph['classes'] if c['type'] == exact_type for t in c['vtables'] if int(t['vtable_rva'], 16) == table_rva]
    if len(matches) != 1:
        raise ValueError('Exact class/table identity not found')
    by_slot = {m['slot']: int(m['rva'], 16) for m in matches[0]['candidate_slots']}
    if any(i not in by_slot for i in slots):
        raise ValueError('Requested slot is not a file-backed candidate')
    return make_plan(pe, [by_slot[i] for i in slots])


def compare_rizin(pe, document):
    """Compare Rizin aflj VAs with PE unwind boundaries. Never infer identity.

    The input wrapper is supplied locally by the analyst; SHA is a binding,
    not proof that Rizin actually generated the list. Rebasing is explicit.
    """
    if document.get('binary_sha256') != pe.sha256:
        raise ValueError('Analyzer input fingerprint mismatch')
    base = document.get('image_base')
    funcs = document.get('functions')
    if type(base) is not int or not 0 <= base < (1 << 64) or not isinstance(funcs, list) or len(funcs) > 500000:
        raise ValueError('Invalid analyzer base or function list')
    entries = runtime_ranges(pe)
    counts = {'exact_unwind_start': 0, 'inside_unwind_range': 0, 'no_unwind_record': 0, 'not_file_backed_executable': 0}
    rows = []
    seen = set()
    for f in funcs:
        if not isinstance(f, dict) or type(f.get('offset')) is not int or not 0 <= f['offset'] < (1 << 64):
            raise ValueError('Invalid Rizin function offset')
        rva = f['offset'] - base
        if rva in seen:
            continue
        seen.add(rva)
        try:
            pe.at_rva(rva, 1, executable=True)
            region = containing_range(entries, rva)
            status = ('no_unwind_record' if region is None else 'exact_unwind_start' if int(region['start_rva'], 16) == rva else 'inside_unwind_range')
        except PEFormatError:
            status, region = 'not_file_backed_executable', None
        counts[status] += 1
        rows.append({'rva': hex(rva), 'status': status, 'unwind_region': region})
    return {'binary_sha256': pe.sha256, 'counts': counts, 'functions': rows,
            'note': 'Imported candidate functions, not verified engine output or recovered DSP. Unwind ranges may represent fragments; missing unwind records are not failures.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary', type=Path)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--class-keyword')
    g.add_argument('--rizin-index', type=Path)
    p.add_argument('--exact-type')
    p.add_argument('--table-rva', type=lambda s: int(s,0))
    p.add_argument('--slots', type=int, nargs='+')
    p.add_argument('--ghidra-home', type=Path, help='Run the existing optional headless bridge on explicitly selected slots')
    p.add_argument('--work-root', type=Path, default=Path('local/ghidra'))
    p.add_argument('--seconds', type=int, default=300)
    a = p.parse_args()
    selected = (a.exact_type is not None, a.table_rva is not None, a.slots is not None)
    if any(selected) and (not all(selected) or not a.class_keyword):
        p.error('Slot plans require --class-keyword, --exact-type, --table-rva and --slots')
    if a.ghidra_home and not all(selected):
        p.error('--ghidra-home requires explicit class/table/slot selection')
    pe = PE(a.binary)
    if a.rizin_index:
        if a.rizin_index.stat().st_size > 64_000_000:
            raise ValueError('Analyzer JSON exceeds size limit')
        result = compare_rizin(pe, json.loads(a.rizin_index.read_text(encoding='utf-8')))
    elif all(selected):
        result = class_plan(pe, a.class_keyword, a.exact_type, a.table_rva, a.slots)
        if a.ghidra_home:
            result = run_analysis(pe, result, a.ghidra_home, a.work_root, a.seconds)
    else:
        result = class_graph(pe, a.class_keyword)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
