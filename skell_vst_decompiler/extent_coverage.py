"""Read-only executable extent and unwind metadata coverage, not function recovery.

Reports aggregate byte coverage of half-open ranges. No code bytes, private
symbols, addresses, unwind opcodes or implementation are exported.
"""
from bisect import bisect_right
from collections import Counter
import hashlib
import struct


def union(ranges):
    out=[]
    for lo,hi in sorted(ranges):
        if not 0<=lo<hi<=2**32:
            raise ValueError('Invalid extent')
        if out and lo<=out[-1][1]:
            out[-1]=(out[-1][0],max(hi,out[-1][1]))
        else:out.append((lo,hi))
    return out


def length(ranges):
    return sum(hi-lo for lo,hi in union(ranges))


def intersect(a,b):
    a,b=union(a),union(b);i=j=0;out=[]
    while i<len(a) and j<len(b):
        lo=max(a[i][0],b[j][0]);hi=min(a[i][1],b[j][1])
        if lo<hi:out.append((lo,hi))
        if a[i][1]<b[j][1]:i+=1
        else:j+=1
    return out


def coverage(scopes,records):
    """Compare union coverage and per-scope intersections, not function identity."""
    scopes=list(scopes); records=list(records)
    if len(scopes)>10000 or len(records)>500000:raise ValueError('Extent count bound')
    if any(not 0<=a<b<=2**32 for a,b in scopes+records):raise ValueError('Invalid extent')
    rec=union(records);ends=[b for a,b in rec]; counts=Counter(); covered=0
    for lo,hi in scopes:
        j=bisect_right(ends,lo);n=0
        while j<len(rec) and rec[j][0]<hi:
            a,b=rec[j];n+=max(0,min(hi,b)-max(lo,a));j+=1
        counts['full' if n==hi-lo else 'partial' if n else 'none']+=1;covered+=n
    unique=length(scopes);unique_covered=length(intersect(scopes,rec))
    return {'scope_count':len(scopes),'scope_sum_bytes':sum(b-a for a,b in scopes),
            'unique_scope_bytes':unique,'overlapping_scope_bytes':sum(b-a for a,b in scopes)-unique,
            'sum_covered_bytes':covered,'unique_covered_bytes':unique_covered,
            'unique_uncovered_bytes':unique-unique_covered,'coverage_counts':dict(counts)}


def inspect(data,scopes=()):
    """Parse PE32/PE32+ sections and x64 runtime extents with strict bounds.

    Use min(raw size, virtual size or raw size) as a conservative mapped
    file-backed executable interval; raw padding is reported separately.
    """
    if not isinstance(data,bytes) or not 256<=len(data)<=512*1024*1024 or data[:2]!=b'MZ':raise ValueError('Invalid PE')
    def unpack(fmt,off):
        if off<0 or off+struct.calcsize(fmt)>len(data):raise ValueError('Truncated PE')
        return struct.unpack_from(fmt,data,off)
    p,=unpack('<I',60)
    if p<64 or data[p:p+4]!=b'PE\0\0':raise ValueError('Invalid PE signature')
    machine,n,_,_,_,optsize,_=unpack('<HHIIIHH',p+4);o=p+24
    magic,=unpack('<H',o)
    if (machine,magic)==(0x14c,0x10b):bits=32;fixed=96
    elif (machine,magic)==(0x8664,0x20b):bits=64;fixed=112
    else:raise ValueError('Unsupported PE')
    if not 1<=n<=96 or optsize<fixed or o+optsize+n*40>len(data):raise ValueError('Invalid section table')
    dirs,=unpack('<I',o+fixed-4)
    if dirs>(optsize-fixed)//8:raise ValueError('Truncated directories')
    sections=[];raw_exec=[];mapped_exec=[]
    for i in range(n):
        _,vs,rva,size,off,_,_,_,_,flags=unpack('<8sIIIIIIHHI',o+optsize+40*i)
        if size and (off+size>len(data) or rva+size>2**32):raise ValueError('Invalid raw section')
        if vs and rva+vs>2**32:raise ValueError('Invalid virtual section')
        if size:sections.append((rva,rva+size,off))
        if size and flags&0x20000000:
            raw_exec.append((rva,rva+size));mapped_exec.append((rva,rva+min(size,vs or size)))
    sections.sort();starts=[a for a,b,c in sections]
    if any(b>c for (a,b,_),(c,d,__) in zip(sections,sections[1:])):raise ValueError('Overlapping raw section RVAs')
    def read(rva,n):
        i=bisect_right(starts,rva)-1
        if i<0 or n<=0 or rva+n>sections[i][1]:raise ValueError('Extent not file backed')
        a,b,off=sections[i];return data[off+rva-a:off+rva-a+n]
    records=[];flags=Counter();versions=Counter();unique_headers=set()
    exception_rva,exception_size=unpack('<II',o+fixed+24) if dirs>=4 else (0,0)
    if bits==64 and (exception_rva or exception_size):
        if not exception_rva or not 0<exception_size<=6000000 or exception_size%12:raise ValueError('Invalid exception extent')
        for lo,hi,uw in struct.iter_unpack('<III',read(exception_rva,exception_size)):
            if not lo<hi or not uw or (records and lo<records[-1][1]):raise ValueError('Invalid runtime record')
            records.append((lo,hi));h=read(uw,4)[0];versions[h&7]+=1;flags[h>>3]+=1;unique_headers.add(uw)
    record_bytes=length(records);mapped_record_bytes=length(intersect(records,mapped_exec))
    if record_bytes!=length(intersect(records,raw_exec)):raise ValueError('Runtime record outside executable file bytes')
    scopes=list(scopes)
    if length(scopes)!=length(intersect(scopes,raw_exec)):raise ValueError('Scope outside executable file bytes')
    return {'binary_sha256':hashlib.sha256(data).hexdigest(),'bits':bits,'section_count':n,
            'executable_raw_bytes':length(raw_exec),'executable_mapped_file_bytes':length(mapped_exec),
            'raw_padding_bytes':length(raw_exec)-length(mapped_exec),'runtime_records':len(records),
            'runtime_record_union_bytes':record_bytes,'runtime_record_mapped_bytes':mapped_record_bytes,
            'mapped_bytes_without_runtime_record':length(mapped_exec)-mapped_record_bytes if bits==64 else None,
            'unique_unwind_header_locations':len(unique_headers),'unwind_versions':dict(versions),'unwind_flags':dict(flags),
            'scope_raw_coverage':coverage(scopes,raw_exec),'scope_mapped_coverage':coverage(scopes,mapped_exec),
            'scope_runtime_coverage':coverage(scopes,records) if bits==64 else None,
            'note':'Metadata extent coverage, not executed code, full function boundaries or DSP identity.'}
