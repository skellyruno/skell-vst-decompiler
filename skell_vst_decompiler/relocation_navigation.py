"""Bounded read-only PE relocation evidence; no runtime dispatch inference."""
from collections import Counter
import bisect
import json
from pathlib import Path
import struct
from .pe import PE, PEFormatError
from .navigation import runtime_ranges


def relocated_slots(pe):
    """DIR64 slots from original relocation metadata, not pointer guessing."""
    opt = pe._unpack('<I', 60)[0] + 24
    size = pe._unpack('<H', opt - 4)[0]
    # COFF SizeOfOptionalHeader is four bytes before the optional header.
    if size < 112 + 6 * 8 or pe._unpack('<I', opt + 108)[0] < 6:
        return []
    rva, n = pe._unpack('<II', opt + 112 + 5 * 8)
    if not rva and not n:
        return []
    if not rva or not 8 <= n <= 16 * 1024 * 1024:
        raise PEFormatError('Invalid relocation directory size')
    raw = pe.at_rva(rva, n)
    seen = set()
    p = 0
    while p < len(raw):
        if len(raw) - p < 8:
            raise PEFormatError('Truncated relocation block')
        page, block = struct.unpack_from('<II', raw, p)
        if page & 4095 or block < 8 or block % 4 or block > len(raw) - p:
            raise PEFormatError('Invalid relocation block')
        for (entry,) in struct.iter_unpack('<H', raw[p+8:p+block]):
            kind = entry >> 12
            if kind == 0:
                continue
            if kind != 10:
                raise PEFormatError('Unsupported non-DIR64 relocation in x64 image')
            slot = page + (entry & 4095)
            if slot in seen or len(seen) >= 1_000_000:
                raise PEFormatError('Duplicate or excessive relocation slots')
            pe.at_rva(slot, 8)
            seen.add(slot)
        p += block
    return sorted(seen)


def census(path, expected, anchors):
    """Summarize absolute file-image code pointers and evidence anchor scopes.

    Counts only non-executable, file-backed source slots with DIR64 records.
    No table contents, slot values, source code, or instructions are exported.
    Unwind start is compiler metadata, not a guaranteed function entry.
    """
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 256*1024*1024:
        raise ValueError('Invalid source file')
    if not isinstance(anchors, dict) or len(anchors)>64 or any(
        not isinstance(k,str) or not k or len(k)>128 or type(v) is not int or not 0<=v<2**32
        for k,v in anchors.items()):
        raise ValueError('Invalid anchors')
    pe = PE(path)
    if pe.sha256 != expected:
        raise ValueError('Fingerprint mismatch')
    ranges = runtime_ranges(pe)
    starts = [a for a,_,_ in ranges]
    def scope(rva):
        i = bisect.bisect_right(starts,rva)-1
        return ranges[i] if i>=0 and rva<ranges[i][1] else None
    # File-backed virtual bytes only; ignore executable relocation slots.
    secs = sorted(pe.sections,key=lambda s:s.rva)
    ends = [s.rva+min(s.virtual_size,s.file_size) for s in secs]
    if any(ends[i]>secs[i+1].rva for i in range(len(secs)-1)):
        raise PEFormatError('Overlapping file-backed virtual sections')
    srvas = [s.rva for s in secs]
    def section(rva,n):
        i=bisect.bisect_right(srvas,rva)-1
        return secs[i] if i>=0 and rva+n<=ends[i] else None
    slots = relocated_slots(pe)
    by_target=Counter()
    by_scope=Counter()
    categories=Counter()
    for slot in slots:
        src=section(slot,8)
        if src is None:
            categories['outside_virtual_bytes']+=1; continue
        if src.executable:
            categories['executable_source_slot']+=1; continue
        target=struct.unpack('<Q',pe.at_rva(slot,8))[0]-pe.image_base
        dst=section(target,1)
        if dst is None or not dst.executable:
            categories['non_code_target']+=1;continue
        by_target[target]+=1
        entry=scope(target)
        if entry is None:
            categories['no_unwind_range']+=1
        elif entry[0]==target:
            categories['unwind_start']+=1;by_scope[entry[0]]+=1
        else:
            categories['unwind_interior']+=1;by_scope[entry[0]]+=1
    result={}
    for label,rva in anchors.items():
        pe.at_rva(rva,1,executable=True)
        s=scope(rva)
        row={'anchor_rva':hex(rva),'exact_anchor_slots':by_target[rva], 'scope_start':None}
        if s:
            row.update(scope_start=hex(s[0]),anchor_is_scope_start=rva==s[0],
                       scope_start_slots=by_target[s[0]],scope_total_slots=by_scope[s[0]])
        result[label]=row
    return {'source_sha256':pe.sha256,'relocation_slots':len(slots),
            'categories':dict(sorted(categories.items())), 'unique_code_targets':len(by_target),
            'unwind_ranges':len(ranges),'anchors':result,
            'limits':'File-image absolute DIR64 references only; not runtime calls, vtables or algorithm identity. Relative pointers and leaf/indirect dispatch remain unresolved.'}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary');p.add_argument('sha256');p.add_argument('anchors',nargs='*',help='label:hex-rva')
    a=p.parse_args();pairs=[v.rsplit(':',1) for v in a.anchors];targets={k:int(v,16) for k,v in pairs}
    if len(targets)!=len(pairs):raise ValueError('Duplicate anchors')
    print(json.dumps(census(a.binary,a.sha256,targets),indent=2,allow_nan=False))
