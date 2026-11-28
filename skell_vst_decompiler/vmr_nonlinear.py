"""Exact-build local DSP arithmetic and static call links, never executes source binaries.

No raw instructions, vendor coefficient arrays or complete vendor processors exported.
"""
import argparse
import json
import struct
from .pe import PE
from .extended_dsp import VMR_COPY, check_region
from .rack_paths import pointer_slots
from .disasm import disassemble, direct_calls


def verify(pe, objdump='objdump'):
    name = pe.path.name
    if name not in ('FG-116.epl','FG-2A.epl','FG-Stress.epl') or pe.sha256 != VMR_COPY[name][0]:
        raise ValueError('Unsupported source fingerprint')
    regions, constants, dispatches = [], {}, []
    def constant(rva, expected):
        if pe.at_rva(rva,8) != struct.pack('<d',expected):
            raise ValueError(f'Unexpected constant at {rva:#x}')
        constants[hex(rva)] = expected
    def add(key,title,start,end,checks,equation,confidence='instruction-verified local arithmetic; runtime dispatch unverified'):
        result=check_region(pe,start,end,checks,objdump=objdump)
        calls=direct_calls(pe,disassemble(pe,start,end-start,objdump))
        regions.append({'id':key,'title':title,'equation':equation,'confidence':confidence,
                        'direct_calls':calls,**result})
    def table(rva,expected):
        slots=pointer_slots(pe,rva,len(expected))
        if [int(s['target_rva'],16) for s in slots]!=expected or not all(s['executable_file_backed'] for s in slots):
            raise ValueError(f'Unexpected dispatch slots at {rva:#x}')
        dispatches.append({'table_rva':hex(rva),'slots':slots,'note':'Inspected entries only; runtime selector not recovered.'})
    if name=='FG-116.epl':
        constant(0xe7dc60,-0.0);constant(0xe7cd88,1.0);constant(0xe979a8,.046774);constant(0xe979a0,.053088)
        add('fg116_clamped_state_setup','FG-116 clamped-state coefficient and bounds setup',0x15e732,0x15e88c,[
            (0x15e732,'movsd','xmm12,QWORD PTR [r14+0x160]'),(0x15e742,'movsd','xmm13,QWORD PTR [r14+0x168]'),
            (0x15e74f,'movsd','xmm14,QWORD PTR [r14+0x170]'),(0x15e75b,'movsd','xmm15,QWORD PTR [rip+0xd1f4fc]'),
            (0x15e764,'xorps','xmm9,xmm9'),(0x15e768,'movsd','xmm10,QWORD PTR [rip+0xd1e617]'),
            (0x15e7c4,'movsd','xmm3,QWORD PTR [rbx+0x60]'),(0x15e7d0,'movsd','xmm6,QWORD PTR [rip+0xd391d0]'),
            (0x15e7dc,'movsd','xmm11,QWORD PTR [rip+0xd391bb]'),(0x15e821,'xorps','xmm7,xmm15')],
            'Loads coefficients a, k1, k0 at offsets 0x160/168/170, previous state at channel record +0x60, and signed clamp bounds from file-backed constants.')
        add('fg116_clamped_integrator','FG-116 clamped two-output integrator and branch-dependent coefficient',0x15eaa1,0x15eb40,[
            (0x15eab8,'xorps','xmm11,xmm15'),(0x15eabf,'movsd','xmm4,QWORD PTR [r9+rdx*1]'),
            (0x15eac9,'subsd','xmm4,xmm3'),(0x15ead0,'minsd','xmm0,xmm3'),(0x15ead4,'mulsd','xmm4,xmm12'),
            (0x15ead9,'maxsd','xmm1,xmm0'),(0x15eadd,'subsd','xmm3,xmm1'),(0x15eae4,'addsd','xmm5,xmm4'),
            (0x15eae8,'ucomisd','xmm3,xmm9'),(0x15eaef,'jne','0x18015eaf5'),(0x15eaf1,'xor','eax,eax'),
            (0x15eaf5,'mov','eax,0x1'),(0x15eb06,'movsd','QWORD PTR [r10+rdx*1],xmm5'),
            (0x15eb0c,'movaps','xmm3,xmm5'),(0x15eb0f,'subsd','xmm2,xmm1'),(0x15eb13,'movsd','QWORD PTR [rcx+rdx*1],xmm1'),
            (0x15eb1b,'addsd','xmm3,xmm4'),(0x15eb1f,'mulsd','xmm0,xmm13'),(0x15eb24,'mulsd','xmm2,xmm14'),
            (0x15eb29,'addsd','xmm2,xmm0'),(0x15eb2d,'movsd','QWORD PTR [rdx],xmm2'),(0x15eb3b,'movsd','QWORD PTR [rbx+0x60],xmm3')],
            'Finite input/state: c=clamp(s,-0.053088,0.046774); d=a*(x-s); q=c+d; s_next=c+2*d; flag=(s!=c); k=(1-flag)*k0+flag*k1. q, flag, and k enter separate scratch arrays. No physical circuit or knob interpretation asserted.')
        add('fg116_selected_retention','FG-116 minimum envelope of selected coefficients',0x15eb40,0x15ec87,[
            (0x15eb47,'movsd','xmm4,QWORD PTR [r14+0x178]'),(0x15eb50,'lea','rdx,[rbp-0x80]'),
            (0x15ec5a,'movsd','xmm0,QWORD PTR [rdx+rcx*1]'),(0x15ec5f,'movsd','xmm1,QWORD PTR [rbx+0x58]'),
            (0x15ec64,'subsd','xmm1,xmm0'),(0x15ec68,'mulsd','xmm1,xmm4'),(0x15ec6c,'addsd','xmm1,xmm0'),
            (0x15ec70,'minsd','xmm1,xmm0'),(0x15ec74,'movsd','QWORD PTR [rbx+0x58],xmm1'),(0x15ec79,'movsd','QWORD PTR [rcx],xmm1')],
            'The branch-selected k stream feeds k_s=min(k,k+a_r*(k_s_prev-k)), using retention field 0x178 and channel state +0x58.')
        add('fg116_variable_integrator','FG-116 variable-coefficient state and residual output',0x15ec87,0x15edb0,[
            (0x15ec87,'movsd','xmm3,QWORD PTR [rbx+0x68]'),(0x15ec8c,'lea','rcx,[rbp+0x2b0]'),
            (0x15ed88,'movsd','xmm1,QWORD PTR [rsi+rcx*1]'),(0x15ed8d,'subsd','xmm1,xmm3'),
            (0x15ed94,'movsd','QWORD PTR [rdx+rcx*1],xmm1'),(0x15ed99,'mulsd','xmm0,QWORD PTR [rcx]'),
            (0x15eda1,'addsd','xmm3,xmm0'),(0x15edab,'movsd','QWORD PTR [rbx+0x68],xmm3')],
            'The smoothed k stream feeds an independent state: e=x-v; v_next=v+k_s*e. Writes residual e to scratch and stores v at channel state +0x68. Local signal path, not a complete compressor gain equation.')
    elif name=='FG-Stress.epl':
        add('stress_piecewise','FG-Stress affine/quadratic/identity nonlinear branch',0x163270,0x1632f9,[
            (0x16327e,'movsd','xmm1,QWORD PTR [rbx+rdi*1]'),(0x163283,'comisd','xmm1,QWORD PTR [r15+0xd0]'),
            (0x16328c,'jae','0x1801632d7'),(0x16328e,'comisd','xmm1,QWORD PTR [r15+0xc8]'),(0x163297,'jb','0x1801632c5'),
            (0x16329c,'mulsd','xmm0,QWORD PTR [r15+0xe8]'),(0x1632a5,'mulsd','xmm0,xmm1'),
            (0x1632a9,'mulsd','xmm1,QWORD PTR [r15+0xf0]'),(0x1632b2,'addsd','xmm0,xmm1'),
            (0x1632b6,'addsd','xmm0,QWORD PTR [r15+0xf8]'),(0x1632bf,'movsd','QWORD PTR [rbx],xmm0'),
            (0x1632c3,'jmp','0x1801632db'),(0x1632c5,'mulsd','xmm1,QWORD PTR [r15+0xd8]'),
            (0x1632ce,'addsd','xmm1,QWORD PTR [r15+0xe0]'),(0x1632d7,'movsd','QWORD PTR [rbx],xmm1'),
            (0x1632f4,'call','0x18006f840')],
            'Ordered finite thresholds lo<=hi: F(x)=x for x>=hi, A*x+B for x<lo, C*x*x+D*x+E otherwise. Coefficients at object offsets 0xd8..0xf8; continuity, target parameter mapping and gain-law role unknown.')
        add('stress_curve_caller','FG-Stress nonlinear scratch flow into downstream effect routine',0x163300,0x1633f6,[
            (0x163300,'mov','rdi,QWORD PTR [rbp+rsi*8+0x2b0]'),(0x163308,'mov','rbx,QWORD PTR [rbp+rsi*8+0xa20]'),
            (0x163332,'mov','rcx,rdi'),(0x163335,'call','0x18006f8a0'),(0x163343,'call','0x18006f9c0'),
            (0x16335e,'call','0x18006f800'),(0x1633a4,'mov','rax,QWORD PTR [rbp+0xa20]'),
            (0x1633af,'mov','rax,QWORD PTR [rbp+0x2b0]'),(0x1633f1,'call','0x18015d420')],
            'The transformed channel stream is consumed by subsequent vector calls and is passed alongside derived scratch buffers to the downstream candidate at 0x15d420. Its complete effect on output has not been proven.')
    else:
        constant(0xea9448,1.0);constant(0xeaa4b8,-1.0)
        add('fg2a_signed_curve','FG-2A signed biased piecewise quadratic and plateau',0x14d9c1,0x14da5e,[
            (0x14d9d2,'movsd','xmm0,QWORD PTR [rcx+r8*1]'),(0x14d9d8,'addsd','xmm0,QWORD PTR [rbx+0x228]'),
            (0x14d9e0,'comisd','xmm0,xmm5'),(0x14d9e4,'jb','0x18014d9eb'),(0x14d9e6,'movaps','xmm3,xmm6'),
            (0x14d9eb,'movaps','xmm3,xmm4'),(0x14d9f1,'mulsd','xmm2,xmm0'),(0x14d9f5,'movsd','xmm0,QWORD PTR [rbx+0x1f0]'),
            (0x14d9fd,'comisd','xmm0,xmm2'),(0x14da01,'jae','0x18014da40'),(0x14da03,'comisd','xmm2,QWORD PTR [rbx+0x1f8]'),
            (0x14da0b,'jbe','0x18014da17'),(0x14da0d,'movsd','xmm2,QWORD PTR [rbx+0x208]'),
            (0x14da1d,'mulsd','xmm0,QWORD PTR [rbx+0x218]'),(0x14da25,'mulsd','xmm1,xmm2'),
            (0x14da29,'mulsd','xmm1,QWORD PTR [rbx+0x210]'),(0x14da34,'addsd','xmm2,xmm0'),
            (0x14da38,'addsd','xmm2,QWORD PTR [rbx+0x220]'),(0x14da40,'mulsd','xmm2,xmm3'),
            (0x14da44,'subsd','xmm2,QWORD PTR [rbx+0x230]'),(0x14da4c,'movsd','QWORD PTR [rcx],xmm2')],
            'u=x+bias; p=abs(u); F(p)=p if p<=lo, plateau if p>hi and p>lo, A*p*p+B*p+C otherwise; v=sign(u)*F(p)-offset (sign(0)=+1). Finite values only. Exact runtime coefficients and physical purpose unknown.')
        add('fg2a_curve_sign_setup','FG-2A signed curve constant setup',0x14d748,0x14d76d,[
            (0x14d748,'movsd','xmm6,QWORD PTR [rip+0xd5bcf8]'),(0x14d757,'movsd','xmm4,QWORD PTR [rip+0xd5cd59]'),(0x14d766,'xorps','xmm5,xmm5')],
            'Loads +1, -1 and zero used for sign and absolute magnitude in the piecewise branch.')
        add('fg2a_even_power_chain','FG-2A even-power nonlinear polynomial candidate',0x14da5e,0x14db2d,[
            (0x14da61,'lea','rdx,[rbp+0x990]'),(0x14da68,'lea','rcx,[rbp+0x790]'),(0x14da6f,'call','0x180075f40'),
            (0x14da77,'lea','rdx,[rbp+0xb90]'),(0x14da7e,'lea','rcx,[rbp+0x990]'),(0x14da85,'call','0x180075f40'),
            (0x14da8d,'lea','r8,[rbp+0xfb0]'),(0x14da94,'lea','rdx,[rbp+0x990]'),(0x14da9b,'lea','rcx,[rbp+0xb90]'),(0x14daa2,'call','0x18006f8a0'),
            (0x14daaa,'lea','rdx,[rsp+0x50]'),(0x14daaf,'lea','rcx,[rbp+0xb90]'),(0x14dab6,'call','0x180075f40'),
            (0x14dabb,'movsd','xmm0,QWORD PTR [rbx+0x578]'),(0x14dacb,'call','0x18006f7e0'),
            (0x14dad0,'movsd','xmm0,QWORD PTR [rbx+0x568]'),(0x14dae2,'call','0x18006f7e0'),(0x14daf6,'call','0x18006f840'),
            (0x14dafb,'movsd','xmm1,QWORD PTR [rbx+0x560]'),(0x14db0d,'lea','rcx,[rbp+0xb90]'),(0x14db14,'call','0x18006f820'),(0x14db28,'call','0x18006f840')],
            'On the inspected scalar helper dispatch paths: v2=v*v; v4=v2*v2; v6=v4*v2; v8=v4*v4; p=A*v4+B*v6+C*v8. Coefficients are fields 0x560,0x568,0x578. All seven square slots checked; scalar candidate multiply/scale/add semantics established, not every alternative helper slot. Not claimed to be the final gain computer.',
            'instruction-verified call/argument chain with inspected helper candidates; runtime selector unverified')
        table(0x10160e0,[0x75f60,0x75f80,0x75fa0,0x75fc0,0x75fe0,0x76000,0x76020])
        for a,b in [(0x1016120,0x76040),(0x1016148,0x760a0),(0x1016170,0x760a0),(0x1016198,0x760a0),(0x10161c0,0x76440),(0x10161e8,0x767a0)]:table(a,[b])
        add('fg2a_square_dispatch','FG-2A square dispatcher and seven forwarding entries',0x75f40,0x76030,[
            (0x75f40,'movsxd','rax,DWORD PTR [rip+0xfebf0d]'),(0x75f47,'lea','r11,[rip+0xfa0192]'),(0x75f4e,'jmp','QWORD PTR [r11+rax*8]'),
            (0x75f64,'mov','rax,QWORD PTR [rip+0xfa01b5]'),(0x75f84,'mov','rax,QWORD PTR [rip+0xfa01bd]'),
            (0x75fa4,'mov','rax,QWORD PTR [rip+0xfa01c5]'),(0x75fc5,'mov','rax,QWORD PTR [rip+0xfa01a4]'),
            (0x75fe4,'mov','rax,QWORD PTR [rip+0xfa01ad]'),(0x76004,'mov','rax,QWORD PTR [rip+0xfa01b5]'),(0x76024,'mov','rax,QWORD PTR [rip+0xfa01bd]')],
            'Seven explicit dispatch slots lead through forwarding stubs to four file-backed square candidate routines.')
        add('fg2a_square_kernels','FG-2A scalar, SSE, AVX square arithmetic',0x76040,0x76a90,[
            (0x76065,'movsd','xmm0,QWORD PTR [rcx+rax*8]'),(0x7606a,'mulsd','xmm0,xmm0'),(0x7606e,'movsd','QWORD PTR [rdx+rax*8],xmm0'),
            (0x761a5,'mulsd','xmm0,xmm0'),(0x761d5,'mulpd','xmm0,xmm0'),(0x76548,'vmulsd','xmm1,xmm0,xmm0'),
            (0x76566,'vmulpd','ymm1,ymm0,ymm0'),(0x768c8,'vmulpd','ymm5,ymm3,ymm3'),(0x76936,'vmulpd','ymm0,ymm2,ymm2')],
            'All four candidate entry routines contain scalar or packed self-multiplication; the scalar body explicitly stores x*x. No claim of runtime dispatch selection.')
        for title,rva,t,first,start,end,checks,eq in [
            ('In-place scalar multiply',0x6f7e0,0x1015e78,0x716b0,0x7173d,0x7174e,[(0x7173d,'movsd','xmm1,QWORD PTR [r10]'),(0x71745,'mulsd','xmm1,xmm0'),(0x71749,'movsd','QWORD PTR [r10],xmm1')],'dst*=scalar'),
            ('In-place vector sum',0x6f840,0x1015f20,0x72710,0x7277b,0x7278d,[(0x7277b,'movsd','xmm0,QWORD PTR [r9+r11*8]'),(0x72781,'addsd','xmm0,QWORD PTR [rdx+r11*8]'),(0x72787,'movsd','QWORD PTR [rdx+r11*8],xmm0')],'dst+=src'),
            ('Vector multiply',0x6f8a0,0x1015fc8,0x73500,0x73571,0x73583,[(0x73571,'movsd','xmm0,QWORD PTR [rcx+r11*8]'),(0x73577,'mulsd','xmm0,QWORD PTR [rdx+r11*8]'),(0x7357d,'movsd','QWORD PTR [r8+r11*8],xmm0')],'dst=src1*src2'),
            ('Out-of-place scalar multiply',0x6f820,0x1015ee8,0x72110,0x721a1,0x721b0,[(0x721a1,'movsd','xmm0,QWORD PTR [rcx+rdx*8]'),(0x721a6,'mulsd','xmm0,xmm1'),(0x721aa,'movsd','QWORD PTR [r8+rdx*8],xmm0')],'dst=src*scalar')]:
            table(t,[first]);ins=disassemble(pe,rva,18,objdump)
            if len(ins)!=3 or ins[-1].text!='jmp QWORD PTR [r11+rax*8]' or f'# {pe.image_base+t:#x}' not in ins[1].operands:
                raise ValueError('Unexpected helper dispatcher')
            add(f'fg2a_helper_{rva:x}',title,start,end,checks,eq+' for inspected first dispatch slot; other slots not established.')
        add('fg2a_biquad_after_polynomial','FG-2A post-polynomial DF2T filter',0x14db50,0x14dbbb,[
            (0x14db50,'movsd','xmm2,QWORD PTR [rbp+rax*8+0x390]'),(0x14db5f,'mulsd','xmm1,QWORD PTR [rbx+0x360]'),
            (0x14db67,'addsd','xmm1,QWORD PTR [rbx+0x320]'),(0x14db6f,'movsd','QWORD PTR [rsp+rax*8+0x50],xmm1'),
            (0x14db75,'mulsd','xmm0,QWORD PTR [rbx+0x368]'),(0x14db7d,'mulsd','xmm1,QWORD PTR [rbx+0x380]'),
            (0x14db85,'addsd','xmm0,QWORD PTR [rbx+0x328]'),(0x14db8d,'subsd','xmm0,xmm1'),(0x14db91,'movsd','QWORD PTR [rbx+0x320],xmm0'),
            (0x14db99,'mulsd','xmm2,QWORD PTR [rbx+0x370]'),(0x14dba1,'movsd','xmm0,QWORD PTR [rbx+0x388]'),
            (0x14dbaf,'subsd','xmm2,xmm0'),(0x14dbb3,'movsd','QWORD PTR [rbx+0x328],xmm2')],
            'Standard double DF2T recurrence follows the even-power sum scratch; coefficients 0x360/368/370/380/388. Frequency response, actual runtime values and ultimate role remain unknown.')
    return {'schema_version':1,'source':name,'binary_sha256':pe.sha256,'regions':regions,'constants':constants,'dispatches':dispatches,
            'checkpoint_count':sum(r['checkpoint_count'] for r in regions),'limits':'Local arithmetic and candidate helper paths, not complete vendor source or runtime gain laws.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary');p.add_argument('--objdump',default='objdump');a=p.parse_args()
    print(json.dumps(verify(PE(a.binary),a.objdump),indent=2,allow_nan=False))

if __name__=='__main__':main()
