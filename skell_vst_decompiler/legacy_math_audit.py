"""Read-only PE32 import/relocation evidence; no private code or addresses returned."""
from collections import Counter
import hashlib
import re
import struct


LINE = re.compile(r'^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)(\S+)(?:\s|$)')
PUBLIC_MATH = frozenset(('_CIsqrt','_CIlog','_CIsin','_CIpow','_CIexp','_CIlog10','_CIcos','sqrt','log','sin','pow','exp','log10','cos','atan2','floor','ceil','fmod'))


def read_string(pe,rva):
    sections=[s for s in pe.sections if s['rva']<=rva<s['rva']+s['size']]
    if len(sections)!=1:raise ValueError('String not uniquely file-backed')
    s=sections[0];raw=pe.read(rva,min(512,s['rva']+s['size']-rva))
    end=raw.find(b'\0')
    if end<=0:raise ValueError('Invalid bounded string')
    return raw[:end].decode('ascii')


def imports(pe):
    """IAT slot RVA -> public import name (in memory only)."""
    rva,size=pe.directory(1)
    if not rva and not size:return {},0
    if not rva or not 20<=size<=20*256:raise ValueError('Import directory bound')
    raw=pe.read(rva,size);slots={};descriptors=0
    for offset in range(0,size-19,20):
        oft,stamp,chain,name,iat=struct.unpack_from('<IIIII',raw,offset)
        if not any((oft,stamp,chain,name,iat)):return slots,descriptors
        if not name or not iat:raise ValueError('Incomplete import descriptor')
        dll=read_string(pe,name).lower();descriptors+=1
        for i in range(8192):
            thunk,=struct.unpack('<I',pe.read((oft or iat)+4*i,4))
            if not thunk:break
            slot=iat+4*i;pe.read(slot,4)
            if slot in slots or len(slots)>=8192:raise ValueError('Duplicate or excessive import slots')
            symbol=None if thunk&0x80000000 else read_string(pe,thunk+2)
            slots[slot]=(dll,symbol)
        else:raise ValueError('Unterminated thunk table')
    raise ValueError('Unterminated import directory')


def relocations(pe):
    """Collect validated x86 HIGHLOW relocation locations, not relocated values."""
    rva,size=pe.directory(5)
    if not rva and not size:return set(),0
    if not rva or not 8<=size<=16*1024*1024:raise ValueError('Relocation directory bound')
    raw=pe.read(rva,size);pos=0;sites=set();padding=0
    while pos<len(raw):
        if raw[pos:pos+8]==b'\0'*min(8,len(raw)-pos):
            if any(raw[pos:]):raise ValueError('Nonzero data after relocation terminator')
            break
        if pos+8>len(raw):raise ValueError('Truncated relocation header')
        page,n=struct.unpack_from('<II',raw,pos)
        if page%4096 or n<8 or n%4 or pos+n>len(raw):raise ValueError('Invalid relocation block')
        for (entry,) in struct.iter_unpack('<H',raw[pos+8:pos+n]):
            kind,offset=entry>>12,entry&4095
            if kind==0:padding+=1;continue
            if kind!=3:raise ValueError('Unsupported x86 relocation kind')
            site=page+offset
            if site in sites:raise ValueError('Duplicate relocation')
            pe.read(site,4);sites.add(site)
        pos+=n
    return sites,padding


def decode(text,start,data):
    if not isinstance(data,bytes) or not 0<len(data)<=262144:raise ValueError('Invalid scope')
    rows={}
    for line in text.splitlines():
        m=LINE.match(line)
        if not m:continue
        va=int(m[1],16);raw=bytes.fromhex(m[2]);op=m[3].lower();off=va-start
        if off<0 or off+len(raw)>len(data) or not 1<=len(raw)<=15:continue
        if data[off:off+len(raw)]!=raw:raise ValueError('Decoder/source byte mismatch')
        if op.startswith('.') or op in ('(bad)','<unknown>','unknown'):continue
        if va in rows:raise ValueError('Duplicate decode location')
        rows[va]=(raw,op)
    return rows


def summarize_scope(data,start,base,left,right,slots,relocs,*,allowed=PUBLIC_MATH):
    """Count exact FF /2 or /4 absolute memory operands with IAT and relocation evidence."""
    a,b=decode(left,start,data),decode(right,start,data)
    agreed={va:a[va] for va in a.keys()&b.keys() if a[va][0]==b[va][0]}
    ordered=sorted(agreed)
    if any(v+len(agreed[v][0])>w for v,w in zip(ordered,ordered[1:])):raise ValueError('Overlapping spans')
    counts=Counter();math={'call':Counter(),'jmp':Counter()};unknown=0;no_reloc=0
    for va,(raw,op) in agreed.items():
        other=b[va][1]
        if len(raw)!=6 or raw[:2] not in (b'\xff\x15',b'\xff\x25'):continue
        kind='call' if raw[1]==0x15 else 'jmp'
        if not op.startswith(kind) or not other.startswith(kind):continue
        target=int.from_bytes(raw[2:],'little')-base
        if target not in slots:unknown+=1;continue
        if va-base+2 not in relocs:no_reloc+=1;continue
        counts[kind]+=1
        _,symbol=slots[target]
        if symbol in allowed:math[kind][symbol]+=1
    return {'scope_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
            'agreed_spans':len(agreed),'relocation_backed_iat_calls':counts['call'],
            'relocation_backed_iat_jumps':counts['jmp'],'iat_candidates_without_relocation':no_reloc,
            'absolute_transfers_not_in_import_table':unknown,'public_math_call_counts':dict(sorted(math['call'].items())),
            'public_math_jump_counts':dict(sorted(math['jmp'].items()))}
