"""Cross-report evidence audit, never an algorithm-completeness estimate.

Consumes existing static-analysis JSON only. No target execution, vendor code
export, inferred runtime call graph, or source reconstruction.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from .research_index import records, SHA


def rva(value):
    if not isinstance(value, str) or not value.startswith('0x'):
        raise ValueError('Expected hex RVA')
    n = int(value, 16)
    if not 0 <= n < 2**32:
        raise ValueError('RVA outside PE32+ image range')
    return n


def audit(rows, summary):
    groups = defaultdict(list)
    for row in rows:
        if not SHA.fullmatch(row['binary_sha256']):
            raise ValueError('Invalid source fingerprint')
        groups[row['binary_sha256']].append(row)
    if summary.get('schema_version') != 1:
        raise ValueError('Unsupported class summary')
    binaries = {}
    for binary in summary['binaries']:
        sha = binary['binary_sha256']
        if not SHA.fullmatch(sha) or sha in binaries:
            raise ValueError('Invalid or repeated class source fingerprint')
        if binary['selected_plan']['binary_sha256'] != sha:
            raise ValueError('Class plan/source fingerprint mismatch')
        binaries[sha] = binary
    results = []
    for sha in sorted(groups.keys() | binaries.keys()):
        items = groups[sha]
        spans = []
        edges = defaultdict(lambda: defaultdict(set))
        seen_ids = set()
        for item in items:
            reg = item['region']
            start, end = rva(reg['start_rva']), int(reg['end_rva_exclusive'], 16)
            if not start < end <= 2**32:
                raise ValueError('Invalid evidence interval')
            key = item['report'] + '::' + reg['id']
            if key in seen_ids:
                raise ValueError('Repeated evidence identity: ' + key)
            seen_ids.add(key)
            spans.append((start, end, key))
            for call in reg.get('direct_calls', []):
                if not isinstance(call, dict) or not {'site_rva', 'target_rva'} <= call.keys():
                    continue
                site, target = rva(call['site_rva']), rva(call['target_rva'])
                if not start <= site < end:
                    raise ValueError('Call site outside evidence interval: ' + key)
                edges[site][target].add(key)

        def at(address):
            return sorted(key for start, end, key in spans if start <= address < end)

        targets = defaultdict(set)
        conflicts = []
        for site, dests in sorted(edges.items()):
            if len(dests) > 1:
                conflicts.append({'site_rva': hex(site),
                                  'targets': {hex(t): sorted(refs) for t, refs in sorted(dests.items())}})
                continue
            for target in dests:
                targets[target].add(site)
        uncovered = [
            {'target_rva': hex(t), 'distinct_call_sites': len(sites),
             'site_rvas': [hex(s) for s in sorted(sites)]}
            for t, sites in sorted(targets.items(), key=lambda x: (-len(x[1]), x[0]))
            if not at(t)
        ]
        slots = []
        binary = binaries.get(sha)
        if binary:
            plan = {}
            for target in binary['selected_plan']['targets']:
                address = rva(target['requested_rva'])
                if address in plan:
                    raise ValueError('Repeated class-plan address')
                plan[address] = target.get('unwind_region')
            selected = set()
            for cls in binary['classes']:
                for table in cls['vtables']:
                    for slot, address_text in table['selected_method_rvas'].items():
                        address = rva(address_text)
                        if address not in plan:
                            raise ValueError('Selected method missing from plan')
                        selected.add(address)
                        region = plan[address]
                        overlap = []
                        if region is not None:
                            lo, hi = rva(region['start_rva']), int(region['end_rva_exclusive'], 16)
                            if not lo <= address < hi <= 2**32:
                                raise ValueError('Invalid method unwind interval')
                            overlap = sorted(key for start, end, key in spans if start < hi and lo < end)
                        exact = at(address)
                        slots.append({'class': cls['type'], 'table_rva': table['vtable_rva'],
                                      'subobject_offset': table['subobject_offset'], 'slot': int(slot),
                                      'method_rva': hex(address), 'entry_evidence': exact,
                                      'unwind_overlap_evidence': overlap,
                                      'status': 'entry_covered' if exact else
                                      'unwind_overlap_only' if overlap else 'no_local_region'})
            if selected != set(plan):
                raise ValueError('Class plan and selected methods disagree')
        results.append({'binary_sha256': sha,
                        'source': binary['binary'] if binary else sorted({str(x['source']) for x in items})[0],
                        'region_count': len(spans), 'distinct_call_sites': len(edges),
                        'conflicting_call_sites': conflicts, 'uncovered_targets': uncovered,
                        'selected_methods': slots})
    return {'schema_version': 1, 'binaries': results,
            'note': 'Address coverage of existing reports only. Uncovered targets may be imports, thunks or utility functions. Unwind overlap does not establish function identity or runtime routing.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reports', type=Path)
    a = p.parse_args(argv)
    summary = a.reports / 'class_navigation_summary.json'
    if summary.stat().st_size > 8_000_000:
        raise ValueError('Oversized class summary')
    result = audit(records(a.reports.glob('*.json')), json.loads(summary.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
