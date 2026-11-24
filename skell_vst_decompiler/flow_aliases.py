"""Exact decoder-alias reconciliation for bounded static flow observations.

Never infer instructions from unmatched bytes. Preserve raw counts separately.
"""
from .static_flow import _parse, summarize


_ALIAS = {b'\x9b\xdb\xe2': ('fclex','fnclex'),
          b'\x9b\xdb\xe3': ('finit','fninit')}


def _render(rows):
    return '\n'.join(f'{va:x}: {raw.hex(" ")} {op}' for va,(raw,op) in sorted(rows.items()))


def _normalize(data, start, left, right):
    a,b = _parse(left,start,data),_parse(right,start,data)
    repairs = []
    for fused,split in ((a,b),(b,a)):
        for va,(raw,op) in tuple(fused.items()):
            alias = _ALIAS.get(raw)
            if alias is None or op != alias[0]:
                continue
            first = split.get(va)
            if (first not in ((b'\x9b','wait'),(b'\x9b','fwait')) or
                split.get(va+1) != (raw[1:],alias[1]) or
                va+1 in fused or va+2 in fused or va+2 in split):
                continue
            # Canonical pair preserves the independently observed split boundary.
            fused[va] = split[va] = (b'\x9b','wait')
            fused[va+1] = (raw[1:],alias[1])
            repairs.append(va)
    return _render(a),_render(b),len(repairs)


def reconcile(data, start, left, right, seeds, *, bits=32):
    """Split only verified fused WAIT/clear or WAIT/init equivalents.

    Source-byte validation and identical bounded input are required. A split
    boundary is derived from both observations, not a third independent decode.
    Exception paths are still outside the flow model. No code is returned.
    """
    seeds=tuple(seeds)
    raw_report=summarize(data,start,left,right,seeds,bits=bits)
    a,b,pairs=_normalize(data,start,left,right)
    normalized = summarize(data,start,a,b,seeds,bits=bits)
    return {'raw':raw_report,'normalized':normalized,
            'alias_pairs':pairs,
            'additional_reached_bytes':normalized['possible_reached_bytes']-raw_report['possible_reached_bytes'],
            'note':'Alias-normalized counts are derived; not independent engine agreement or runtime execution.'}
