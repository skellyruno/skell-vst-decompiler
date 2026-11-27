"""Read-only arithmetic candidate triage of ordinary .text unwind extents.

Raw opcode markers are a cheap *heuristic*, not decoded instructions. The
report confirms only selected arithmetic mnemonics/spans with two decoders.
Never interprets proprietary coefficients, algorithms, or dynamic dispatch.
"""
import re
from fractions import Fraction
from .navigation import runtime_ranges
from .pe import PEFormatError
from .scope_consensus import audit_scope

# Legacy SSE arithmetic markers. No claim of instruction alignment; AVX/x87
# can be missed by the prefilter and are covered only by the stratified lane.
MARKER = re.compile(rb'[\x66\xf2\xf3]?[\x40-\x4f]?\x0f[\x51\x58\x59\x5c\x5d\x5e\x5f]')


def select_windows(pe, fingerprint, excluded=(), *, per_lane=12):
    """Choose complete nonoverlapping .text extents by three bounded lanes."""
    if pe.sha256 != fingerprint:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(per_lane) is not int or not 1 <= per_lane <= 64:
        raise ValueError('per_lane must be 1..64')
    excluded = list(excluded)
    if len(excluded) > 1024 or any(type(a) is not int or type(b) is not int or not 0 <= a < b <= 2**32 for a,b in excluded):
        raise ValueError('Invalid exclusion intervals')
    text = pe.section('.text')
    if text is None or not text.executable:
        raise PEFormatError('No ordinary executable .text')
    end_text = text.rva + min(text.file_size, text.virtual_size)
    entries = runtime_ranges(pe)
    eligible = []
    for a,b,_ in entries:
        if not (text.rva <= a < b <= end_text and 128 <= b-a <= 8192):
            continue
        if any(a < y and x < b for x,y in excluded):
            continue
        n = sum(1 for _ in MARKER.finditer(pe.at_rva(a,b-a,executable=True)))
        eligible.append((a,b,n))
    chosen = {}
    def add(rows, lane):
        for a,b,n in rows:
            if (a,b) not in chosen:
                chosen[a,b] = {'start':a,'bytes':b-a,'marker_count':n,'lane':lane}
    n = len(eligible)
    k = min(n,per_lane)
    if k:
        add([eligible[(2*i+1)*n//(2*k)] for i in range(k)],'stratified')
    positive = [r for r in eligible if r[2] >= 4]
    for lane,key in [('marker_count',lambda r:(-r[2],r[0])),
                     ('marker_density',lambda r:(-Fraction(r[2],r[1]-r[0]),r[0]))]:
        available = [r for r in positive if (r[0],r[1]) not in chosen]
        add(sorted(available,key=key)[:per_lane],lane)
    return {'runtime_records':len(entries),'eligible_extents':n,
            'marker_positive_extents':len(positive),'windows':list(chosen.values())}


def survey(pe, fingerprint, excluded=(), *, per_lane=12):
    result = select_windows(pe,fingerprint,excluded,per_lane=per_lane)
    for row in result['windows']:
        audit = audit_scope(pe,fingerprint,row['start'],row['bytes'])
        # Report evidence summaries, never disassembly or vendor constant data.
        row.update(scope_sha256=audit['scope_sha256'],counts=audit['counts'],
                   fp_families=audit['fp_families'],
                   excluded_fp_by_decoder=audit['excluded_fp_by_decoder'])
        row['selected_fp_sites'] = sum(row['fp_families'].values())
    result.update(binary_sha256=fingerprint,per_lane=per_lane,
                  limits='Unwind records are not logical functions; sampling is biased by markers. Arithmetic is not proof of audio processing or runtime reachability.')
    return result


def shape_signature(pe, fingerprint, start, length):
    """Strict cross-decoder structural signature; never compares operand values.

    Identical signatures can indicate compiler/library duplication but cannot
    prove shared origin or equivalent semantics. The terminal instruction is
    omitted because its complete span has not been independently established.
    """
    import hashlib
    from .disasm import disassemble
    if pe.sha256 != fingerprint:
        raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1 <= length <= 8192:
        raise ValueError('Invalid signature window')
    pe.at_rva(start,length,executable=True)
    va = pe.image_base+start
    shapes = []
    for tool in ('objdump','llvm-objdump'):
        rows = [i for i in disassemble(pe,start,length,tool) if va<=i.address<va+length]
        if not rows or rows[0].address != va:
            return None
        shape = [(a.address-va,b.address-a.address,a.mnemonic) for a,b in zip(rows,rows[1:])]
        if len(shape)<16 or any(not 1<=n<=15 for _,n,_ in shape):
            return None
        shapes.append(shape)
    if shapes[0]!=shapes[1]:
        return None
    return hashlib.sha256(repr(shapes[0]).encode('ascii')).hexdigest()
