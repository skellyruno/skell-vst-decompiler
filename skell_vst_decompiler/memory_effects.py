"""Conservative legacy SSE memory evidence; no runtime address or DSP inference."""
import hashlib
import re
from collections import Counter
from .pe import PEFormatError
from .disasm import disassemble
from .scope_consensus import reconcile

REGS = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi') + tuple('r%d'%i for i in range(8,16))
FORMS = {0x10:'mov',0x11:'mov',0x28:'mov',0x29:'mov',0x51:'sqrt',
         0x58:'add',0x59:'mul',0x5c:'sub',0x5d:'min',0x5e:'div',0x5f:'max'}
PREFIX = {0:('ps',16),0x66:('pd',16),0xf2:('sd',8),0xf3:('ss',4)}
SIZES = {4:'dword',8:'qword',16:'xmmword'}


def decode_memory(raw):
    """Decode only explicit memory operands of selected legacy SSE forms."""
    if not raw: return None
    p = 0; rex = 0; i = 0
    if raw[i] in (0x66,0xf2,0xf3): p=raw[i]; i+=1
    if i<len(raw) and 0x40<=raw[i]<=0x4f: rex=raw[i]; i+=1
    if len(raw)<i+3 or raw[i]!=0x0f or raw[i+1] not in FORMS: return None
    op, mr = raw[i+1:i+3]; i+=3
    mod, reg, rm = mr>>6, ((mr>>3)&7)+8*bool(rex&4), mr&7
    if mod==3: return None
    if op in (0x28,0x29) and p not in (0,0x66): return None
    suffix,width = PREFIX[p]
    mnemonic = ('movu'+suffix if op in (0x10,0x11) and p in (0,0x66) else 'mova'+suffix if op in (0x28,0x29) else FORMS[op]+suffix)
    base, index, scale, disp_size = None,None,1,0
    if rm==4:
        if i>=len(raw): return None
        sib=raw[i]; i+=1; scale=1<<(sib>>6)
        idx=(sib>>3)&7; b=sib&7
        if idx!=4 or rex&2: index=REGS[idx+8*bool(rex&2)]
        if mod==0 and b==5: disp_size=4
        else: base=REGS[b+8*bool(rex&1)]
    elif mod==0 and rm==5: base='rip'; disp_size=4
    else: base=REGS[rm+8*bool(rex&1)]
    if mod==1: disp_size=1
    if mod==2: disp_size=4
    if len(raw)!=i+disp_size: return None
    disp=int.from_bytes(raw[i:],'little',signed=True) if disp_size else 0
    if index is None: scale=1
    return mnemonic, 'write' if op in (0x11,0x29) else 'read', width, reg, base,index,scale,disp


def operand_matches(ins, decoded):
    mnemonic,access,width,reg,base,index,scale,disp=decoded
    if ins.mnemonic!=mnemonic: return False
    args=re.sub(r'\s+','',ins.operands.split('#',1)[0].lower()).split(',')
    if len(args)!=2: return False
    mem,xmm=(args[0],args[1]) if access=='write' else (args[1],args[0])
    if xmm!='xmm%d'%reg: return False
    m=re.fullmatch(SIZES[width]+r'ptr\[([^\]]+)\]',mem)
    if not m: return False
    expr=m[1]
    # Accept reordered addition, explicit scale-one, decimal/hex displacement.
    terms=re.findall(r'[+-]?[^+-]+',expr)
    if ''.join(terms)!=expr: return False
    regs=[]; constant=0
    for term in terms:
        sign=-1 if term.startswith('-') else 1
        t=term.lstrip('+-')
        r=re.fullmatch(r'(r(?:[a-z]{2}|1[0-5]|[89])|rip)(?:\*([1248]))?',t)
        rr=re.fullmatch(r'([1248])\*(r(?:[a-z]{2}|1[0-5]|[89])|rip)',t)
        if r or rr:
            if sign<0: return False
            regs.append((r[1],int(r[2] or '1')) if r else (rr[2],int(rr[1])))
        elif re.fullmatch(r'0x[0-9a-f]+|[0-9]+',t):
            constant+=sign*int(t,16 if t.startswith('0x') else 10)
        else: return False
    wanted=([(base,1)] if base else [])+([(index,scale)] if index else [])
    return sorted(regs)==sorted(wanted) and constant==disp


