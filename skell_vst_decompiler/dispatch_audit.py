"""Conservative decoder comparison and indirect dispatch census for x64 PE.

Read-only. An IAT identity is a dependency boundary, not a loaded address.
A relocated file-image pointer is a candidate, not a guaranteed runtime target.
"""
from collections import Counter
import re
import struct
from .disasm import disassemble
from .pe import PEFormatError
from .relocation_navigation import relocated_slots

NUM = re.compile(r'(?<![a-z0-9])(?:0x[0-9a-f]+|[0-9]+)(?![a-z0-9])')
REG = re.compile(r'(?:r(?:ax|bx|cx|dx|si|di|sp|bp|[89]|1[0-5]))$')
MEM = re.compile(r'qwordptr\[rip(?:([+-])(\d+))?\]$')
ALU = {'add','sub','cmp','test','and','or','xor','adc','sbb','mov','movabs'}


def basic(ins):
    s=ins.operands.split('#',1)[0].split('<',1)[0].lower()
    s=NUM.sub(lambda m:str(int(m[0],16 if m[0].startswith('0x') else 10)),s)
    s=re.sub(r'\s+','',s)
    s=re.sub(r'(?<![a-z0-9])([1248])\*([a-z][a-z0-9]+)',r'\2*\1',s)
    return ins.mnemonic.lower(),re.sub(r'\+0(?=\])','',s)


def width(operand):
    for name,bits in [('byteptr',8),('wordptr',16),('dwordptr',32),('qwordptr',64)]:
        if operand.startswith(name+'['):return bits
    if REG.fullmatch(operand):return 64
    if re.fullmatch(r'e(?:ax|bx|cx|dx|si|di|sp|bp)|r(?:[89]|1[0-5])d',operand):return 32
    if re.fullmatch(r'(?:ax|bx|cx|dx|si|di|sp|bp)|r(?:[89]|1[0-5])w',operand):return 16
    if re.fullmatch(r'[abcd][hl]|(?:sil|dil|spl|bpl)|r(?:[89]|1[0-5])b',operand):return 8
    return None


def canonical(ins):
    op,s=basic(ins)
    # Omit only an explicit scale of one in a memory expression.
    s=re.sub(r'\[[^\]]*\]',lambda m:re.sub(r'\b([a-z][a-z0-9]*)\*1(?!\d)',r'\1',m[0]),s)
    if op in ALU and s.count(',')==1:
        dst,imm=s.split(',');bits=width(dst)
        if bits and re.fullmatch(r'-?\d+',imm):
            value=int(imm)
            if -(1<<(bits-1))<=value<(1<<bits):s=dst+','+str(value%(1<<bits))
    if op=='xchg' and s.count(',')==1:
        a,b=s.split(',')
        if width(a) and width(a)==width(b) and '[' not in s:s=','.join(sorted((a,b)))
    return op,s


def agreement(pe,a,b):
    if a.address!=b.address:return False
    if canonical(a)==canonical(b):return True
    # Explicit and implicit count-one shifts have exactly the same D0/D1
    # encoding. Validate the opcode and extension before accepting the alias.
    rva=a.address-pe.image_base
    try:
        p=pe.at_rva(rva,2,executable=True)
        offset=1 if 0x40<=p[0]<=0x4f else 0
        raw=pe.at_rva(rva,offset+2,executable=True)[offset:]
        shifts={'rol':0,'ror':1,'rcl':2,'rcr':3,'shl':4,'shr':5,'sar':7}
        aa,bb=canonical(a),canonical(b)
        if aa[0]==bb[0] and aa[0] in shifts and raw[0] in (0xd0,0xd1) and (raw[1]>>3)&7==shifts[aa[0]]:
            if aa[1]==bb[1]+',1' or bb[1]==aa[1]+',1':return True
        # A redundant operand-size prefix on the specific 0F 1F /0 NOP.
        for x,y in ((a,b),(b,a)):
            if canonical(x)==('xchg','ax,ax') and canonical(y)==('nop','') and p==b'\x66\x90':return True
            if x.mnemonic=='data16' and x.operands.lower().startswith('nop ') and y.mnemonic=='nop':
                from .disasm import Instruction
                raw=pe.at_rva(rva,4,executable=True)
                if raw[:2]==b'\x66\x66' and raw[2:]==b'\x0f\x1f' and canonical(Instruction(x.address,'nop',x.operands[4:]))==canonical(y):return True
        # GNU may print the signed LEA displacement as a 64-bit unsigned value.
        if aa[0]==bb[0]=='lea':
            ra=re.fullmatch(r'(r[a-z0-9]+),\[rip([+-])(\d+)\]',aa[1]);rb=re.fullmatch(r'(r[a-z0-9]+),\[rip([+-])(\d+)\]',bb[1])
            if ra and rb and ra[1]==rb[1] and width(ra[1])==64:
                raw=pe.at_rva(rva,7,executable=True)
                if raw[0] in (0x48,0x4c) and raw[1]==0x8d and raw[2]&0xc7==5:
                    regs=['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15']
                    reg=regs[((raw[2]>>3)&7)+(8 if raw[0]&4 else 0)]
                    disp=struct.unpack_from('<i',raw,3)[0]
                    values=[int(m[3])*(-1 if m[2]=='-' else 1) for m in (ra,rb)]
                    if reg==ra[1] and all(v in (disp,disp%(1<<64)) for v in values):return True
    except PEFormatError:pass
    # These aliases require exact original bytes, not blanket prefix removal.
    for x,y in ((a,b),(b,a)):
        rva=x.address-pe.image_base
        try:
            if x.mnemonic=='rex' and x.operands.lower().startswith('push '):
                reg=x.operands.lower()[5:];regs=['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi']
                if reg in regs and pe.at_rva(rva,2,executable=True)==bytes([0x40,0x50+regs.index(reg)]) and canonical(y)==('push',reg):return True
            if x.mnemonic=='rex.' and x.operands.lower().startswith('w jmp '):
                from .disasm import Instruction
                stripped=Instruction(x.address,'jmp',x.operands[6:]);raw=pe.at_rva(rva,7,executable=True)
                if raw[:3]==b'\x48\xff\xa0' and struct.unpack_from('<i',raw,3)[0]>=0:
                    if canonical(stripped)==canonical(y)==('jmp','qwordptr[rax+'+str(struct.unpack_from('<i',raw,3)[0])+']'):return True
        except PEFormatError:pass
    return False


