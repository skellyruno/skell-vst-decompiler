"""Read-only x64 chained-unwind metadata validation and aggregate grouping.

Only metadata relationships are reported. No code, handler data or function
implementation is exported. Chained records do not prove runtime reachability.
"""
from collections import Counter
import struct
from .extent_coverage import inspect


def summarize(data):
    inventory=inspect(data)
    if inventory['bits']!=64:return {'binary_sha256':inventory['binary_sha256'],'applicable':False}
    p=struct.unpack_from('<I',data,60)[0];o=p+24
    n=struct.unpack_from('<H',data,p+6)[0];opt=struct.unpack_from('<H',data,p+20)[0]
    dirs=struct.unpack_from('<I',data,o+108)[0]
    sections=[]
    for i in range(n):
        _,_,rva,size,off,*_=struct.unpack_from('<8sIIIIIIHHI',data,o+opt+40*i)
        if size:sections.append((rva,rva+size,off))
    def read(rva,size):
        a=[(lo,off) for lo,hi,off in sections if lo<=rva and rva+size<=hi]
        if len(a)!=1 or size<=0:raise ValueError('Unbacked unwind metadata')
        lo,off=a[0];return data[off+rva-lo:off+rva-lo+size]
    exp,size=struct.unpack_from('<II',data,o+136) if dirs>=4 else (0,0)
    records=set(struct.iter_unpack('<III',read(exp,size))) if exp else set()
    links={};unsupported=0;invalid=0
    for rec in records:
        _,_,uw=rec;h=read(uw,4);version=h[0]&7;flags=h[0]>>3
        if not flags&4:continue
        if version!=1:unsupported+=1;continue
        if flags!=4:invalid+=1;continue
        # UNWIND_CODE entries are two bytes, aligned to an even slot count.
        padded=(h[2]+1)&~1
        try:
            payload=read(uw,4+2*padded+12)
            parent=struct.unpack_from('<III',payload,4+2*padded)
        except (ValueError,struct.error):invalid+=1;continue
        links[rec]=parent
    outcomes=Counter();depths=Counter();roots=Counter()
    for rec in links:
        cur=rec;seen=set();depth=0
        while cur in links:
            if cur in seen:outcomes['cycle']+=1;break
            if depth>=128:outcomes['depth_limit']+=1;break
            seen.add(cur);cur=links[cur];depth+=1
            if cur not in records:outcomes['parent_not_in_table']+=1;break
        else:
            header=read(cur[2],4)
            if header[0]&7!=1 or (header[0]>>3)&4:outcomes['unresolved_terminal']+=1
            else:outcomes['resolved_table_root']+=1;depths[depth]+=1;roots[cur]+=1
    return {'binary_sha256':inventory['binary_sha256'],'applicable':True,'runtime_records':len(records),'chain_flag_records':sum(v for k,v in inventory['unwind_flags'].items() if k&4),'parsed_chain_records':len(links),'unsupported_version':unsupported,'invalid_chain_metadata':invalid,'outcomes':dict(outcomes),'resolved_depth_histogram':dict(depths),'distinct_resolved_roots':len(roots),'largest_chain_group':max(roots.values(),default=0),'note':'Exact table membership and terminal metadata only; no unwind opcode or runtime behavior validation.'}
