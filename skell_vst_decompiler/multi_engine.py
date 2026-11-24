"""Reconcile like-for-like static evidence from multiple analyzers.

Function entries and call relationships are separate claims. An inventory
count or an enclosing function does not vote for an exact function entry.
"""


def reconcile_observations(fingerprint, documents):
    if not documents:
        raise ValueError('No engine documents')
    engines = set()
    claims = {}
    for doc in documents:
        name = doc['engine']
        if not isinstance(name, str) or not name or name in engines:
            raise ValueError('Invalid or duplicate engine')
        engines.add(name)
        if doc['binary_sha256'] != fingerprint:
            raise ValueError('Engine source fingerprint mismatch')
        seen = set()
        for row in doc['observations']:
            kind, subject, value = row['kind'], row['subject'], row['value']
            if kind not in ('function_entry', 'function_call') or type(subject) is not int or type(value) is not int or not 0 <= subject < 2**32 or not 0 <= value < 2**32:
                raise ValueError('Invalid observation')
            # Multiple callees are legitimate; compare positive observations
            # for each distinct edge, not an exclusive destination per caller.
            key = (kind, subject, value)
            if key in seen:
                raise ValueError('Duplicate observation')
            seen.add(key)
            claims.setdefault(key, set()).add(name)
    rows = []
    for (kind, subject, value), support in sorted(claims.items()):
        rows.append({'kind':kind, 'subject_rva':hex(subject), 'value_rva':hex(value),
                     'supporting_engines':sorted(support),
                     'status':'corroborated_static' if len(support)>1 else 'single_observation'})
    return {'binary_sha256':fingerprint, 'engines':sorted(engines), 'claims':rows,
            'note':'Positive evidence only. Missing claims are not negative votes; function-level edges do not resolve call sites.'}
