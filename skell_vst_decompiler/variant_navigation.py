"""Compare selected VMR dispatch wrappers using existing exact-build class plans.
Only metadata and bounded static references; no execution or runtime routing claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from .pe import PE
from .navigation import runtime_ranges, containing_range
from .disasm import disassemble, direct_calls
from .research_index import records


def overlaps(rows, sha, start, end):
    return sorted({r['report']+'::'+r['region']['id'] for r in rows
                   if r['binary_sha256']==sha and int(r['region']['start_rva'],16)<end
                   and start<int(r['region']['end_rva_exclusive'],16)})


def inspect(pe, binary, rows):
    if pe.sha256!=binary['binary_sha256'] or pe.sha256!=binary['selected_plan']['binary_sha256']:
        raise ValueError('Exact binary fingerprint required')
    ranges=runtime_ranges(pe)
    result=[]
    for item in binary['selected_plan']['targets']:
        start=int(item['requested_rva'],16)
        region=containing_range(ranges,start)
        if region!=item['unwind_region'] or region is None or int(region['start_rva'],16)!=start:
            raise ValueError('Unexpected method metadata')
        n=region['bytes']
        ins=disassemble(pe,start,n)
        tables={int(m.group(1),16)-pe.image_base for i in ins if i.mnemonic=='lea'
                and (m:=re.search(r'\[rip[^\]]*\].*#\s*0x([a-f0-9]+)',i.operands))}
        indexed=[hex(i.address-pe.image_base) for i in ins if i.mnemonic=='call' and re.fullmatch(r'QWORD PTR \[(r15|rsi)\+rdx\*8\]',i.operands)]
        field={'FG-116.epl':'0xd0','FG-2A.epl':'0x190','FG-Stress.epl':'0x360'}[binary['binary']]
        selector=[hex(i.address-pe.image_base) for i in ins if i.mnemonic=='movsxd' and i.operands==f'rdx,DWORD PTR [rax+{field}]']
        if len(tables)!=1 or len(indexed)!=2 or len(selector)!=2:
            raise ValueError('Unexpected indexed dispatch shape')
        table=tables.pop()
        slots=[]
        for slot in range(6):
            target=struct.unpack('<Q',pe.at_rva(table+8*slot,8))[0]-pe.image_base
            pe.at_rva(target,1,executable=True)
            span=containing_range(ranges,target)
            slots.append({'slot':slot,'target_rva':hex(target),'unwind_region':span})
        if slots[4]['target_rva']!=slots[5]['target_rva']:
            raise ValueError('Expected repeated candidate target')
        target=int(slots[4]['target_rva'],16)
        span=slots[4]['unwind_region']
        if span is None or int(span['start_rva'],16)!=target:
            raise ValueError('Expected target unwind start')
        body=disassemble(pe,target,span['bytes'])
        calls=direct_calls(pe,body)
        result.append({'wrapper_rva':hex(start),'wrapper_bytes':n,'wrapper_instructions':len(ins),
                       'wrapper_sha256':hashlib.sha256(pe.at_rva(start,n,executable=True)).hexdigest(),
                       'table_rva':hex(table),'selector_field':field,'selector_read_sites':selector,'indexed_call_sites':indexed,
                       'sampled_slots':slots,'slot45_target_sha256':hashlib.sha256(pe.at_rva(target,span['bytes'],executable=True)).hexdigest(),
                       'slot45_instruction_count':len(body),'slot45_direct_call_count':len(calls),
                       'slot45_unique_direct_targets':len({c['target_rva'] for c in calls}),
                       'slot45_indirect_call_count':sum(i.mnemonic=='call' and not i.operands.startswith('0x') for i in body),
                       'slot45_atlas_overlap':overlaps(rows,pe.sha256,target,int(span['end_rva_exclusive'],16))})
    return {'binary':binary['binary'],'binary_sha256':pe.sha256,'wrappers':sorted(result,key=lambda r:r['wrapper_rva']),
            'limits':'Six sampled slots only; no table extent or runtime selection inferred. Unwind ranges and overlap are navigation evidence, not algorithm identity.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('modules',type=Path)
    p.add_argument('reports',type=Path)
    a=p.parse_args()
    summary=json.loads((a.reports/'class_navigation_summary.json').read_text())
    rows=records(a.reports.glob('*.json'))
    result=[inspect(PE(a.modules/b['binary']),b,rows) for b in summary['binaries'] if b['binary'].lower().endswith('.epl')]
    print(json.dumps({'schema_version':1,'binaries':result},indent=2,allow_nan=False))


if __name__=='__main__':main()
