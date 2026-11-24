"""Offline, fingerprint-scoped reconciliation of archived navigation evidence.
No binary execution, decompilation, or automatic confidence promotion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

VERSION = 1
SHA = re.compile(r'[0-9a-f]{64}\Z')
MAX_BYTES = 8_000_000


def fingerprint(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError('Invalid SHA-256')
    return value


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', value):
        raise ValueError('Invalid RVA')
    number = int(value, 16)
    if not 0 <= number <= 2**32:
        raise ValueError('RVA out of range')
    return number


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def load(path):
    with Path(path).open('rb') as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Oversized input')
    return json.loads(raw), digest(raw)


def reconcile(snapshot, inputs):
    """Inputs are (basename, report document, exact file SHA-256) tuples."""
    if snapshot.get('schema_version') != 1:
        raise ValueError('Unsupported snapshot')
    regions = {}
    manifest = {}
    for name, document, sha in inputs:
        if Path(name).name != name or name in manifest:
            raise ValueError('Repeated or invalid report name')
        manifest[name] = fingerprint(sha)
        for report in document if isinstance(document, list) else [document]:
            if not isinstance(report, dict) or report.get('schema_version') != 1 or 'regions' not in report:
                continue
            source = fingerprint(report['binary_sha256'])
            for region in report['regions']:
                lo, hi = address(region['start_rva']), address(region['end_rva_exclusive'])
                key = (source, name + '::' + region['id'])
                if lo >= hi or key in regions:
                    raise ValueError('Invalid or repeated evidence interval')
                regions[key] = (lo, hi)
    checks = []
    seen = set()
    for binary in snapshot['binaries']:
        sha = fingerprint(binary['binary_sha256'])
        for wrapper in binary['wrappers']:
            rva = address(wrapper['wrapper_rva'])
            key = (sha, rva)
            if key in seen:
                raise ValueError('Repeated wrapper')
            seen.add(key)
            slots = wrapper['sampled_slots']
            if [s['slot'] for s in slots] != list(range(6)) or slots[4]['target_rva'] != slots[5]['target_rva'] or slots[4]['unwind_region'] != slots[5]['unwind_region']:
                raise ValueError('Inconsistent sampled slots')
            span = slots[4]['unwind_region']
            lo, hi = address(span['start_rva']), address(span['end_rva_exclusive'])
            if lo != address(slots[4]['target_rva']) or hi <= lo or span['bytes'] != hi - lo:
                raise ValueError('Inconsistent target span')
            expected = set(wrapper['slot45_atlas_overlap'])
            observed = {name for (source, name), (start, end) in regions.items() if source == sha and max(lo, start) < min(hi, end)}
            missing, added = sorted(expected-observed), sorted(observed-expected)
            status = 'consistent' if not (missing or added) else 'review_required'
            checks.append({'binary':binary['binary'], 'wrapper_rva':hex(rva), 'status':status,
                           'missing_references':missing, 'additional_references':added,
                           'overlap_count':len(observed)})
    identity = {'version':VERSION, 'snapshot_sha256':digest(canonical(snapshot)), 'reports':manifest}
    return {'schema_version':VERSION, 'input_key':digest(canonical(identity)), 'inputs':identity,
            'region_count':len(regions), 'checks':sorted(checks,key=lambda c:(c['binary'],c['wrapper_rva'])),
            'note':'Consistency only; no runtime or algorithm-equivalence claim.'}


def revenant_metadata(document, expected_sha):
    """Read safe metadata from an offline Revenant report.json (never invoke it)."""
    if fingerprint(document['sha256']) != fingerprint(expected_sha):
        raise ValueError('External report/source fingerprint mismatch')
    count = document['function_count']
    if type(count) is not int or count < 0:
        raise ValueError('Invalid external function count')
    completed, failed = document['stages_completed'], document['stages_failed']
    if not isinstance(completed,list) or not isinstance(failed,dict) or not all(isinstance(s,str) for s in completed) or set(completed) & set(failed):
        raise ValueError('Invalid external stage status')
    return {'engine':'revenant','sha256':expected_sha,'function_count':count,
            'completed_stage_count':len(set(completed)), 'failed_stage_count':len(failed),
            'status':'external_unverified', 'note':'Imported metadata only; counts are not equivalent to atlas regions.'}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reports',type=Path)
    p.add_argument('--revenant',type=Path)
    p.add_argument('--sha256')
    a = p.parse_args(argv)
    snapshot, raw_sha = load(a.reports/'vmr_variant_navigation.json')
    inputs = [(path.name,*load(path)) for path in sorted(a.reports.glob('*.json')) if path.name != 'vmr_variant_navigation.json']
    result = reconcile(snapshot, inputs)
    result['snapshot_file_sha256'] = raw_sha
    if a.revenant:
        if not a.sha256:
            p.error('--revenant requires --sha256')
        external, external_sha = load(a.revenant)
        result['external'] = revenant_metadata(external, a.sha256)
        result['external']['report_sha256'] = external_sha
    print(json.dumps(result,indent=2,allow_nan=False))
    return int(any(c['status'] != 'consistent' for c in result['checks']))


if __name__ == '__main__':
    raise SystemExit(main())
