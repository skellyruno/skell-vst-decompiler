"""Bounded stratified corpus review; no semantic labels or binary execution."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .shared_code import scan_modules
from .pe import PE
from .disasm import disassemble
from .function_roles import role_evidence


def select_regions(regions, frequencies, module_count, anchors=()):
    selected={}
    for bucket in sorted({1,module_count}):
        subset=[x for x in regions if frequencies[x[2]]==bucket]
        n=min(2,len(subset))
        for j in range(n):
            a,b,h=subset[(2*j+1)*len(subset)//(2*n)]
            selected[(a,b)]=(a,b,h,'stratified')
    exact={(a,b):(a,b,h) for a,b,h in regions}
    for a,b in anchors:
        if (a,b) not in exact:raise ValueError('Anchor not an exact indexed scope')
        selected[(a,b)]=(*exact[(a,b)],'prior_anchor')
    return sorted(selected.values())


def review(directory, inventory, focus=()):
    if len(focus)>128:raise ValueError('Too many focus scopes')
    root=Path(directory);index=scan_modules(root,inventory)
    modules=index['modules'];frequencies=index['frequencies'];rows=[]
    anchors={m['name']:[] for m in modules.values()}
    for f in focus:
        name=f['module']
        if name not in inventory or f['source_sha256']!=inventory[name]['sha256']:
            raise ValueError('Focus source mismatch')
        anchors[name].append((int(f['covering_start_rva'],16),int(f['covering_end_rva_exclusive'],16)))
    for i,m in modules.items():
        pe=PE(root/m['name'])
        if pe.sha256!=m['sha256']:raise ValueError('Source changed')
        for a,b,h,kind in select_regions(index['regions'][i],frequencies,len(modules),anchors[m['name']]):
            roles=[role_evidence(disassemble(pe,a,b-a,t))['role'] for t in ('objdump','llvm-objdump')]
            rows.append({'module':m['name'],'binary_sha256':pe.sha256,'start_rva':hex(a),'end_rva_exclusive':hex(b),
                         'region_sha256':h,'frequency':frequencies[h],'selection':kind,'gnu':roles[0],'llvm':roles[1],
                         'role':roles[0] if roles[0]==roles[1] else 'UNRESOLVED'})
        if PE(root/m['name']).sha256!=pe.sha256:raise ValueError('Source changed during review')
    counts=Counter((r['selection'],r['frequency'],r['role']) for r in rows)
    return {'type':'stratified_role_evidence','modules':len(modules),'eligible_regions':index['report']['total_scoped_regions'],
            'scanned_regions':len(rows),'decoder_agreements':sum(r['gnu']==r['llvm'] for r in rows),
            'counts':[dict(selection=k[0],frequency=k[1],role=k[2],count=v) for k,v in sorted(counts.items())],
            'rows':rows,'limits':'Deterministic sample and exact supplied anchors, not representative accuracy. Shared DSP and unique utilities remain possible.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');p.add_argument('--inventory',required=True,type=Path);p.add_argument('--focus',type=Path);a=p.parse_args()
    for f in (a.inventory,a.focus):
        if f and f.stat().st_size>256*1024:raise ValueError('Manifest exceeds bounds')
    doc=json.loads(a.inventory.read_text());items=doc['inventory']
    inventory={r['name']:{'size':r['size'],'sha256':r['sha256']} for r in items}
    if len(inventory)!=len(items):raise ValueError('Duplicate inventory name')
    print(json.dumps(review(a.directory,inventory,json.loads(a.focus.read_text()) if a.focus else []),indent=2))

if __name__=='__main__':main()
