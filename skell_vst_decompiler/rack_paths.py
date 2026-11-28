"""Read-only, exact-build evidence for rack filter, dynamics and spatial paths.
No vendor code or calibration arrays are emitted. VMR table slots are candidates,
not proven runtime choices. Only the listed local arithmetic is verified.
"""
import hashlib
import math
import struct
from .equations import TVB_SHA256
from .extended_dsp import VMR_COPY, check_region, constants
from .disasm import disassemble, direct_calls
from .pe import PEFormatError


def pointer_slots(pe, table, count):
    """Inspect an explicit bounded number of native VA slots, not inferred extent."""
    if not isinstance(count, int) or not 1 <= count <= 64 or table % 8:
        raise ValueError('Require aligned table and 1..64 explicit slots')
    result=[]
    for index, (va,) in enumerate(struct.iter_unpack('<Q', pe.at_rva(table,count*8))):
        rva=va-pe.image_base
        try: pe.at_rva(rva,1,executable=True); valid=True
        except PEFormatError: valid=False
        result.append({'slot':index,'target_rva':hex(rva) if valid else None,'executable_file_backed':valid})
    return result


def verify_tvb_rack(pe,objdump='objdump'):
    if pe.sha256 != TVB_SHA256: raise ValueError('Unexpected source fingerprint')
    regions=[]
    def add(id,title,start,end,checks,equation,imports=()):
        regions.append({'id':id,'title':title,'confidence':'exact-source instruction-verified local relationships; runtime unverified','equation':equation,**check_region(pe,start,end,checks,imports,objdump)})
    add('eq_coefficients','Eight-way TPT coefficient builder',0x5a5ef0,0x5a6117,[
      (0x5a5f51,'maxss','xmm10,DWORD PTR [rip+0x3ce23e]'),(0x5a5f5a,'divss','xmm0,xmm1'),
      (0x5a5f70,'divss','xmm1,DWORD PTR [rip+0x382b08]'),(0x5a5f84,'divss','xmm8,xmm10'),
      (0x5a5fa1,'mov','ecx,DWORD PTR [rdx+rdi*4+0x5a6118]'),(0x5a5fab,'jmp','rcx'),
      (0x5a5fb1,'mov','DWORD PTR [rbx+0x1c],0xbf800000'),(0x5a5fc4,'mulss','xmm6,xmm6'),
      (0x5a5fce,'mulss','xmm0,xmm10'),(0x5a5fda,'divss','xmm8,xmm0'),(0x5a5fdf,'mulss','xmm6,xmm8'),
      (0x5a6007,'divss','xmm9,xmm0'),(0x5a601b,'mulss','xmm0,xmm8'),(0x5a6020,'movss','DWORD PTR [rbx+0x1c],xmm6'),
      (0x5a6043,'mulss','xmm9,xmm0'),(0x5a6056,'movss','DWORD PTR [rbx+0x14],xmm1'),(0x5a6060,'mulss','xmm0,xmm6'),(0x5a6070,'movss','DWORD PTR [rbx+0x1c],xmm0'),
      (0x5a6086,'movss','DWORD PTR [rbx+0x18],xmm8'),(0x5a6096,'mov','DWORD PTR [rbx+0x1c],0x3f800000'),
      (0x5a60a7,'mulss','xmm0,DWORD PTR [rip+0x363c2d]'),(0x5a60c5,'addss','xmm8,xmm9'),(0x5a60d0,'mulss','xmm8,xmm9'),(0x5a60d5,'addss','xmm8,xmm7'),(0x5a60da,'divss','xmm7,xmm8'),
      (0x5a60e5,'movss','DWORD PTR [rbx+0x8],xmm7'),(0x5a60ef,'movss','DWORD PTR [rbx+0xc],xmm7'),(0x5a60ff,'movss','DWORD PTR [rbx+0x10],xmm7')],
      'A=10^(gain_dB/40); g=tan(pi*f/Fs), k=1/max(Q,.025). Numeric modes 0 highpass, 1 bell (k=k/A), 2 low shelf (g=g/sqrt(A)), 3 high shelf (g=g*sqrt(A)), 4 notch, 5 bandpass, 6 lowpass, 7 allpass. Coefficient mixer and integrator math documented in report; GUI mapping not established.',[(0x5a5f5e,'tanf'),(0x5a5f89,'powf'),(0x5a6002,'sqrtf'),(0x5a603e,'sqrtf')])
    table=list(struct.unpack('<8I',pe.at_rva(0x5a6118,32)))
    if table != [0x5a5fad,0x5a5fc4,0x5a5fee,0x5a602a,0x5a6077,0x5a6084,0x5a6094,0x5a60a3]:raise ValueError('Wrong EQ branch table')
    add('eq_consumer','Suite EQ mono TPT sample consumer',0x5a43e0,0x5a4466,[
      (0x5a43f4,'subss','xmm1,xmm4'),(0x5a4401,'mulss','xmm5,xmm2'),(0x5a4408,'mulss','xmm3,DWORD PTR [rax+rbx*1+0x10]'),(0x5a440e,'mulss','xmm0,xmm1'),(0x5a4412,'addss','xmm5,xmm4'),(0x5a4416,'mulss','xmm1,DWORD PTR [rax+rbx*1+0x18]'),(0x5a441c,'addss','xmm3,xmm0'),(0x5a4420,'addss','xmm5,xmm1'),(0x5a4432,'subss','xmm0,xmm2'),(0x5a4436,'subss','xmm1,xmm4'),(0x5a443a,'movss','DWORD PTR [rax+rbx*1+0x28],xmm0'),(0x5a4443,'movss','DWORD PTR [rax+rbx*1+0x48],xmm1'),(0x5a4449,'mulss','xmm3,DWORD PTR [rax+rbx*1+0x20]'),(0x5a444f,'mulss','xmm0,DWORD PTR [rax+rbx*1+0x1c]'),(0x5a4455,'mulss','xmm5,DWORD PTR [rax+rbx*1+0x24]'),(0x5a4462,'addss','xmm6,xmm5')],
      'v3=x-s2; v1=a1*s1+a2*v3; v2=s2+a2*s1+a3*v3; s1_next=2*v1-s1; s2_next=2*v2-s2; y=m0*x+m1*v1+m2*v2. Mono TPT branch; other cascades remain.')
    add('gate_detector','Gate high-pass and stereo-linked absolute envelope',0x5c99ac,0x5c9a47,[
      (0x5c99bf,'addss','xmm1,DWORD PTR [rbx+rcx*4+0x18c]'),(0x5c99c8,'subss','xmm1,DWORD PTR [rbx+rcx*4+0x16c]'),(0x5c99d1,'mulss','xmm1,DWORD PTR [rbx+0x1ac]'),(0x5c99e2,'movss','DWORD PTR [rbx+rcx*4+0x18c],xmm1'),(0x5c99eb,'andps','xmm1,xmm6'),(0x5c99ee,'maxss','xmm1,xmm2'),(0x5c9a11,'cmova','rax,rdx'),(0x5c9a15,'mulss','xmm2,DWORD PTR [rbx+rax*1]'),(0x5c9a22,'movss','DWORD PTR [rbx+0x1b0],xmm2')],
      'hp=a*(x-x_prev+hp_prev); p=max_channel(abs(hp)); E+=alpha_attack_or_release*(p-E); level=max(-120,20log10(E)). Detector filtered, main audio multiplied separately.',[(0x5c9a2f,'log10f')])
    add('gate_hold','Gate hysteresis, hold and gain smoothing',0x5c9a47,0x5c9b18,[
      (0x5c9a47,'comiss','xmm1,xmm10'),(0x5c9a4d,'mov','BYTE PTR [rbx+0x1bc],0x1'),(0x5c9a54,'mov','DWORD PTR [rbx+0x1c0],r12d'),(0x5c9a5d,'comiss','xmm12,xmm1'),(0x5c9a6d,'dec','eax'),(0x5c9a77,'mov','BYTE PTR [rbx+0x1bc],0x0'),(0x5c9a8d,'subss','xmm1,xmm10'),(0x5c9a92,'subss','xmm0,xmm15'),(0x5c9a97,'mulss','xmm1,xmm0'),(0x5c9a9b,'maxss','xmm1,DWORD PTR [rsp+0x24]'),(0x5c9ac5,'movss','xmm1,DWORD PTR [rbx+0x1c4]'),(0x5c9ae2,'mulss','xmm0,xmm2'),(0x5c9aea,'movss','DWORD PTR [rbx+0x1c4],xmm0'),(0x5c9b10,'mulss','xmm0,DWORD PTR [rbx+0x1c4]')],
      'Open when detector level > T, reload hold; below close threshold decrement hold then close. When closed, gain_dB=max(floor,(level-T)*(ratio-1)); when open, 0 dB. Linear gain uses separate rising/falling smoothing. Close threshold optionally T-4 dB; native setup mapping and runtime not fully established.',[(0x5c9ac0,'powf')])
    add('limiter_interpolator','Limiter three 12-tap fractional-phase peak candidates',0x5dd820,0x5ddb3f,[
      (0x5dd820,'movss','xmm2,DWORD PTR [rsi+0x2a0]'),(0x5dd85a,'movss','xmm3,DWORD PTR [rsi+0x2d0]'),(0x5dd98f,'mulss','xmm0,DWORD PTR [rsi+0x2cc]'),(0x5dd9b7,'andps','xmm2,XMMWORD PTR [rip+0x30be62]'),(0x5dd9c2,'maxss','xmm2,DWORD PTR [rsp+0x30]'),(0x5dda6c,'movss','xmm1,DWORD PTR [rsi+0x2f8]'),(0x5ddabb,'andps','xmm3,XMMWORD PTR [rip+0x30bd5e]'),(0x5ddac2,'maxss','xmm3,xmm2'),(0x5ddac6,'movss','xmm2,DWORD PTR [rsi+0x300]'),(0x5ddb21,'addss','xmm2,xmm15'),(0x5ddb26,'andps','xmm2,XMMWORD PTR [rip+0x30bcf3]'),(0x5ddb2d,'maxss','xmm2,xmm3'),(0x5ddb31,'movaps','XMMWORD PTR [rsp+0x30],xmm2')],
      'In enabled branch, three 12-coefficient dot products at 0x2a0/0x2d0/0x300 on channel history; maximum of absolute values and prior peak. Exact fractional-phase positions and true-peak compliance not established.')
    add('limiter_peak','Monotonic peak queue and soft-knee target',0x5ddbbe,0x5ddd17,[
      (0x5ddbe6,'comiss','xmm2,DWORD PTR [rax+rcx*8+0x8]'),(0x5ddbed,'mov','DWORD PTR [rsi+0x26c],edx'),(0x5ddc16,'mov','QWORD PTR [rcx+rdx*8],rax'),(0x5ddc1a,'movss','DWORD PTR [rcx+rdx*8+0x8],xmm2'),(0x5ddc4a,'movsxd','rax,DWORD PTR [rsi+0x178]'),(0x5ddc58,'sub','rcx,rax'),(0x5ddc81,'cmp','QWORD PTR [r8+rax*8],rcx'),(0x5ddc8d,'movss','xmm0,DWORD PTR [r8+rax*8+0x8]'),(0x5ddcd6,'subss','xmm1,xmm0'),(0x5ddd01,'addss','xmm7,xmm1'),(0x5ddd05,'mulss','xmm7,xmm7'),(0x5ddd09,'divss','xmm7,xmm2'),(0x5ddd12,'maxss','xmm7,xmm11')],
      'Timestamped monotonic peak queue expires entries older than lookahead interval. Excess u=peak_dB-ceiling_dB. For half-knee h>0 and -h<u<h, target GR=(u+h)^2/(4h); otherwise max(u,0).',[(0x5ddc9a,'log10f')])
    add('limiter_output','Delayed gain and final sample ceiling',0x5de006,0x5de079,[
      (0x5de027,'mov','DWORD PTR [rdx+rcx*4],eax'),(0x5de02a,'movsxd','rax,DWORD PTR [rsi+0x178]'),(0x5de038,'sub','rcx,rax'),(0x5de03b,'and','rcx,QWORD PTR [rsi+0x240]'),(0x5de042,'mulss','xmm1,DWORD PTR [rdx+rcx*4]'),(0x5de04c,'movaps','xmm0,xmm2'),(0x5de055,'minss','xmm0,xmm1'),(0x5de067,'movss','DWORD PTR [rcx+rbp*4],xmm0')],
      'y=clamp(delayed_audio*linear_gain,-ceiling_linear,ceiling_linear). Sample ceiling is not a certified intersample bound.')
    add('width','Mid/side width with interpolated decorrelation and optional DC/high-pass recurrence',0x5d5f66,0x5d6034,[
      (0x5d5f8b,'mulss','xmm3,xmm7'),(0x5d5f93,'addss','xmm3,xmm6'),(0x5d5f97,'mulss','xmm1,xmm8'),(0x5d5f9c,'addss','xmm1,xmm2'),(0x5d5fa8,'mulss','xmm11,xmm2'),(0x5d5fad,'mulss','xmm0,xmm2'),(0x5d5fb1,'subss','xmm3,xmm1'),(0x5d5fb5,'mulss','xmm3,xmm11'),(0x5d5fba,'addss','xmm3,xmm0'),(0x5d5fbe,'mulss','xmm3,xmm9'),(0x5d5fd8,'subss','xmm0,DWORD PTR [rbp+0x1fc]'),(0x5d5fec,'movss','DWORD PTR [rbp+0x1f8],xmm1'),(0x5d6006,'addss','xmm0,xmm3'),(0x5d6017,'subss','xmm1,xmm3'),(0x5d6024,'movss','DWORD PTR [r8+rcx*4],xmm0'),(0x5d602e,'movss','DWORD PTR [r9+rcx*4],xmm1')],
      'S=width*((L-R)/2 + d*(tapA-tapB)/2), optional first-order high-pass/DC recurrence on S; L_out=M+S,R_out=M-S. Two interpolated history taps. Mid history write at 0x5d5d3f; exact knob mappings remain.')
    add('delay','Stereo fractional delay interpolation and feedback routing',0x5d6a55,0x5d6bac,[
      (0x5d6a88,'subsd','xmm6,xmm0'),(0x5d6a9d,'subss','xmm9,DWORD PTR [r8+rdx*4]'),(0x5d6aad,'mulss','xmm9,xmm2'),(0x5d6ab8,'addss','xmm9,DWORD PTR [r8+rdx*4]'),(0x5d6acc,'addss','xmm6,DWORD PTR [r9+rdx*4]'),(0x5d6af0,'movss','DWORD PTR [rsi+0x1d4],xmm2'),(0x5d6b16,'subss','xmm2,xmm1'),(0x5d6b34,'movss','DWORD PTR [rsi+0x1d8],xmm3'),(0x5d6b65,'je','0x1805d6b90'),(0x5d6b7b,'movss','DWORD PTR [r8+rdi*4],xmm0'),(0x5d6b88,'movss','DWORD PTR [r9+rax*4],xmm2'),(0x5d6b99,'movss','DWORD PTR [r8+rdi*4],xmm2')],
      'Linear fractional ring read d=(1-t)*buf[i]+t*buf[i+1] per channel; two first-order smoothing stages in feedback path and selectable cross-channel versus ordinary write routing. Full coefficient/control mapping unresolved.',[(0x5d6a55,'floor')])
    add('reverb','Eight indexed modulated reverb lanes and bounded coloration',0x5d8ba7,0x5d8ec3,[
      (0x5d8c04,'mulss','xmm7,xmm6'),(0x5d8c18,'addss','xmm7,xmm1'),(0x5d8c2d,'movss','DWORD PTR [r14+rdi*4+0x344],xmm7'),(0x5d8c49,'movss','DWORD PTR [r14+rdi*4+0x364],xmm6'),(0x5d8c5c,'subss','xmm7,xmm6'),(0x5d8c93,'divss','xmm1,xmm0'),(0x5d8caa,'movss','DWORD PTR [rsp+rdi*4+0xb0],xmm8'),(0x5d8ea9,'add','esi,0x2'),(0x5d8eba,'cmp','esi,0x8'),(0x5d8ebd,'jl','0x1805d8a90')],
      'Modulated fractional delay taps, per-lane two-state damping, optional tanh normalization. Unrolled pair loop covers eight lane indices. Full feedback matrix and decay mapping not yet proven.',[(0x5d8ba7,'floorf'),(0x5d8c53,'powf'),(0x5d8c7d,'tanhf'),(0x5d8c8a,'tanhf')])
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'regions':regions,'checkpoint_count':sum(r['checkpoint_count'] for r in regions),'eq_branch_rvas':list(map(hex,table)),'constants':constants(pe,[(0x8e96ac,1),(0xa5b1ec,.49),(0x9143c0,math.pi),(0x974198,.025),(0x928a80,40),(0x909cdc,-2),(0x8e96a8,.5),(0x9143d8,4),(0x928a70,20)]),'limits':'Static local equations. No full plugin execution or complete EQ host mapping; no raw vendor coefficient arrays.'}


