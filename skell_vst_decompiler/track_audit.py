"""Independent exact-range evidence audit, inspired by reproducible comparison workflows."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from .research_index import records,SHA

TRACKS = {
    'TVB': {'cefaa0c08642093832b0cf9cd93fea791ebd8146dae395d310a2624610a8fff9'},
    'VMR': {'1cf796db09bc6ce3455d3fa3506614fa990374fc2f2642ff8fc9c40e626dfbf2',
            '6b365ee15dbb94efb9d97b76923445f4ad4f3740194e21363cd9ffbe8df8d573',
            '2509a6f3480481feb15a0fde97abcb4acccfc6fc936f55f5e8c88b7c98edcd26'},
    'Evo': {'278d03b4a88fe6ef59b48e5c1f70bc921b3ae530ea672879ef2ae21f0ce873d5'},
}


def compare_ranges(rows, fingerprints):
    groups=defaultdict(list)
    seen=set()
    for row in rows:
        sha=row['binary_sha256']
        if sha not in fingerprints:
            continue
        reg=row['region']
        start,end=(int(reg[k],16) for k in ('start_rva','end_rva_exclusive'))
        if not 0<=start<end<=2**32:
            raise ValueError('Invalid range')
        key=(row['report'],sha,reg['id'])
        if key in seen:
            raise ValueError('Duplicate report evidence identity')
        seen.add(key)
        digest=reg.get('sha256')
        if digest is not None and (not isinstance(digest,str) or not SHA.fullmatch(digest)):
            raise ValueError('Invalid recorded region digest')
        groups[(sha,start,end)].append((row['report']+'::'+reg['id'],digest))
    conflicts=[]
    counts=defaultdict(int)
    for (sha,start,end),claims in sorted(groups.items()):
        counts['region_records']+=len(claims)
        counts['distinct_ranges']+=1
        digests={digest for _,digest in claims if digest is not None}
        counts['records_with_region_digest']+=sum(digest is not None for _,digest in claims)
        counts['records_without_region_digest']+=sum(digest is None for _,digest in claims)
        counts['repeated_exact_ranges']+=len(claims)>1
        if len(digests)>1:
            conflicts.append({'binary_sha256':sha,'start_rva':hex(start),'end_rva_exclusive':hex(end),
                              'recorded_digest_disagreement':True,
                              'observations':[{'reference':ref,'recorded_sha256':digest} for ref,digest in claims]})
    return {**{k:counts[k] for k in ('region_records','distinct_ranges','records_with_region_digest',
             'records_without_region_digest','repeated_exact_ranges')},
             'candidate_digest_conflicts':conflicts,
             'note':'Same fingerprint and exact range only. Digest semantics require review; no byte revalidation or DSP equivalence.'}


def audit_tracks(directory):
    root=Path(directory)
    rows=records(root.glob('*.json'))
    evo=json.loads((root/'evo_legacy_metadata_2026-11-24.json').read_text(encoding='utf-8'))
    if evo['binary_sha256'] not in TRACKS['Evo'] or evo['architecture']!='x86':
        raise ValueError('Legacy source metadata mismatch')
    output={name:compare_ranges(rows,hashes) for name,hashes in TRACKS.items()}
    output['Evo']['metadata_only']=True
    output['Evo']['public_export_names']=evo['public_vst_entry_names']
    return {'schema_version':1,'report_kind':'three_track_exact_range_audit',
            'tracks':output,'note':'Archived records only; absence of repeated ranges is not independent corroboration.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reports',type=Path)
    print(json.dumps(audit_tracks(p.parse_args().reports),indent=2,sort_keys=True))
