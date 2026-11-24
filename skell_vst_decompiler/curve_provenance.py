"""Build-specific evidence of table initialization and adaptive state, no vendor tables exported."""
import hashlib
import math
import re
import struct
from .equations import TVB_SHA256
from .disasm import disassemble, imported_call_sites
from .navigation import runtime_ranges, containing_range


def require(pe, ins, checks):
    by_rva={i.address-pe.image_base:i for i in ins}
    for rva,mnemonic,operand in checks:
        i=by_rva.get(rva)
        if i is None or i.mnemonic!=mnemonic or i.operands.split('#')[0].strip()!=operand:
            raise ValueError(f'Instruction evidence mismatch at {rva:#x}')
    return len(checks)


def immediate_initializer(ins, size):
    """Validate restricted straight-line MOV stores into an RCX output buffer.
    Only recognizes XOR EAX,EAX and MOV immediate/known-zero stores; rejects holes,
    overlap, unsupported writes, unknown instructions, and non-finite float data.
    """
    if size<=0 or size>65536 or size%4:raise ValueError('Invalid buffer size')
    data=bytearray(size); covered=bytearray(size); zero=False; returned=False
    for i in ins:
        if returned:raise ValueError('Unexpected code after return')
        if i.mnemonic=='xor' and i.operands=='eax,eax':zero=True;continue
        if i.mnemonic=='mov' and i.operands=='rax,rcx':zero=False;continue
        if i.mnemonic=='ret' and not i.operands:returned=True;continue
        m=re.fullmatch(r'(DWORD|QWORD) PTR \[rcx(?:\+0x([0-9a-f]+))?\],(eax|rax|0x[0-9a-f]+)',i.operands)
        if i.mnemonic!='mov' or m is None:raise ValueError(f'Unsupported initializer instruction at {i.address:#x}')
        width=4 if m[1]=='DWORD' else 8; offset=int(m[2] or '0',16)
        if offset%4 or offset+width>size or any(covered[offset:offset+width]):raise ValueError('Initializer range or duplicate write')
        value=m[3]
        if value in ('eax','rax'):
            if not zero or (value=='rax')!=(width==8):raise ValueError('Unknown register value')
            v=0
        else:
            v=int(value,16)
            if width==8 and v>=0x80000000:raise ValueError('Unsupported sign-extended immediate')
        data[offset:offset+width]=v.to_bytes(width,'little'); covered[offset:offset+width]=b'\x01'*width
    if not returned or not all(covered):raise ValueError('Incomplete initializer coverage')
    if not all(math.isfinite(v[0]) for v in struct.iter_unpack('<f',data)):raise ValueError('Non-finite initializer')
    return bytes(data)


def summary(data,rows,cols):
    if len(data)!=rows*cols*4:raise ValueError('Wrong table size')
    vals=struct.unpack('<'+'f'*rows*cols,data)
    if not all(map(math.isfinite,vals)):raise ValueError('Nonfinite table')
    return {'rows':rows,'points_per_row':cols,'total_points':len(vals),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(), 'all_finite':True,'row_shapes':[{'row':r,'negative_step_count':sum(b<a for a,b in zip(vals[r*cols:(r+1)*cols-1],vals[r*cols+1:(r+1)*cols])),'flat_step_count':sum(b==a for a,b in zip(vals[r*cols:(r+1)*cols-1],vals[r*cols+1:(r+1)*cols]))} for r in range(rows)]}


