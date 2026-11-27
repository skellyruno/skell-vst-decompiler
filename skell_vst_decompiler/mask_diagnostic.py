"""Conservative local SSE mask-selection diagnostics, calibrated on owned code."""
import re
from collections import Counter
from .value_flow import decode_register

PRED = ('eq','lt','le','unord','neq','nlt','nle','ord')
SUFFIX = {0:'ps',0x66:'pd',0xf2:'sd',0xf3:'ss'}


def decode(raw):
    if not raw:return None
    i=0;p=0;rex=0
    if raw[i] in SUFFIX and raw[i]:p=raw[i];i+=1
    if i<len(raw) and 0x40<=raw[i]<=0x4f:rex=raw[i];i+=1
    if len(raw)<i+3 or raw[i]!=0x0f or raw[i+2]>>6!=3:return None
    op,mr=raw[i+1:i+3];suffix=SUFFIX[p]
    dst=((mr>>3)&7)+8*bool(rex&4);src=(mr&7)+8*bool(rex&1)
    if op==0xc2 and len(raw)==i+4 and raw[-1]<8:
        return 'cmp'+PRED[raw[-1]]+suffix,dst,src
    if op in (0x54,0x55,0x56,0x57) and p in (0,0x66) and len(raw)==i+3:
        return {0x54:'and',0x55:'andn',0x56:'or',0x57:'xor'}[op]+suffix,dst,src
    r=decode_register(raw)
    if r:return r[0],r[2],r[3]
    return None


def scan(left,right,raw,va,entries=()):
    """Count comparison, bitwise and local complementary-mask OR candidates.

    Input maps must be from raw_decode for the same bounded window. A scalar
    comparison only defines a mask in the scalar lane. We never infer the
    payload values, runtime role, numerical transfer or CFG completeness.
    Unknown instructions, entry boundaries and memory operations clear tags.
    """
    tags={};counts=Counter();prev=None;entries=set(entries)
    if not 1<=len(raw)<=32768 or any(not va<=x<va+len(raw) for x in entries):raise ValueError('Invalid bounded window')
    for site in sorted(left.keys()|right.keys()):
        if site!=prev or site in entries:tags.clear()
        prev=None;a,b=left.get(site),right.get(site)
        if not a or not b or a.raw!=b.raw:tags.clear();continue
        chunk=a.raw; offset=site-va
        if not 0<=offset<len(raw) or not 1<=len(chunk)<=15 or offset+len(chunk)>len(raw) or raw[offset:offset+len(chunk)]!=chunk:raise ValueError('Raw row outside original window')
        d=decode(chunk)
        if not d:tags.clear();continue
        op,dst,src=d; args='xmm%d,xmm%d'%(dst,src)
        if any(r.instruction.mnemonic!=op or re.sub(r'\s+','',r.instruction.operands.split('#',1)[0].lower())!=args for r in (a,b)):
            tags.clear();continue
        prev=site+len(chunk);old=tags.get(dst);other=tags.get(src);tags.pop(dst,None)
        if op.startswith('cmp'):
            counts['comparison_masks']+=1;tags[dst]=('mask',site,op[-2:])
        elif op in ('movaps','movapd','movups','movupd'):
            if other:tags[dst]=other
        elif op in ('andps','andpd','andnps','andnpd','orps','orpd','xorps','xorpd'):
            counts['bitwise_register_ops']+=1
            width=op[-1]
            def mask(t):return t and t[0]=='mask' and t[2][-1]==width
            if op.startswith('andn') and mask(old) and other is None and dst!=src:
                tags[dst]=('term',old[1],old[2],False)
            elif op.startswith('and') and not op.startswith('andn'):
                m=old if mask(old) and other is None else other if mask(other) and old is None else None
                if m and dst!=src:tags[dst]=('term',m[1],m[2],True)
            elif op.startswith('or') and old and other and old[0]==other[0]=='term' and old[1:3]==other[1:3] and old[3]!=other[3] and old[2][-1]==width:
                counts['complementary_mask_select_candidates']+=1
                counts['select_'+old[2]]+=1
    return dict(counts)
