"""Measure sensitivity of bounded static flow to a wider verified code scope.

Only aggregate instruction-span observations are returned. No call traversal,
indirect target resolution, recovered source or runtime reachability claim.
"""
from .static_flow import _parse, _classify


def _graph(data, start, left, right, bits):
    if not isinstance(data,bytes) or not 0<len(data)<=262144 or type(start) is not int or start<0 or bits not in (32,64):
        raise ValueError('Invalid scope')
    a,b=_parse(left,start,data),_parse(right,start,data)
    rows={v:(a[v][0],a[v][1],b[v][1]) for v in a.keys()&b.keys() if a[v][0]==b[v][0]}
    ordered=sorted(rows)
    if any(v+len(rows[v][0])>w for v,w in zip(ordered,ordered[1:])):
        raise ValueError('Overlapping agreeing spans')
    graph={}
    for v,(raw,op1,op2) in rows.items():
        kind,delta=_classify(raw,op1,op2,bits);nxt=v+len(raw)
        if kind in ('direct_call','indirect_call','fallthrough'):dest=(nxt,)
        elif kind=='conditional':dest=(nxt,nxt+delta)
        elif kind=='jump':dest=(nxt+delta,)
        else:dest=()
        graph[v]=(raw,dest)
    return graph


def _walk(graph,seed):
    seen=set();todo=[seed]
    while todo:
        v=todo.pop()
        if v in seen or v not in graph:continue
        seen.add(v);todo.extend(graph[v][1])
    return seen


def compare_context(data,start,left,right,child_start,child_size,child_left,child_right,*,bits=32):
    """Compare a child scope with its enclosing scope, at two explicit seeds.

    Match exact spans across both decodes; context-only spans are not counted
    as recovered child instructions. The enclosing seed may be an unwind
    record start, not a function entry. Calls are assumed returning.
    """
    if (type(child_start) is not int or type(child_size) is not int or
        not 0<child_size<=len(data) or not start<=child_start<=start+len(data)-child_size):
        raise ValueError('Child outside scope')
    full=_graph(data,start,left,right,bits)
    child=data[child_start-start:child_start-start+child_size]
    small=_graph(child,child_start,child_left,child_right,bits)
    comparable={v for v,(raw,_) in small.items() if v in full and full[v][0]==raw}
    local=_walk(small,child_start)
    same=_walk(full,child_start)&comparable
    entry=_walk(full,start)&comparable
    def counts(seen):
        gained=seen-local;lost=local-seen
        return {'reached_comparable_spans':len(seen),'additional_spans':len(gained),'additional_bytes':sum(len(small[v][0]) for v in gained),
                'local_spans_not_confirmed':len(lost),'local_bytes_not_confirmed':sum(len(small[v][0]) for v in lost)}
    return {'child_agreed_spans':len(small),'local_reached_spans':len(local),'comparable_spans':len(comparable),
            'enclosing_agreed_spans':len(full),'child_seed_agreed_in_enclosing':child_start in full,
            'enclosing_seed_agreed':start in full,'same_seed_enclosing':counts(same),'enclosing_entry_seed':counts(entry),
            'note':'Static scope-sensitivity comparison, not a runtime path or recovered function.'}


def compare_alias_context(data,start,left,right,child_start,child_size,child_left,child_right,*,bits=32):
    """Report raw and exact decoder-alias-normalized scope comparisons separately."""
    from .flow_aliases import _normalize
    raw=compare_context(data,start,left,right,child_start,child_size,child_left,child_right,bits=bits)
    a,b,pairs=_normalize(data,start,left,right)
    child=data[child_start-start:child_start-start+child_size]
    ca,cb,cpairs=_normalize(child,child_start,child_left,child_right)
    normalized=compare_context(data,start,a,b,child_start,child_size,ca,cb,bits=bits)
    return {'raw':raw,'normalized':normalized,'enclosing_alias_pairs':pairs,'child_alias_pairs':cpairs}
