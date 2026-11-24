"""Fingerprint-aware search across evidence reports, with bounded Ghidra targets."""
import argparse
import json
from pathlib import Path
import re

SHA = re.compile(r'[0-9a-f]{64}\Z')


def records(paths):
    result = []
    for path in sorted(set(map(Path, paths))):
        if path.stat().st_size > 8_000_000:
            raise ValueError(f'Oversized evidence report: {path.name}')
        data = json.loads(path.read_text(encoding='utf-8'))
        for report in data if isinstance(data, list) else [data]:
            if not isinstance(report, dict) or report.get('schema_version') != 1 or 'regions' not in report:
                continue  # Legacy inventories and WAV metrics are not equation records.
            sha = report.get('binary_sha256')
            if not isinstance(sha, str) or not SHA.fullmatch(sha):
                raise ValueError(f'Invalid binary fingerprint: {path.name}')
            if not isinstance(report['regions'], list):
                raise ValueError(f'Invalid regions: {path.name}')
            for region in report['regions']:
                start, end = (int(region[k], 16) for k in ('start_rva','end_rva_exclusive'))
                if not 0 <= start < end <= 2**32:
                    raise ValueError(f'Invalid code range: {path.name}')
                result.append({'report': path.name, 'source': report.get('source'),
                               'binary_sha256': sha, 'region': region})
    return result


def query(rows, terms='', fingerprint=None, address=None):
    if fingerprint is not None and not SHA.fullmatch(fingerprint):
        raise ValueError('Fingerprint must be a lowercase SHA-256')
    if address is not None and not 0 <= address < 2**32:
        raise ValueError('Invalid RVA')
    words = terms.casefold().split()
    found = []
    for item in rows:
        if fingerprint is not None and item['binary_sha256'] != fingerprint:
            continue
        r = item['region']
        if address is not None and not int(r['start_rva'],16) <= address < int(r['end_rva_exclusive'],16):
            continue
        hay = json.dumps(item, ensure_ascii=False).casefold()
        if all(w in hay for w in words):
            found.append(item)
    return found


def target_rvas(rows, fingerprint):
    # Keep the exact evidence addresses rather than equating unwind ranges with functions.
    return sorted({int(r['region']['start_rva'],16) for r in query(rows,fingerprint=fingerprint)})


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('query', nargs='?', default='')
    p.add_argument('--sha256')
    p.add_argument('--rva', type=lambda s:int(s,0))
    a=p.parse_args(argv)
    found=query(records(a.directory.glob('*.json')),a.query,a.sha256,a.rva)
    print(json.dumps({'count':len(found),'matches':found},indent=2,allow_nan=False))
    return 0

if __name__=='__main__':raise SystemExit(main())
