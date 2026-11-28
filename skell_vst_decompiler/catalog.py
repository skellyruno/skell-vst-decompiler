"""Search previously verified evidence without reopening a vendor binary."""
import argparse
import json
from pathlib import Path


def search(report, query=''):
    if report.get('schema_version') != 1 or not isinstance(report.get('regions'), list):
        raise ValueError('Unsupported equation catalog')
    query=query.strip().casefold()
    rva=None
    if query.startswith('0x'):
        try: rva=int(query,16)
        except ValueError: raise ValueError('Invalid hexadecimal RVA') from None
    results=[]
    for region in report['regions']:
        if rva is not None:
            match=int(region['start_rva'],16)<=rva<int(region['end_rva_exclusive'],16)
        else:
            terms=query.split()
            match=all(term in json.dumps(region,ensure_ascii=False).casefold() for term in terms)
        if match: results.append(region)
    return {'binary_sha256':report.get('binary_sha256'),'source':report.get('source'),'query':query,'matches':results,'limits':report.get('limits',[])}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report',type=Path)
    p.add_argument('query',nargs='?',default='')
    a=p.parse_args(argv)
    print(json.dumps(search(json.loads(a.report.read_text(encoding='utf-8')),a.query),indent=2,allow_nan=False))
    return 0

if __name__=='__main__': raise SystemExit(main())