def address_class(base,index):
    if base=='rip': return 'rip_relative'
    if base=='rsp' or index=='rsp': return 'stack_pointer'
    if base=='rbp' or index=='rbp': return 'frame_or_general'
    if base is None: return 'no_base'
    return 'general_register'


def audit_scope(pe,fingerprint,start,length):
    if pe.sha256!=fingerprint: raise PEFormatError('Binary fingerprint mismatch')
    if type(start) is not int or type(length) is not int or not 1<=length<=32768: raise ValueError('Invalid bounded scope')
    raw=pe.at_rva(start,length,executable=True); va=pe.image_base+start
    streams=[[x for x in disassemble(pe,start,length,t) if va<=x.address<va+length] for t in ('objdump','llvm-objdump')]
    _,fp=reconcile(*streams,va,va+length)
    maps=[{x.address:(x,y.address) for x,y in zip(s,s[1:])} for s in streams]
    counts=Counter(); rejected=0; verified={}
    for site in sorted(maps[0].keys() & maps[1].keys()):
        a,end=maps[0][site]; b,end2=maps[1][site]
        if end!=end2 or not 1<=end-site<=15: continue
        d=decode_memory(raw[site-va:end-va])
        if d is None: continue
        if not operand_matches(a,d) or not operand_matches(b,d): rejected+=1; continue
        cls=address_class(d[4],d[5]); counts[d[1]+'_'+cls]+=1
        verified[site]=d
    # A narrow local read/FP register arithmetic/write pattern. Identical
    # effective-address expression does not prove a runtime buffer identity.
    patterns=0
    for site,d in verified.items():
        if d[0] not in ('movss','movsd','movaps','movapd','movps','movpd','movups','movupd') or d[1]!='read' or address_class(d[4],d[5])!='general_register': continue
        middle=maps[0][site][1]
        if middle not in maps[0] or middle not in maps[1] or middle not in fp: continue
        a,end=maps[0][middle]; b,end2=maps[1][middle]
        if end!=end2 or end not in verified: continue
        out=verified[end]
        if out[0]!=d[0] or out[1]!='write' or out[2:]!=d[2:]: continue
        # The middle instruction must be selected register-register legacy SSE.
        chunk=raw[middle-va:end-va]; i=0
        if chunk and chunk[0] in (0x66,0xf2,0xf3): i+=1
        rex=0
        if i<len(chunk) and 0x40<=chunk[i]<=0x4f: rex=chunk[i];i+=1
        if len(chunk)!=i+3 or chunk[i]!=0x0f or chunk[i+1] not in (0x58,0x59,0x5c,0x5d,0x5e,0x5f) or chunk[i+2]>>6!=3: continue
        dst=((chunk[i+2]>>3)&7)+8*bool(rex&4)
        src=(chunk[i+2]&7)+8*bool(rex&1)
        op=FORMS[chunk[i+1]]+d[0][-2:]
        operands='xmm%d,xmm%d'%(dst,src)
        if dst!=d[3] or any(x.mnemonic!=op or re.sub(r'\s+','',x.operands.lower())!=operands for x in (a,b)): continue
        patterns+=1
    return {'start':hex(start),'bytes':length,'scope_sha256':hashlib.sha256(raw).hexdigest(),
            'verified_memory_sites':sum(counts.values()),'memory_classes':dict(counts),'operand_rejections':rejected,
            'selected_fp_sites':len(fp),'local_read_arithmetic_write':patterns,
            'limits':'Selected legacy SSE only; address syntax classes and contiguous local patterns, not runtime buffers or DSP proof.'}
