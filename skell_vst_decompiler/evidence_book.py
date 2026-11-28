"""Build a consolidated, fingerprint-scoped equation and call-site research book.

Evidence records may overlap; this is not a decompilation or completeness estimate.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from .research_index import records


def build(rows):
    groups=defaultdict(list)
    for row in rows:
        groups[(str(row['source']),row['binary_sha256'])].append(row)
    result=[]
    for (source,sha), items in sorted(groups.items()):
        entries=[]
        for item in sorted(items,key=lambda r:(int(r['region']['start_rva'],16),r['report'],r['region']['id'])):
            region=item['region']
            edges=[]
            for call in region.get('direct_calls',[]):
                if not isinstance(call,dict) or not all(k in call for k in ('site_rva','target_rva')):
                    continue
                site,target=(int(call[k],16) for k in ('site_rva','target_rva'))
                if not int(region['start_rva'],16)<=site<int(region['end_rva_exclusive'],16):
                    continue
                matches=[f"{i['report']}::{i['region']['id']}" for i in items
                         if int(i['region']['start_rva'],16)<=target<int(i['region']['end_rva_exclusive'],16)]
                edges.append({'site_rva':hex(site),'target_rva':hex(target),'covering_evidence':sorted(matches)})
            entries.append({'id':region['id'],'title':region['title'],'report':item['report'],
                            'start_rva':region['start_rva'],'end_rva_exclusive':region['end_rva_exclusive'],
                            'equation':region['equation'],'confidence':region.get('confidence','candidate / confidence not explicitly recorded'),
                            'direct_calls':sorted(edges,key=lambda e:(int(e['site_rva'],16),int(e['target_rva'],16)))})
        result.append({'source':source,'binary_sha256':sha,'region_count':len(entries),'entries':entries})
    return {'schema_version':1,'region_count':sum(g['region_count'] for g in result), 'binaries':result,
            'limits':'Overlapping local evidence, not an algorithm-completeness count. Calls are static decoded references, not proven runtime edges. Unmatched targets are unresolved in this catalog, not necessarily unknown functions. No vendor implementation or raw coefficient arrays.'}


def markdown(book):
    lines=['# Skell DSP equation and code-location atlas','',book['limits'],'',f"**{book['region_count']} evidence records across {len(book['binaries'])} exact binary fingerprints.**",'']
    for group in book['binaries']:
        lines += [f"## {group['source']}",'',f"SHA-256: `{group['binary_sha256']}` — {group['region_count']} records.",'']
        for e in group['entries']:
            lines += [f"### {e['title']}",'',f"- **RVA:** `{e['start_rva']}–{e['end_rva_exclusive']}` (end exclusive)",f"- **Evidence:** `{e['report']}::{e['id']}`",f"- **Confidence:** {e['confidence']}",'',e['equation'],'']
            if e['direct_calls']:
                lines += ['Static direct call references:', '']
                for c in e['direct_calls']:
                    links=', '.join(f'`{x}`' for x in c['covering_evidence']) or 'not covered in catalog'
                    lines.append(f"- `{c['site_rva']}` → `{c['target_rva']}`: {links}")
                lines.append('')
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reports',type=Path);p.add_argument('--format',choices=['json','markdown'],default='markdown');a=p.parse_args()
    book=build(records(a.reports.glob('*.json')))
    print(markdown(book) if a.format=='markdown' else json.dumps(book,indent=2,allow_nan=False),end='\n')

if __name__=='__main__':main()
