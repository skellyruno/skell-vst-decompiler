"""Exact-build cross-module function fingerprints for read-only research triage.

Identical hash-labeled bounded unwind ranges can indicate shared code. They are
NOT proof of utility behavior, identical source, or an algorithm's absence.
Original module binaries are never executed, copied to reports, or modified.
"""
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path

from .pe import PE
from .navigation import runtime_ranges

MAX_MODULES = 64
MAX_BYTES_PER_MODULE = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MIN_REGION = 32
MAX_REGION = 4096


def _files(directory, inventory=None):
    folder = Path(directory)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError('Expected a real local module directory')
    paths = sorted(folder.glob('*.epl'), key=lambda x: x.name.casefold())
    if not 2 <= len(paths) <= MAX_MODULES:
        raise ValueError('Choose 2..64 adjacent EPL modules')
    if len({p.name.casefold() for p in paths}) != len(paths):
        raise ValueError('Ambiguous module file names')
    total = 0
    for p in paths:
        if p.is_symlink() or not p.is_file():
            raise ValueError('Symlink or nonfile module is unsupported')
        size = p.stat().st_size
        if not 0 < size <= MAX_BYTES_PER_MODULE:
            raise ValueError('Individual module exceeds bounds')
        total += size
    if total > MAX_TOTAL_BYTES:
        raise ValueError('Corpus exceeds total 1 GiB bound')
    if inventory is not None:
        if not isinstance(inventory, dict) or set(inventory) != {p.name for p in paths}:
            raise ValueError('Inventory and module names differ')
        for name, row in inventory.items():
            if (not isinstance(row, dict) or type(row.get('size')) is not int or
                    type(row.get('sha256')) is not str or len(row['sha256']) != 64):
                raise ValueError('Invalid expected module inventory')
            if (folder/name).stat().st_size != row['size']:
                raise ValueError('Module size differs from expected manifest')
    return paths


def scan_modules(directory, inventory=None, min_region=MIN_REGION, max_region=MAX_REGION):
    """Index exact non-overlapping unwind-covered byte spans by source module.

    Returns a private ephemeral index plus a portable summary. It deliberately
    does not scan arbitrary code in gaps without unwind records.
    """
    if not all(type(n) is int for n in (min_region, max_region)) or not 16 <= min_region <= max_region <= 32768:
        raise ValueError('Invalid bounded region lengths')
    paths = _files(directory, inventory)
    by_digest = defaultdict(set)
    modules = {}
    all_regions = {}
    for name_id, path in enumerate(paths):
        pe = PE(path)
        if inventory is not None and pe.sha256 != inventory[path.name]['sha256']:
            raise ValueError(f'SHA-256 differs from expected manifest: {path.name}')
        scoped = []
        entries = runtime_ranges(pe)
        for start, end, _ in entries:
            n = end-start
            if min_region <= n <= max_region:
                raw = pe.at_rva(start,n,executable=True)
                sha = hashlib.sha256(raw).hexdigest()
                by_digest[sha].add(name_id)
                scoped.append((start,end,sha))
        # Make sure the source remains unchanged during the scan.
        if hashlib.sha256(path.read_bytes()).hexdigest() != pe.sha256:
            raise ValueError('Module changed while being scanned')
        modules[name_id] = {'name':path.name,'sha256':pe.sha256,'bytes':len(pe.data),
                            'runtime_records':len(entries),'scoped_regions':len(scoped)}
        all_regions[name_id] = scoped
    frequencies = {sha:len(ids) for sha, ids in by_digest.items()}
    summary=[]
    for i,m in modules.items():
        hist=Counter(frequencies[sha] for _,_,sha in all_regions[i])
        total=sum(hist.values())
        shared_10=sum(v for k,v in hist.items() if k >= 10)
        shared_bytes_10=sum(end-start for start,end,sha in all_regions[i] if frequencies[sha] >= 10)
        summary.append({**m,'regions_matching_at_least_10_modules':shared_10,
            'matched_ratio':round(shared_10 / total, 6) if total else 0,
            'matching_region_bytes':shared_bytes_10,
            'frequency_histogram':{str(k):v for k,v in sorted(hist.items())}})
    signatures={i:{sha for _,_,sha in all_regions[i]} for i in modules}
    pairs=[]
    for i in modules:
        for j in range(i+1,len(modules)):
            count=len(signatures[i] & signatures[j])
            union=len(signatures[i] | signatures[j])
            pairs.append({'left':modules[i]['name'],'right':modules[j]['name'],
                          'shared_distinct_regions':count,
                          'jaccard':round(count/union,6) if union else 0})
    pairs.sort(key=lambda row:(-row['jaccard'],-row['shared_distinct_regions'],row['left'],row['right']))
    report = {'schema_version':1,'type':'bounded_cross_module_code_frequency',
        'module_count':len(paths),'region_limits':[min_region,max_region],
        'total_scoped_regions':sum(x['scoped_regions'] for x in summary),
        'distinct_region_fingerprints':len(by_digest),
        'fingerprints_in_all_modules':sum(v == len(paths) for v in frequencies.values()),
        'fingerprints_in_at_least_10_modules':sum(v >= 10 for v in frequencies.values()),
        'regions_matching_at_least_10_modules':sum(x['regions_matching_at_least_10_modules'] for x in summary),
        'modules':summary,
        'most_related_pairs':pairs[:16],
        'limits':'Exact SHA-256 byte matches over complete x64 unwind ranges only. Relative calls and relocations may make equivalent functions differ; shared DSP is possible. No function labels, runtime activation or sound measurements are inferred.'}
    # Keep private region-level hashes in memory; portable summary excludes them.
    return {'report':report,'regions':all_regions,'frequencies':frequencies,'modules':modules}


def annotate(index, file_sha256, candidates):
    """Attach frequency, keeping the existing candidate order and confidence."""
    if not isinstance(candidates,list) or len(candidates)>128:
        raise ValueError('Expected bounded candidate list')
    matches=[i for i,m in index['modules'].items() if m['sha256']==file_sha256]
    if len(matches)!=1:
        raise ValueError('Target source SHA-256 is not unique within the corpus')
    lookup={(start,end):digest for start,end,digest in index['regions'][matches[0]]}
    result=[]
    for row in candidates:
        start=int(row['start_rva'],16);end=int(row['end_rva_exclusive'],16)
        sha=lookup.get((start,end))
        row=dict(row)
        row['cross_module_evidence'] = (
            {'status':'EXACT_FUNCTION_SCOPE','module_frequency':index['frequencies'][sha],
             'corpus_modules':len(index['modules']),
             'investigation_hint':'shared_code_candidate' if index['frequencies'][sha]>=10 else 'compare_module_specific_path'}
            if sha else {'status':'UNRESOLVED_SCOPE','note':'Candidate range is not a complete indexed unwind region'})
        result.append(row)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--inventory',type=Path,help='Exact source name/size/SHA inventory JSON')
    a=parser.parse_args()
    inventory=None
    if a.inventory:
        if a.inventory.stat().st_size>256*1024:
            raise ValueError('Inventory too large')
        document=json.loads(a.inventory.read_text())
        rows=document['inventory']
        if not isinstance(rows,list) or len(rows)>MAX_MODULES:
            raise ValueError('Invalid manifest rows')
        inventory={x['name']:{'size':x['size'],'sha256':x['sha256']} for x in rows}
        if len(inventory)!=len(rows):raise ValueError('Duplicate module names in manifest')
    print(json.dumps(scan_modules(a.directory,inventory)['report'],indent=2))


if __name__=='__main__':main()
