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
    """Decode only E8/E9/EB and FF 15/25 (optionally redundant REX.W)."""
    try:
        op=pe.at_rva(rva,1,executable=True)[0]
        if op in (0xe8,0xe9,0xeb):
            n=2 if op==0xeb else 5
            kind='call' if op==0xe8 else 'jmp';indirect=False;offset=1
        elif op in (0xff,0x48):
            prefix=int(op==0x48)
            raw=pe.at_rva(rva,prefix+2,executable=True)
            if raw[prefix]!=0xff or raw[prefix+1] not in (0x15,0x25):return None
            n=6+prefix;kind='call' if raw[prefix+1]==0x15 else 'jmp';indirect=True;offset=2+prefix
        else:return None
        if end is not None and rva+n>end:return None
        raw=pe.at_rva(rva,n,executable=True)
        return kind,indirect,rva+n+int.from_bytes(raw[offset:],'little',signed=True)
    except PEFormatError:return None


def text_agrees(pe,ins,edge):
    kind,indirect,dest=edge
    text=ins.operands.split('#',1)[0].split('<',1)[0].strip().lower()
    mnemonic=ins.mnemonic
    try:prefix=indirect and pe.at_rva(ins.address-pe.image_base,1,executable=True)==b'\x48'
    except PEFormatError:return False
    if prefix and mnemonic=='rex.' and text.startswith('w '+kind+' '):
        mnemonic=kind;text=text[len(kind)+3:]
    if mnemonic!=kind:return False
    if not indirect:
        m=re.fullmatch(r'0x([0-9a-f]+)',text)
        return bool(m and int(m[1],16)-pe.image_base==dest)
    m=re.fullmatch(r'qword\s*ptr\s*\[\s*rip\s*(?:([+-])\s*(0x[0-9a-f]+|[0-9]+))?\s*\]',text)
    if not m:return False
    d=int(m[2],16 if m[2].startswith('0x') else 10) if m[2] else 0
    if m[1]=='-':d=-d
    return ins.address-pe.image_base+6+int(prefix)+d==dest


REGISTERS = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')


def adjacent_import_load(pe, load, branch, end):
    """Recognize a byte-backed adjacent MOV from an IAT slot, then CALL/JMP register.

    This identifies an instruction-pair candidate only: alternate control-flow
    entry, register state, and loaded pointer contents are not established.
    """
    a=load.address-pe.image_base;b=branch.address-pe.image_base
    if b!=a+7 or b>=end or load.mnemonic!='mov' or branch.mnemonic not in ('call','jmp'):
        return None
    try:
        raw=pe.at_rva(a,7,executable=True)
        if raw[0] not in (0x48,0x4c) or raw[1]!=0x8b or raw[2]&0xc7!=5:return None
        reg=((raw[2]>>3)&7)+(8 if raw[0]&4 else 0)
        disp=struct.unpack_from('<i',raw,3)[0]
        text=load.operands.split('#',1)[0].split('<',1)[0].strip().lower()
        match=re.fullmatch(r'(\w+)\s*,\s*qword\s*ptr\s*\[\s*rip\s*(?:([+-])\s*(0x[0-9a-f]+|[0-9]+))?\s*\]',text)
        if not match or match[1]!=REGISTERS[reg]:return None
        d=int(match[3],16 if match[3].startswith('0x') else 10) if match[3] else 0
        if match[2]=='-':d=-d
        if d!=disp or branch.operands.strip().lower()!=REGISTERS[reg]:return None
        n=3 if reg>=8 else 2
        if b+n>end:return None
        encoded=pe.at_rva(b,n,executable=True)
        if reg>=8 and encoded[0]!=0x41:return None
        expected=(0xd0 if branch.mnemonic=='call' else 0xe0)+(reg&7)
        if encoded[-2:]!=bytes((0xff,expected)):return None
        return b+disp
    except PEFormatError:return None


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
        rows=[];candidates=[];rejected=0;pe_base=self.pe.image_base
        for addr,x in a.items():
            site=addr-self.pe.image_base;y=b.get(addr)
            if not start<=site<start+length or x.mnemonic not in ('call','jmp','rex.'):continue
            edge=transfer(self.pe,site,start+length)
            if edge is None:continue
            if y is None or not text_agrees(self.pe,x,edge) or not text_agrees(self.pe,y,edge):rejected+=1;continue
            op,indirect,dest=edge
            result=self.slot(dest,[]) if indirect else self.follow(dest)
            rows.append({'site':hex(site),'op':op,**result})
        for addr,x in a.items():
            prev=a.get(addr-7);other=b.get(addr);other_prev=b.get(addr-7)
            if not (prev and other and other_prev) or not start<=addr-pe_base<start+length or prev.address-pe_base<start:continue
            slot=adjacent_import_load(self.pe,prev,x,start+length)
            if slot is not None and slot in self.imports and slot==adjacent_import_load(self.pe,other_prev,other,start+length):
                candidates.append({'site':hex(addr-pe_base),'load':hex(prev.address-pe_base),'slot':hex(slot),**self.imports[slot],'status':'adjacent_import_load_candidate'})
        return {'start':hex(start),'bytes':length,'counts':dict(Counter(r['status'] for r in rows)),'rejected':rejected,'import_edges':[r for r in rows if r['status']=='import_boundary'],'adjacent_import_candidates':candidates}
