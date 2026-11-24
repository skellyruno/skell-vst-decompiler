"""Exact-build FG-2A coefficient provenance and bounded nonlinear path evidence.
No coefficient arrays, raw instructions, vendor source, or reconstructed processor exported.
"""
import argparse
import json
import math
import struct
import hashlib
from .pe import PE
from .disasm import disassemble, direct_calls
from .extended_dsp import VMR_COPY, check_region
from .rack_paths import pointer_slots

# Store, source constant RVA, exponent call, sign. Only the address map is published.
WEIGHTS = (
    (0x550,0x14240e,0xeaa530,0x142409,1),
    (0x558,0x142448,0xeaa570,0x142435,-1),
    (0x560,0x142479,0xeaa560,0x14246f,-1),
    (0x568,0x1424a5,0xeaa500,0x1424a0,1),
    (0x570,0x1424d6,0xeaa4d0,0x1424cc,-1),
    (0x578,0x142507,0xeaa4d8,0x1424fd,-1),
    (0x580,0x142538,0xeaa518,0x14252e,-1),
    (0x588,0x142564,0xeaa460,0x14255f,1),
    (0x590,0x1425a4,0xeaa4f8,0x142587,1),
)


def verify(pe, objdump='objdump'):
    if pe.path.name != 'FG-2A.epl' or pe.sha256 != VMR_COPY['FG-2A.epl'][0]:
        raise ValueError('Unsupported source fingerprint')
    regions = []
    def add(key, title, start, end, checks, equation, imports=()):
        info = check_region(pe,start,end,checks,imports,objdump)
        regions.append({'id':key,'title':title,'equation':equation,
                        'confidence':'exact-build static evidence; runtime dispatch unverified',
                        'direct_calls':direct_calls(pe,disassemble(pe,start,end-start,objdump)),**info})
    add('fg2a_initializer_object','FG-2A initializer and processing subobject link',0x142340,0x14239f,[
        (0x142352,'mov','rsi,r8'),(0x142374,'lea','rcx,[rsi+0x590]'),
        (0x14237b,'call','0x180142c20'),(0x142380,'lea','rcx,[rsi+0x1360]'),
        (0x142387,'call','0x1801423a0')],
        'Setup calls coefficient initializer with parent subobject +0x1360; a separate subobject at +0x590 has a different initializer.')
    add('fg2a_processing_object','FG-2A processing subobject argument',0x156f00,0x156f54,[
        (0x156f04,'lea','rax,[rbx+0x1360]'),(0x156f0b,'mov','QWORD PTR [rsp+0x20],rax'),
        (0x156f4a,'lea','rcx,[rsp+0x20]'),(0x156f4f,'call','0x18014d590')],
        'The processing caller passes parent subobject +0x1360 through the first context slot to 0x14d590.')
    add('fg2a_processing_context','FG-2A coefficient base and channel count',0x14d5bd,0x14d61c,[
        (0x14d5bd,'mov','rax,QWORD PTR [rcx+0x30]'),(0x14d5c8,'mov','rbx,QWORD PTR [rcx]'),
        (0x14d5d8,'movsxd','rsi,DWORD PTR [rax+0x4]'),(0x14d5dc,'lea','r15d,[rsi+rsi*1]'),
        (0x14d617,'cmp','edi,0x2'),(0x14d61a,'jb','0x18014d5f0')],
        'RBX is the supplied subobject pointer; the processing loop copies two streams and uses twice the per-stream sample count for vector operations.')
    for addr, val in [(0xea9450,10.0),(0xeaa3b8,0.05),(0xeaa4b8,-1.0)]:
        if pe.at_rva(addr,8)!=struct.pack('<d',val):raise ValueError('Unexpected calibration conversion constant')
    add('fg2a_weight_base','FG-2A logarithmic calibration base',0x1425b7,0x1425ee,[
        (0x1425cc,'movaps','xmm0,xmm6'),(0x1425cf,'call','0x180d38e3c'),
        (0x1425d4,'mulsd','xmm0,xmm7'),(0x1425df,'movsd','QWORD PTR [rip+0xef3ee9],xmm0'),
        (0x1425ec,'jmp','0x180142577')],
        'A static initialization path computes ln(10)*0.05 and writes it to shared calibration scalar 0x10364d0.',[(0x1425cf,'log')])
    ins = disassemble(pe,0x1423a0,0x217,objdump)
    by={i.address-pe.image_base:i for i in ins}
    checks=[(0x1423c6,'movsd','xmm6,QWORD PTR [rip+0xd67082]'),
            (0x1423d7,'movsd','xmm7,QWORD PTR [rip+0xd67fd9]'),
            (0x14243a,'movsd','xmm8,QWORD PTR [rip+0xd68075]')]
    # Validate every multiply's actual RIP destination and the exact store, not a float search.
    vals=[]
    for offset,store,constant,call,sign in WEIGHTS:
        mul=by[call-8];load=by[call-16]
        if mul.mnemonic!='mulsd' or not mul.operands.startswith('xmm0,QWORD PTR [rip+') or not mul.operands.endswith(hex(pe.image_base+constant)):
            raise ValueError('Calibration constant reference mismatch')
        if load.mnemonic!='movsd' or not load.operands.endswith(hex(pe.image_base+0x10364d0)):
            raise ValueError('Calibration scalar reference mismatch')
        checks += [(call-16,'movsd',load.operands.split('#')[0].strip()),(call-8,'mulsd',mul.operands.split('#')[0].strip()),(call,'call','0x180d38e54'),(store,'movsd',f'QWORD PTR [rbx+{offset:#x}],xmm0')]
        if sign<0:
            checks.append((store-5,'mulsd','xmm0,xmm8'))
        raw=pe.at_rva(constant,8);db=struct.unpack('<d',raw)[0]
        value=sign*math.exp(math.log(10)*0.05*db)
        if not math.isfinite(value):raise ValueError('Nonfinite weight')
        vals.append(raw)
    add('fg2a_weight_initializer','FG-2A nine polynomial calibration weights',0x1423a0,0x1425b7,checks,
        'Nine scalar weights follow signed exp(ln(10)*0.05*d), equivalently signed 10^(d/20), with file-backed dB calibrations. Actual runtime updates not excluded.',[(r[3],'exp') for r in WEIGHTS])
    add('fg2a_odd_order_terms','FG-2A odd-power parallel branch',0x14dd74,0x14de64,[
        (0x14dd74,'movsd','xmm0,QWORD PTR [rbx+0x588]'),(0x14dd86,'call','0x18006f7e0'),
        (0x14dd95,'lea','rdx,[rbp+0x990]'),(0x14dd9c,'lea','rcx,[rbp+0x790]'),(0x14dda3,'call','0x18006f8a0'),
        (0x14ddb2,'lea','rdx,[rbp+0x990]'),(0x14ddb9,'lea','rcx,[rbp+0x390]'),(0x14ddc0,'call','0x18006f8a0'),
        (0x14ddcd,'lea','rdx,[rbp+0x990]'),(0x14ddd4,'lea','rcx,[rbp+0xfb0]'),(0x14dddb,'call','0x18006f8a0'),
        (0x14dde0,'movsd','xmm0,QWORD PTR [rbx+0x570]'),(0x14ddf5,'movsd','xmm0,QWORD PTR [rbx+0x558]'),
        (0x14de1b,'call','0x18006f840'),(0x14de20,'movsd','xmm0,QWORD PTR [rbx+0x590]'),
        (0x14de32,'call','0x18006f7e0'),(0x14de48,'call','0x18006f840')],
        'Previously computed v^2 combines with v to form v^3, v^5, v^7. The inspected vector paths scale and sum v^3/v^7, then scale the sum and add to a filtered branch. v^5 is formed but its final use is not established here.')
    add('fg2a_second_filter','FG-2A additional stereo DF2T bank',0x14dc90,0x14dd74,[
        (0x14dc9f,'mulsd','xmm1,QWORD PTR [rbx+0x3d0]'),(0x14dca7,'addsd','xmm1,QWORD PTR [rbx+0x390]'),
        (0x14dcb8,'mulsd','xmm0,QWORD PTR [rbx+0x3d8]'),(0x14dcc0,'mulsd','xmm1,QWORD PTR [rbx+0x3f0]'),
        (0x14dcc8,'addsd','xmm0,QWORD PTR [rbx+0x398]'),(0x14dcd0,'subsd','xmm0,xmm1'),
        (0x14dcd4,'movsd','QWORD PTR [rbx+0x390],xmm0'),(0x14dcdc,'mulsd','xmm2,QWORD PTR [rbx+0x3e0]'),
        (0x14dce4,'movsd','xmm0,QWORD PTR [rbx+0x3f8]'),(0x14dcf5,'subsd','xmm2,xmm0'),
        (0x14dcf9,'movsd','QWORD PTR [rbx+0x398],xmm2'),(0x14dd16,'addsd','xmm1,QWORD PTR [rbx+0x3b0]'),
        (0x14dd3f,'movsd','QWORD PTR [rbx+0x3b0],xmm0'),(0x14dd63,'movsd','QWORD PTR [rbx+0x3b8],xmm2')],
        'Two independent DF2T state pairs share coefficients at 0x3d0/3d8/3e0/3f0/3f8. Standard y=b0*x+z1, z1_next=b1*x-a1*y+z2, z2_next=b2*x-a2*y. Frequency calibration unresolved.')
    # The local rational helper uses scalar addition, division and symmetric clipping.
    # Confirm the inspected first slots; do not claim every SIMD slot or runtime selection.
    for thunk,table,target in [(0x6f800,0x1015eb0,0x71b90),(0x6f8c0,0x1016000,0x739d0),(0x6f7c0,0x1015e40,0x71270),(0x6f880,0x1015f90,0x73030)]:
        entries=pointer_slots(pe,table,1)
        ins=disassemble(pe,thunk,18,objdump)
        if int(entries[0]['target_rva'],16)!=target or not entries[0]['executable_file_backed'] or len(ins)!=3 or not ins[1].operands.endswith(hex(pe.image_base+table)) or ins[-1].text!='jmp QWORD PTR [r11+rax*8]':
            raise ValueError('Unexpected rational helper dispatch')
    add('fg2a_scalar_offset','FG-2A scalar addition candidate',0x71c09,0x71c18,[
        (0x71c09,'movsd','xmm0,QWORD PTR [rcx+rdx*8]'),(0x71c0e,'addsd','xmm0,xmm1'),(0x71c12,'movsd','QWORD PTR [r8+rdx*8],xmm0')],
        'Inspected scalar helper: dst=src+offset.')
    add('fg2a_division','FG-2A vector division candidate',0x739fa,0x73a19,[
        (0x739fa,'movsd','xmm0,QWORD PTR [rcx+rdx*8]'),(0x739ff,'movsd','xmm1,QWORD PTR [r10+rdx*8]'),(0x73a05,'ucomisd','xmm0,xmm2'),(0x73a0b,'je','0x180073a19'),(0x73a0d,'divsd','xmm1,xmm0'),(0x73a11,'movsd','QWORD PTR [r8+rdx*8],xmm1')],
        'Inspected scalar helper: dst=second/first for finite nonzero denominator. Exceptional denominator handling is outside this equation.')
    if struct.unpack('<Q',pe.at_rva(0xf68100,8))[0] != 0x8000000000000000:raise ValueError('Unexpected clip sign mask')
    add('fg2a_symmetric_clip','FG-2A symmetric clipping candidate',0x7128a,0x712c3,[
        (0x7128e,'comisd','xmm0,xmm3'),(0x71292,'jbe','0x180071298'),(0x71298,'movaps','xmm2,xmm3'),(0x7129d,'xorps','xmm2,XMMWORD PTR [rip+0xef6e5c]'),(0x712aa,'maxsd','xmm0,QWORD PTR [rcx+rax*8]'),(0x712af,'minsd','xmm1,xmm0'),(0x712b3,'movsd','QWORD PTR [rdx+rax*8],xmm1')],
        'Inspected scalar helper: dst=clamp(src,-limit,+limit), finite limit >= 0.')
    add('fg2a_subtract','FG-2A vector difference candidate',0x730a1,0x730b3,[
        (0x730a1,'movsd','xmm0,QWORD PTR [rdx+r11*8]'),(0x730a7,'subsd','xmm0,QWORD PTR [rcx+r11*8]'),(0x730ad,'movsd','QWORD PTR [r8+r11*8],xmm0')],
        'Inspected scalar helper: dst=second-first.')
    add('fg2a_rational_stage','FG-2A local biased rational transform',0x142110,0x142335,[
        (0x142132,'mov','rsi,r9'),(0x142135,'mov','r14,rcx'),(0x142152,'movsd','xmm1,QWORD PTR [rsi+0x28]'),(0x14216c,'call','0x18006f800'),(0x142180,'call','0x180075f40'),(0x14219b,'call','0x18006f8a0'),(0x1421a0,'movsd','xmm1,QWORD PTR [rsi]'),(0x1421b5,'call','0x18006f820'),(0x1421ba,'movsd','xmm2,QWORD PTR [rsi+0x8]'),(0x14229b,'mulsd','xmm0,QWORD PTR [rdx+rcx*1]'),(0x1422a0,'addsd','xmm0,QWORD PTR [rcx]'),(0x1422a4,'movsd','QWORD PTR [rcx],xmm0'),(0x1422b2,'movsd','xmm1,QWORD PTR [rsi+0x10]'),(0x1422c8,'call','0x18006f800'),(0x1422e5,'call','0x18006f8c0'),(0x1422ea,'movsd','xmm3,QWORD PTR [rsi+0x20]'),(0x142300,'call','0x18006f7c0'),(0x142305,'movsd','xmm1,QWORD PTR [rsi+0x30]'),(0x142314,'mov','r8,r14'),(0x142317,'call','0x18006f800')],
        'On the inspected scalar dispatch path for finite input/nonzero denominator/nonnegative limit: u=x+offset_in; numerator=A*u^3+B*u; denominator=u^2+C; dst=clamp(numerator/denominator,-limit,limit)+offset_out. Six coefficient fields in argument record at +0/+8/+0x10/+0x20/+0x28/+0x30. Runtime coefficient origins and dispatch unverified.')
    add('fg2a_rational_consumers','FG-2A two rational transform callsites',0x14dc2c,0x14dc79,[
        (0x14dc2c,'movsd','xmm1,QWORD PTR [rbx+0x550]'),(0x14dc45,'call','0x18006f820'),(0x14dc59,'call','0x18006f840'),(0x14dc5e,'lea','r9,[rbx+0x238]'),(0x14dc65,'mov','r8d,r15d'),(0x14dc68,'lea','rdx,[rsp+0x50]'),(0x14dc6d,'lea','rcx,[rbp+0x190]'),(0x14dc74,'call','0x180142110')],
        'The filtered even-order sum is combined with a weighted squared term, then passed to a rational transform with parameter record +0x238. This verifies a second-order contribution in addition to the previous fourth/sixth/eighth-order polynomial.')
    add('fg2a_branch_merge','FG-2A later branch merge and second rational transform',0x14e04e,0x14e0ae,[
        (0x14e05d,'call','0x18006f840'),(0x14e062,'lea','r9,[rbx+0x270]'),(0x14e06c,'lea','rdx,[rbp+0x790]'),(0x14e073,'lea','rcx,[rsp+0x50]'),(0x14e078,'call','0x180142110'),(0x14e087,'lea','rdx,[rsp+0x50]'),(0x14e08c,'lea','rcx,[rbp+0x790]'),(0x14e093,'call','0x18006f880'),(0x14e0a9,'call','0x18006f840')],
        'A second rational transform uses record +0x270. Its output is differenced against the preceding stream and added into another scratch branch on the inspected helper paths. This is not the final audio gain law.')
    # Read endpoints span one confirmed processor object, not an offset-only search.
    consumers=[(0x550,0x14dc2c,'xmm1'),(0x558,0x14ddf5,'xmm0'),(0x560,0x14dafb,'xmm1'),
               (0x568,0x14dad0,'xmm0'),(0x570,0x14dde0,'xmm0'),(0x578,0x14dabb,'xmm0'),
               (0x580,0x14de4d,'xmm0'),(0x588,0x14dd74,'xmm0'),(0x590,0x14de20,'xmm0')]
    add('fg2a_weight_consumers','FG-2A nine initialized weight read endpoints',0x14dabb,0x14de64,
        [(r,'movsd',f'{reg},QWORD PTR [rbx+{f:#x}]') for f,r,reg in consumers]+[
        (0x14de55,'lea','rdx,[rbp+0xb90]'),(0x14de5f,'call','0x18006f7e0')],
        'All nine initialized weight fields are read from the linked subobject in this candidate. The last endpoint (0x580) scales the fourth-power scratch stream. A matching read is not proof that every path is executed in a live plugin.')
    add('fg2a_local_output_merge','FG-2A candidate local clipping and output handoff',0x14e1b6,0x14e2ab,[
        (0x14e1b6,'movaps','xmm3,xmm6'),(0x14e1b9,'lea','rdx,[rsp+0x50]'),(0x14e1c1,'lea','rcx,[rbp+0x190]'),
        (0x14e1c8,'call','0x18006f7c0'),(0x14e1d0,'lea','rdx,[rsp+0x50]'),(0x14e1d5,'lea','rcx,[rbp+0x11b0]'),(0x14e1dc,'call','0x18006f840'),
        (0x14e22c,'call','0x18006f740'),(0x14e233,'cmp','edi,0x2'),(0x14e236,'jb','0x18014e210'),(0x14e2a6,'call','0x18014f340')],
        'Inspected scalar candidates clamp a local filtered branch, add the saved input scratch stream, copy two buffers, and pass a context to 0x14f340. That downstream routine and final plugin output remain unresolved.')
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'regions':regions,
            'weight_origins_verified':len(WEIGHTS),'weight_origins_total':9,
            'weight_consumer_endpoints_verified':len(consumers),'weight_links':[{'field':hex(f),'initializer_store_rva':hex(w[1]),'consumer_read_rva':hex(r)} for w,(f,r,_) in zip(WEIGHTS,consumers)],
            'calibration_source_sha256':hashlib.sha256(b''.join(vals)).hexdigest(),
            'checkpoint_count':sum(r['checkpoint_count'] for r in regions),
            'limits':'Only nine weights in this initializer; not a percentage of all FG-2A DSP. No raw dB values or reconstructed processor exported. Runtime dispatch and full gain law unverified.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary');p.add_argument('--objdump',default='objdump');a=p.parse_args()
    print(json.dumps(verify(PE(a.binary),a.objdump),indent=2,allow_nan=False))

if __name__=='__main__':main()
