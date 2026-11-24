"""Bounded, read-only PE export-directory metadata for x86 and x64.

No binary loading, disassembly or export of private symbol names. The optional
public_names parameter is an explicit allowlist (owned fixtures or public ABI).
"""
import argparse
import json
import struct
from pathlib import Path
from .legacy_pe import LegacyPE
from .pe import PE


def export_metadata(path, public_names=('VSTPluginMain','main','GetPluginFactory')):
    path=Path(path)
    with path.open('rb') as f:
        head=f.read(64)
        if len(head)!=64 or head[:2]!=b'MZ':
            raise ValueError('Missing DOS header')
        offset=struct.unpack_from('<I',head,60)[0]
        if offset<64 or offset>path.stat().st_size-26:
            raise ValueError('Invalid PE offset')
        f.seek(offset); header=f.read(26)
    if header[:4]!=b'PE\0\0':
        raise ValueError('Invalid PE signature')
    machine,=struct.unpack_from('<H',header,4)
    opt_size,=struct.unpack_from('<H',header,20)
    magic,=struct.unpack_from('<H',header,24)
    if (machine,magic)==(0x14c,0x10b):
        pe=LegacyPE(path); read=pe.read; rva,size=pe.directory(0)
        arch='x86';base=pe.base
    elif (machine,magic)==(0x8664,0x20b):
        pe=PE(path);read=pe.at_rva;arch='x64';base=pe.image_base
        if opt_size<112:
            raise ValueError('Truncated PE32+ directories')
        n,=struct.unpack_from('<I',pe.data,offset+24+108)
        if n>(opt_size-112)//8:
            raise ValueError('Truncated data directories')
        rva,size=struct.unpack_from('<II',pe.data,offset+24+112) if n else (0,0)
    else:
        raise ValueError('Unsupported PE architecture')
    result={'binary_sha256':pe.sha256,'architecture':arch,'image_base':hex(base),
            'named_count':0,'address_count':0,'public_entries':[],
            'reccmp_contiguous_table_assumption':None}
    if not rva and not size:
        return result
    if not rva or size<40 or rva+size>2**32:
        raise ValueError('Invalid export directory')
    _,_,_,_,_,ordinal_base,nf,nn,funcs,names,ords=struct.unpack('<IIHHIIIIIII',read(rva,40))
    # Aliases can outnumber function slots. Never assume names and slots are 1:1.
    if nf>65536 or nn>65536 or (nn and not nf):
        raise ValueError('Unreasonable export counts')
    if (nf and not funcs) or (nn and (not names or not ords)):
        raise ValueError('Missing export table')
    ft=read(funcs,4*nf) if nf else b''
    nt=read(names,4*nn) if nn else b''
    ot=read(ords,2*nn) if nn else b''
    allowed={}
    for name in public_names:
        raw=name.encode('ascii')
        if not raw or len(raw)>256 or b'\0' in raw:
            raise ValueError('Invalid public name')
        allowed[raw+b'\0']=name
    seen=set()
    for i in range(nn):
        pointer,=struct.unpack_from('<I',nt,i*4)
        index,=struct.unpack_from('<H',ot,i*2)
        if index>=nf:
            raise ValueError('Invalid name ordinal')
        target,=struct.unpack_from('<I',ft,index*4)
        for raw,name in allowed.items():
            try:
                matches=read(pointer,len(raw))==raw
            except ValueError:
                matches=False
            if matches:
                if name in seen:
                    raise ValueError('Repeated public export name')
                seen.add(name)
                result['public_entries'].append({'name':name,'rva':hex(target),
                    'ordinal':ordinal_base+index,'forwarded':rva<=target<rva+size})
    result['named_count']=nn;result['address_count']=nf
    result['public_entries'].sort(key=lambda x:x['name'])
    result['reccmp_contiguous_table_assumption']=(nf==nn and funcs==rva+40 and names==funcs+4*nf)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary',type=Path)
    print(json.dumps(export_metadata(p.parse_args().binary),indent=2,sort_keys=True))


if __name__=='__main__':main()
