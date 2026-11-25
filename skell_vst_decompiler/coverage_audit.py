"""Quantify limitations of unwind-based discovery, without exporting vendor code."""
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import struct
from .pe import PE, PEFormatError
from .navigation import runtime_ranges
from .relocation_navigation import relocated_slots


def coverage(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 256*1024*1024:
        raise ValueError('Invalid source file')
    pe = PE(path)
    if pe.sha256 != expected:
        raise ValueError('Fingerprint mismatch')
    sections = sorted((s.rva, s.rva + min(s.file_size, s.virtual_size), s.executable) for s in pe.sections if min(s.file_size, s.virtual_size))
    if any(a[1] > b[0] for a,b in zip(sections, sections[1:])):
        raise PEFormatError('Overlapping virtual sections')
    starts = [s[0] for s in sections]
    def section(rva, n):
        i = bisect_right(starts,rva)-1
        return sections[i] if i >= 0 and rva+n <= sections[i][1] else None
    ranges = runtime_ranges(pe)
    scope_starts = [r[0] for r in ranges]
    code_bytes = sum(end-begin for begin,end,exe in sections if exe)
    scope_bytes = 0
    for begin,end,_ in ranges:
        s = section(begin,end-begin)
        if not s or not s[2]:
            raise PEFormatError('Unwind range outside executable virtual bytes')
        scope_bytes += end-begin
    counts = Counter()
    unique = set()
    for slot in relocated_slots(pe):
        src = section(slot,8)
        if not src:
            counts['outside_virtual_bytes']+=1; continue
        if src[2]:
            counts['executable_source_slot']+=1; continue
        target = struct.unpack('<Q',pe.at_rva(slot,8))[0]-pe.image_base
        dst = section(target,1)
        if not dst or not dst[2]:
            counts['non_code_target']+=1; continue
        unique.add(target)
        i = bisect_right(scope_starts,target)-1
        if i < 0 or target >= ranges[i][1]:
            counts['no_unwind_range']+=1
        else:
            counts['unwind_start' if target == ranges[i][0] else 'unwind_interior']+=1
    # Unique addresses are not distinct logical functions; a gap may contain code,
    # padding or data. Coverage of code-section bytes is not algorithm completeness.
    unique_outside = sum(1 for v in unique if (i:=bisect_right(scope_starts,v)-1)<0 or v>=ranges[i][1])
    return dict(source_sha256=pe.sha256,executable_virtual_file_bytes=code_bytes,
                unwind_covered_bytes=scope_bytes,unwind_ranges=len(ranges),
                relocation_slots=sum(counts.values()),categories=dict(sorted(counts.items())),
                unique_code_targets=len(unique),unique_targets_without_unwind=unique_outside)