class DispatchAudit:
    def __init__(self,pe):
        self.pe=pe
        self.imports=pe.imports()
        self.relocations=set(relocated_slots(pe))

    def pointer(self,slot):
        if slot in self.imports:
            return {'status':'import_boundary','slot_rva':hex(slot),'dll':self.imports[slot]['dll']}
        section=next((s for s in self.pe.sections if s.rva<=slot and slot+8<=s.rva+min(s.virtual_size,s.file_size)),None)
        if section is None:return {'status':'unbacked_pointer_slot','slot_rva':hex(slot)}
        if slot not in self.relocations:return {'status':'pointer_without_relocation','slot_rva':hex(slot)}
        value=struct.unpack('<Q',self.pe.at_rva(slot,8))[0]-self.pe.image_base
        try:self.pe.at_rva(value,1,executable=True)
        except PEFormatError:return {'status':'relocation_noncode','slot_rva':hex(slot)}
        if section.executable or section.characteristics&0x80000000:
            return {'status':'mutable_pointer_candidate','slot_rva':hex(slot),'file_target_rva':hex(value)}
        return {'status':'readonly_relocated_candidate','slot_rva':hex(slot),'file_target_rva':hex(value)}

    def classify(self,ins,end):
        site=ins.address-self.pe.image_base;op,operand=canonical(ins)
        if op=='rex.' and operand.startswith('wjmp'):
            op,operand='jmp',operand[4:]
        if op not in ('call','jmp') or re.fullmatch(r'\d+',operand):return None
        # Byte-derive RIP-relative slot: FF /2 or /4, mod=00 r/m=101.
        m=MEM.fullmatch(operand)
        if m:
            try:
                first=self.pe.at_rva(site,1,executable=True)[0];prefix=1 if first==0x48 else 0
                size=6+prefix
                if site+size>end:return {'status':'truncated_instruction'}
                raw=self.pe.at_rva(site,size,executable=True)
                disp=struct.unpack_from('<i',raw,prefix+2)[0]
                expected=(int(m[2])*(-1 if m[1]=='-' else 1)) if m[2] else 0
                if raw[prefix:prefix+2]==bytes((0xff,0x15 if op=='call' else 0x25)) and disp==expected:return self.pointer(site+size+disp)
            except PEFormatError:pass
            return {'status':'rip_encoding_unverified'}
        if REG.fullmatch(operand):return {'status':'register_dynamic'}
        if operand.startswith('qwordptr['):return {'status':'memory_dynamic'}
        return {'status':'other_indirect'}

    def compare(self,start,length,left,right):
        a={i.address-self.pe.image_base:i for i in left};b={i.address-self.pe.image_base:i for i in right}
        rows=[];old=0;new=0;missing=0
        for site,x in a.items():
            y=b.get(site)
            if y is None:missing+=1;old+=1;new+=1;continue
            if basic(x)!=basic(y):old+=1
            if not agreement(self.pe,x,y):new+=1;continue
            row=self.classify(y,start+length)
            if row is not None:rows.append({'site_rva':hex(site),**row})
        return {'start':hex(start),'bytes':length,'gnu_sites':len(a),'llvm_sites':len(b),'old_strict_disagreements':old,'remaining_gnu_disagreements':new,'gnu_only_sites':missing,'llvm_only_sites':len(b.keys()-a.keys()),'indirect_sites':rows,'status_counts':dict(Counter(r['status'] for r in rows))}

    def scope(self,start,length):
        return self.compare(start,length,*(disassemble(self.pe,start,length,t) for t in ('objdump','llvm-objdump')))


def main():
    import argparse
    import json
    from pathlib import Path
    from .pe import PE
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('binary');p.add_argument('sha256');p.add_argument('--scope',action='append',default=[],help='hex RVA:decimal length')
    p.add_argument('--vmr-wrappers',action='store_true')
    a=p.parse_args();path=Path(a.binary)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=256*1024*1024:raise ValueError('Expected bounded PE file')
    pe=PE(path)
    if pe.sha256!=a.sha256:raise ValueError('Fingerprint mismatch')
    if a.vmr_wrappers:
        if a.scope:raise ValueError('Select either scopes or wrapper mode')
        from .wrapper_dispatch import module_wrappers
        result=module_wrappers(pe)
    else:
        if not 1<=len(a.scope)<=128:raise ValueError('Select 1..128 scopes')
        scopes=[v.split(':',1) for v in a.scope];audit=DispatchAudit(pe)
        result={'sha256':pe.sha256,'scopes':[audit.scope(int(s,16),int(n)) for s,n in scopes]}
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