VMR_PATHS={
 'FG-116.epl':(0x160540,0x160759,0x16069f,0xd0,0x1606a6,0xfef548,0x1619a0,0x162418,[(0x161b26,'subsd','xmm0,xmm2'),(0x161b2a,'mulsd','xmm0,xmm7'),(0x161b2e,'addsd','xmm2,xmm0'),(0x161b39,'mulsd','xmm0,QWORD PTR [rdx]'),(0x161b45,'movsd','QWORD PTR [rcx],xmm0'),(0x161bd9,'movsd','QWORD PTR [r10+0x8],xmm2')],'Smoothed scalar gain multiplication: g+=alpha*(target-g); y=x*g; per-lane gain state written back.'),
 'FG-2A.epl':(0x1561c0,0x1563d9,0x15631f,0x190,0x156326,0x1008518,0x156b20,0x156ffb,[(0x156dd4,'mulsd','xmm0,QWORD PTR [rbx+0x1300]'),(0x156ddc,'addsd','xmm0,QWORD PTR [rbx+0x12e0]'),(0x156de4,'movsd','QWORD PTR [rax+rdx*8],xmm0'),(0x156de9,'mulsd','xmm0,QWORD PTR [rbx+0x1318]'),(0x156df8,'mulsd','xmm1,QWORD PTR [rbx+0x1308]'),(0x156e00,'subsd','xmm1,xmm0'),(0x156e04,'movsd','QWORD PTR [rbx+0x12e0],xmm1'),(0x156e83,'mulsd','xmm0,QWORD PTR [rbx+0x1340]'),(0x156e8b,'addsd','xmm0,QWORD PTR [rbx+0x1320]'),(0x156eb4,'movsd','QWORD PTR [rbx+0x1320],xmm1')],'Two distinct stereo double-precision first-order filter passes: y=b0*x+z; z_next=b1*x-a1*y. Coefficient meanings and full optical gain law unknown.'),
 'FG-Stress.epl':(0x160a30,0x160c49,0x160b8f,0x360,0x160b96,0x1014588,0x162790,0x1638b6,[(0x163460,'movsd','xmm2,QWORD PTR [r12+0x390]'),(0x163480,'andps','xmm1,xmm4'),(0x163488,'andps','xmm0,xmm4'),(0x16348b,'maxsd','xmm1,xmm0'),(0x16348f,'subsd','xmm2,xmm1'),(0x163493,'mulsd','xmm2,QWORD PTR [r12+0x3a0]'),(0x16349d,'addsd','xmm2,xmm1'),(0x1634a1,'maxsd','xmm2,xmm1'),(0x1634a5,'movsd','QWORD PTR [r12+0x390],xmm2'),(0x163509,'movsd','QWORD PTR [rbp+rdx*1+0xa40],xmm2')],'Linked peak recurrence P=max(p,p+a*(P_prev-p)); p=max(abs(L),abs(R)). Then two bounded threshold-relative control calculations; their full effect not yet established.')}


