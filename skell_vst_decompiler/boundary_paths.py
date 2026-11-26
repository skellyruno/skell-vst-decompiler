"""Bounded dependency-boundary audit for ordinary x64 PE calls and thunks.
No execution, loader emulation or reconstruction of dependent modules.
"""
from collections import Counter
import re
import struct
from .pe import PEFormatError
from .disasm import disassemble


def directory(pe,index):
    opt=pe._unpack('<I',60)[0]+24
    size=pe._unpack('<H',opt-4)[0]
    if size<112 or index>=pe._unpack('<I',opt+108)[0] or size<112+8*(index+1):
        return 0,0
    return pe._unpack('<II',opt+112+8*index)


def delay_imports(pe):
    """RVA-based PE32+ delay descriptors; unsupported layouts fail closed."""
    rva,size=directory(pe,13)
    if not rva and not size:return {}
    if not rva or not 32<=size<=32*1024 or size%32:
        raise PEFormatError('Invalid delay directory size')
    data=pe.at_rva(rva,size);result={}
    for row in struct.iter_unpack('<8I',data):
        if not any(row):return result
        flags,name,_,iat,lookup,_,_,_=row
        if flags!=1 or not name or not iat or not lookup:
            raise PEFormatError('Unsupported delay descriptor layout')
        dll=pe.cstring_rva(name)
        for i in range(8192):
            value=struct.unpack('<Q',pe.at_rva(lookup+8*i,8))[0]
            if not value:break
            slot=iat+8*i;pe.at_rva(slot,8)
            if slot in result:raise PEFormatError('Duplicate delay import slot')
            if value>>63:
                if value&0x7fffffffffff0000:raise PEFormatError('Invalid import ordinal')
                symbol='#'+str(value&0xffff)
            else:
                if value>=1<<32:raise PEFormatError('Invalid delay import name')
                pe.at_rva(value,2);symbol=pe.cstring_rva(value+2)
            result[slot]={'dll':dll,'symbol':symbol,'kind':'delay'}
        else:raise PEFormatError('Delay import thunk limit')
    raise PEFormatError('Missing delay descriptor terminator')


def transfer(pe,rva,end=None):
    """Decode only unprefixed E8/E9/EB and FF 15/25; no arbitrary x86 decoder."""
    try:
        op=pe.at_rva(rva,1,executable=True)[0]
        if op in (0xe8,0xe9,0xeb):
            n=2 if op==0xeb else 5
            kind='call' if op==0xe8 else 'jmp';indirect=False;offset=1
        elif op==0xff:
            second=pe.at_rva(rva+1,1,executable=True)[0]
            if second not in (0x15,0x25):return None
            n=6;kind='call' if second==0x15 else 'jmp';indirect=True;offset=2
        else:return None
        if end is not None and rva+n>end:return None
        raw=pe.at_rva(rva,n,executable=True)
        return kind,indirect,rva+n+int.from_bytes(raw[offset:],'little',signed=True)
    except PEFormatError:return None


def text_agrees(pe,ins,edge):
    kind,indirect,dest=edge
    if ins.mnemonic!=kind:return False
    text=ins.operands.split('#',1)[0].split('<',1)[0].strip().lower()
    if not indirect:
        m=re.fullmatch(r'0x([0-9a-f]+)',text)
        return bool(m and int(m[1],16)-pe.image_base==dest)
    m=re.fullmatch(r'qword\s*ptr\s*\[\s*rip\s*(?:([+-])\s*(0x[0-9a-f]+|[0-9]+))?\s*\]',text)
    if not m:return False
    d=int(m[2],16 if m[2].startswith('0x') else 10) if m[2] else 0
    if m[1]=='-':d=-d
    return ins.address-pe.image_base+6+d==dest


class BoundaryAudit:
    def __init__(self,pe):
        self.pe=pe
        self.imports={k:{**v,'kind':'ordinary'} for k,v in pe.imports().items()}
        delayed=delay_imports(pe)
        if self.imports.keys()&delayed.keys():raise PEFormatError('Overlapping import slots')
        self.imports.update(delayed)

    def follow(self,target,max_hops=8):
        if type(max_hops) is not int or not 1<=max_hops<=16:raise ValueError('Invalid hop bound')
        seen=set();hops=[]
        for _ in range(max_hops):
            if target in seen:return {'status':'cycle','hops':hops}
            seen.add(target)
            try:self.pe.at_rva(target,1,executable=True)
            except PEFormatError:return {'status':'outside_executable','hops':hops}
            edge=transfer(self.pe,target)
            if edge is None or edge[0]!='jmp':return {'status':'local_entry','hops':hops}
            _,indirect,dest=edge;hops.append(hex(target))
            if indirect:return self.slot(dest,hops)
            target=dest
        return {'status':'hop_limit','hops':hops}

    def slot(self,dest,hops):
        if dest not in self.imports:return {'status':'unresolved_pointer','hops':hops,'slot':hex(dest)}
        i=self.imports[dest]
        return {'status':'import_boundary','hops':hops,'slot':hex(dest),'kind':i['kind'],'dll':i['dll'],'symbol':i['symbol']}

    def scope(self,start,length):
        if type(length) is not int or not 1<=length<=32768:raise ValueError('Invalid scope length')
        a,b=({i.address:i for i in disassemble(self.pe,start,length,t)} for t in ('objdump','llvm-objdump'))
        rows=[];rejected=0
        for addr,x in a.items():
            site=addr-self.pe.image_base;y=b.get(addr)
            if not start<=site<start+length or x.mnemonic not in ('call','jmp'):continue
            edge=transfer(self.pe,site,start+length)
            if edge is None:continue
            if y is None or not text_agrees(self.pe,x,edge) or not text_agrees(self.pe,y,edge):rejected+=1;continue
            op,indirect,dest=edge
            result=self.slot(dest,[]) if indirect else self.follow(dest)
            rows.append({'site':hex(site),'op':op,**result})
        return {'start':hex(start),'bytes':length,'counts':dict(Counter(r['status'] for r in rows)),'rejected':rejected,'import_edges':[r for r in rows if r['status']=='import_boundary']}