def verify_curves(pe,objdump='objdump'):
    if pe.sha256!=TVB_SHA256:raise ValueError('Unexpected source fingerprint')
    startup=disassemble(pe,0x16a50,0x151,objdump)
    c=require(pe,startup,[(0x16a5c,'call','0x1805d2c70'),(0x16a68,'mov','edx,0x9'),(0x16ae4,'mov','DWORD PTR [rcx+0x40],eax'),(0x16afc,'call','0x1805d31b0'),(0x16b08,'mov','edx,0x4'),(0x16b95,'mov','QWORD PTR [rcx+0x60],rax')])
    for site,target in [(0x16a61,0x77e7cb0),(0x16b01,0x77e7a40)]:
        i=next(x for x in startup if x.address-pe.image_base==site)
        if i.mnemonic!='lea' or not i.operands.endswith(hex(pe.image_base+target)):raise ValueError('Wrong table destination')
    copy=disassemble(pe,0x5d2c70,0x31b,objdump)
    c+=require(pe,copy,[(0x5d2c78,'mov','r8d,0x4c4'),(0x5d2c8f,'mov','ecx,0x5'),(0x5d2f71,'lea','rdx,[rdx+0xf4]'),(0x5d2f7c,'jne','0x1805d2ca0'),(0x5d2f8a,'ret','')])
    ref=next(x for x in copy if x.address-pe.image_base==0x5d2c88)
    if ref.mnemonic!='lea' or not ref.operands.endswith('0x180a5ba80'):raise ValueError('Wrong table source')
    # All 61 paired loads/stores are verified, not just the loop stride.
    pairs=[i for i in copy if 0x5d2ca0<=i.address-pe.image_base<0x5d2f71]
    if len(pairs)!=122:raise ValueError('Unexpected table copy instructions')
    for j in range(61):
        suffix='' if j==0 else '+'+hex(j*4)
        if pairs[2*j].text!=f'mov eax,DWORD PTR [rdx+r8*1{suffix}]' or pairs[2*j+1].text!=f'mov DWORD PTR [rdx+rbx*1{suffix}],eax':raise ValueError('Unexpected table copy offset')
    initializer=disassemble(pe,0x5d31b0,0x512,objdump)
    a=summary(pe.at_rva(0xa5ba80,1220),5,61)
    b=summary(immediate_initializer(initializer,616),2,77)
    for rva,value in [(0x928ac4,-12.0),(0xa5b808,-70.0),(0x909bec,0.05),(0x909c98,10.0),(0xa5c720,3.01029995664)]:
        if not math.isclose(pe.f32(rva),value,rel_tol=1e-6):raise ValueError('Unexpected numerical constant')
    mode2=disassemble(pe,0x5d18d6,0x1ba,objdump)
    c+=require(pe,mode2,[(0x5d18ee,'subss','xmm7,xmm11'),(0x5d18fa,'divss','xmm0,DWORD PTR [rbp-0x5c]'),(0x5d1913,'xorps','xmm8,xmm12'),(0x5d191b,'call','0x18087f1aa'),(0x5d1920,'mulss','xmm0,DWORD PTR [rbp-0x54]'),(0x5d192e,'mulss','xmm8,xmm0'),(0x5d1933,'minss','xmm8,xmm7'),(0x5d1938,'addss','xmm8,DWORD PTR [rsi+0xd48]'),(0x5d1980,'call','0x18087f1c8'),(0x5d1a3e,'divss','xmm8,xmm0'),(0x5d1a43,'minss','xmm8,xmm9'),(0x5d1a48,'mulss','xmm8,xmm7'),(0x5d1a4d,'addss','xmm8,xmm11'),(0x5d1a63,'movss','DWORD PTR [rsi+0xd48],xmm8'),(0x5d1a6c,'movss','DWORD PTR [rsi+0x204],xmm8'),(0x5d1a75,'subss','xmm1,xmm0'),(0x5d1a79,'mulss','xmm1,DWORD PTR [rbp-0x4c]'),(0x5d1a7e,'addss','xmm1,xmm0'),(0x5d1a88,'movss','DWORD PTR [rsi+0xd4c],xmm1')])
    c+=require(pe,mode2,[(0x5d1961,'maxss','xmm0,xmm11'),(0x5d1975,'movss','xmm1,DWORD PTR [rax]'),(0x5d199d,'movaps','xmm2,xmm7'),(0x5d19a7,'maxss','xmm2,xmm10'),(0x5d19ac,'mulss','xmm3,DWORD PTR [rax]'),(0x5d19cd,'mulss','xmm1,DWORD PTR [rsi+0xd4c]'),(0x5d19e4,'addss','xmm1,xmm9'),(0x5d19fc,'mulss','xmm3,xmm1'),(0x5d1a00,'divss','xmm2,xmm0'),(0x5d1a08,'addss','xmm2,xmm9'),(0x5d1a0d,'divss','xmm3,xmm2'),(0x5d1a11,'comiss','xmm0,xmm3'),(0x5d1a2f,'minss','xmm0,xmm3'),(0x5d1a39,'subss','xmm7,xmm11')])
    i=next(x for x in mode2 if x.address-pe.image_base==0x5d18ff)
    if i.mnemonic!='call' or not i.operands.endswith('0x1808db4f0') or pe.imports().get(0x8db4f0,{}).get('symbol')!='expm1f':raise ValueError('Wrong expm1f import')
    if {x['symbol'] for x in imported_call_sites(pe,mode2)}!={'expf','powf'}:raise ValueError('Wrong adaptive math imports')
    mode1=disassemble(pe,0x5d12f9,0x2bb,objdump)
    c+=require(pe,mode1,[(0x5d1349,'mov','ecx,0x4'),(0x5d134e,'call','0x1805d30b0'),(0x5d1395,'xor','ecx,ecx'),(0x5d139f,'mulss','xmm7,xmm2'),(0x5d1485,'subss','xmm2,xmm4'),(0x5d1498,'divss','xmm2,xmm8'),(0x5d149d,'mulss','xmm7,xmm2'),(0x5d14a6,'addss','xmm7,xmm0'),(0x5d14b3,'call','0x18087f1aa'),(0x5d14cb,'call','0x18087f1c8'),(0x5d14fa,'divss','xmm0,xmm1'),(0x5d1504,'subss','xmm2,xmm3'),(0x5d150a,'mulss','xmm2,DWORD PTR [rbp-0x74]'),(0x5d152e,'mulss','xmm1,DWORD PTR [rsi+0x214]'),(0x5d153b,'divss','xmm0,xmm1'),(0x5d153f,'mulss','xmm0,xmm2'),(0x5d154e,'addss','xmm2,xmm3'),(0x5d1552,'movss','DWORD PTR [rsi+0x210],xmm2'),(0x5d1563,'mulss','xmm0,xmm2'),(0x5d1595,'mulss','xmm2,xmm13'),(0x5d159a,'subss','xmm2,xmm1'),(0x5d159e,'mulss','xmm2,DWORD PTR [rbp-0x68]'),(0x5d15a3,'addss','xmm2,xmm1'),(0x5d15a7,'movss','DWORD PTR [rsi+0x214],xmm2')])
    i=next(x for x in mode1 if x.address-pe.image_base==0x5d1576)
    if i.mnemonic!='call' or not i.operands.endswith('0x1808db3c0') or pe.imports().get(0x8db3c0,{}).get('symbol')!='log1pf':raise ValueError('Wrong log1pf import')
    for rva,value in [(0x9143d8,4),(0x914410,8),(0x928a68,12),(0x928a70,20),(0x909c80,3)]:
        if pe.f32(rva)!=value:raise ValueError('Wrong curve blend anchor')
    entries=runtime_ranges(pe)
    return {'schema_version':1,'binary_sha256':pe.sha256,'source':pe.path.name,'status':'instruction-verified table provenance and local recurrence; runtime and vendor sound unverified','checkpoint_count':c,'copy_word_pairs_verified':61,'initializer_instruction_count':len(initializer),'runtime_record_count':len(entries),'tables':[{'mode':1,'source_rva':'0xa5ba80','initializer_rva':'0x5d2c70','startup_copy_rva':'0x16a50','destination_rva':'0x77e7cb0','lookup_rva':'0x5d30b0','coordinate_origin':-12,**a},{'mode':2,'source':'immediate stores','initializer_rva':'0x5d31b0','startup_copy_rva':'0x16af0','destination_rva':'0x77e7a40','lookup_rva':'0x5d1833','coordinate_origin':-70,**b}], 'regions':[{'id':'mode1_curve_blend','start_rva':'0x5d1342','end_rva_exclusive':'0x5d14aa','title':'Ratio-indexed interpolation across curve rows','confidence':'instruction-verified structure','equation':'Special selector uses row 4. Ordinary selector scales row 0 below anchor 4, interpolates adjacent rows between anchors 4, 8, 12, 20, and selects row 3 above 20; the source field and UI semantics remain unverified.','containing_range':containing_range(entries,0x5d1342)},{'id':'mode1_history_release','start_rva':'0x5d14aa','end_rva_exclusive':'0x5d15af','title':'Mode 1 nonlinear target and coupled recovery','confidence':'instruction-verified structure','equation':'Nonlinear target uses exp and optional pow. Primary state Q at 0x210 rises using attack coefficient and falls with coefficient b/(1+k*H). Secondary history H at 0x214 smooths a transformed log1p output, which is coupled back into target and release. Full parameter scaling unresolved.','containing_range':containing_range(entries,0x5d14aa)},{'id':'mode2_nonlinear_attack','start_rva':'0x5d18d6','end_rva_exclusive':'0x5d1946','title':'Reduction-dependent exponential attack increment','confidence':'instruction-verified local recurrence','equation':'For target C > prior G, delta=C-G; G_new=G+min(delta, A*(1-exp(-delta/B))*exp(-G/D)), with positive setup-dependent A,B,D.','containing_range':containing_range(entries,0x5d18d6)},{'id':'mode2_adaptive_release','start_rva':'0x5d1946','end_rva_exclusive':'0x5d1a52','title':'State- and target-dependent release','confidence':'instruction-verified structure','equation':'G_new=G+min(1, step/tau(G,C,H))*(C-G); tau=clamp(a*(max(0.05,G)/10)^(-p)*(1+k*H)/(1+max(C,0)/max(d,0.1)), lo, hi); selected constants a,p,k,d,lo,hi not mapped to UI.','containing_range':containing_range(entries,0x5d1946)},{'id':'mode2_history','start_rva':'0x5d1a52','end_rva_exclusive':'0x5d1a90','title':'Secondary history state','confidence':'instruction-verified local recurrence','equation':'H_new=H+alpha*(0.05*G_new-H); primary reduction G_new stored in 0xd48 and 0x204; H stored in 0xd4c.','containing_range':containing_range(entries,0x5d1a52)}], 'limits':['No vendor table values or raw instructions exported; table hashes prove reproducibility.','Static initialization verified, later runtime mutations not excluded.','No UI mode names, full parameter mapping, measured audio or VMR gain law established.']}