def verify_vmr_paths(pe,objdump='objdump'):
    if pe.path.name not in VMR_PATHS or pe.sha256!=VMR_COPY[pe.path.name][0]:raise ValueError('Unexpected VMR source fingerprint')
    start,end,selector,offset,site,table,target,stop,checks,equation=VMR_PATHS[pe.path.name]
    ins=disassemble(pe,start,end-start,objdump)
    by={i.address-pe.image_base:i for i in ins}
    sel=by[selector]
    if sel.mnemonic!='movsxd' or not sel.operands.startswith('rdx,DWORD PTR [rax+'):raise ValueError('Unexpected selector')
    if sel.operands!=f'rdx,DWORD PTR [rax+{hex(offset)}]':raise ValueError('Unexpected selector offset')
    if by[site].text!='call QWORD PTR [r15+rdx*8]':raise ValueError('Unexpected indirect call')
    if not any(i.mnemonic=='lea' and i.operands.startswith('r15,[rip') and i.operands.endswith(hex(pe.image_base+table)) for i in ins):raise ValueError('Unexpected table reference')
    slots=pointer_slots(pe,table,6)
    if any(slots[j]['target_rva']!=hex(target) for j in (4,5)):raise ValueError('Unexpected candidate path')
    region=check_region(pe,target,stop,checks,objdump=objdump)
    calls=direct_calls(pe,disassemble(pe,target,stop-target,objdump))
    candidate={'id':'effect_candidate','title':'Shared slot 4/5 processing candidate','equation':equation,**region,'direct_calls':calls}
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'regions':[candidate],'wrapper_rva':hex(start),'table_rva':hex(table),'selector_instruction_rva':hex(selector),'selector_field':sel.operands,'indirect_call_rva':hex(site),'explicit_slots':slots,'candidate':candidate,'limits':'Only six explicit slots inspected. No assertion of table length, runtime selection, coefficient mapping or complete compression law.'}
