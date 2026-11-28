"""Compare exact-build entry claims without treating unwind hints as function extents."""
import re
from .navigation import containing_range


def audit_boundaries(fingerprint, ranges, documents, expected):
    if not isinstance(fingerprint,str) or not re.fullmatch(r'[0-9a-f]{64}',fingerprint):
        raise ValueError('Invalid source fingerprint')
    expected=set(expected)
    if any(type(x) is not int or not 0<=x<2**32 for x in expected):
        raise ValueError('Invalid requested address')
    by_engine={}
    for doc in documents:
        name=doc['engine']
        if not isinstance(name,str) or not name or name in by_engine or doc['binary_sha256']!=fingerprint:
            raise ValueError('Duplicate engine or fingerprint mismatch')
        rows={}
        for item in doc['entries']:
            request,entry=item['requested'],item['entry']
            if type(request) is not int or request not in expected or request in rows:
                raise ValueError('Unexpected or duplicate request')
            if entry is not None and (type(entry) is not int or not 0<=entry<2**32):
                raise ValueError('Invalid entry')
            rows[request]=entry
        by_engine[name]=rows
    result=[]
    for request in sorted(expected):
        votes={name:rows.get(request) for name,rows in sorted(by_engine.items())}
        known={v for v in votes.values() if v is not None}
        span=containing_range(ranges,request)
        unwind=('missing' if span is None else 'exact_start' if int(span['start_rva'],16)==request else 'interior')
        if len(known)>1:
            status='conflicting_entries'
        elif not known:
            status='unobserved'
        elif request not in known:
            status='different_entry'
        elif sum(v==request for v in votes.values())>1:
            status='corroborated_entry'
        else:
            status='single_entry'
        result.append({'requested_rva':hex(request),'unwind_status':unwind,'status':status,
                       'entries':{name:None if v is None else hex(v) for name,v in votes.items()},
                       'unwind_hint':span})
    return {'binary_sha256':fingerprint,'entries':result,
            'review_count':sum(x['status'] in ('conflicting_entries','different_entry') or x['unwind_status']=='interior' for x in result),
            'note':'Unwind extents are hints. Missing unwind or analyzer coverage is not a contradiction.'}
