"""Exact-build TVB reverb evidence, no executable or calibration arrays exported."""
import json
import math
import struct
import argparse
from .pe import PE
from .equations import TVB_SHA256
from .extended_dsp import check_region, constants


def verify_reverb(pe, objdump='objdump'):
    if pe.sha256 != TVB_SHA256:
        raise ValueError('Unexpected source fingerprint')
    regions = []
    def add(id, title, start, end, checks, equation, imports=()):
        regions.append({'id': id, 'title': title, 'equation': equation,
                        'confidence': 'exact-source local instruction evidence; runtime unverified',
                        **check_region(pe, start, end, checks, imports, objdump)})
    add('input_diffusion', 'Four serial allpass-shaped diffusion cells', 0x5d861e, 0x5d8689, [
        (0x5d861e,'lea','rax,[r14+0x1b0]'),(0x5d8625,'lea','r8,[rax+0x80]'),
        (0x5d864d,'mulss','xmm0,xmm4'),(0x5d8651,'movss','xmm2,DWORD PTR [rax+rcx*4]'),
        (0x5d8656,'subss','xmm2,xmm0'),(0x5d865a,'mulss','xmm1,xmm2'),
        (0x5d865e,'addss','xmm1,xmm4'),(0x5d8662,'movaps','xmm4,xmm2'),
        (0x5d8665,'movss','DWORD PTR [rax+rcx*4],xmm1'),(0x5d867a,'add','rdx,0x20')],
        'Each of four 32-byte cells reads d, computes y=d-k*x, writes x+k*y, passes y to the next cell. Delay lengths and k range not established here.')
    add('decay_setup','Decay-duration denominator and input sample-rate field',0x5d8000,0x5d8078,[
        (0x5d801d,'mov','eax,DWORD PTR [r14+0x158]'),(0x5d803f,'movd','xmm0,eax'),
        (0x5d8043,'maxss','xmm0,DWORD PTR [rip+0x331ba5]'),(0x5d8057,'movss','DWORD PTR [rsp+0x58],xmm0')],
        'T=max(field_0x158,0.1). The UI-to-field mapping is not established by this check.')
    add('lane_decay','Per-lane RT60-style decay factor and optional bounded coloration',0x5d8a90,0x5d8cb4,[
        (0x5d8a90,'movss','xmm0,DWORD PTR [rbp+rdi*4+0xa5c870]'),
        (0x5d8a9d,'movss','xmm8,DWORD PTR [rbp+rdi*4+0xa5c890]'),
        (0x5d8aa9,'subss','xmm8,xmm0'),(0x5d8aae,'mulss','xmm8,xmm10'),(0x5d8ab3,'addss','xmm8,xmm0'),
        (0x5d8ab8,'mulss','xmm8,xmm15'),(0x5d8abd,'movaps','xmm7,xmm8'),
        (0x5d8ac1,'mulss','xmm7,DWORD PTR [rsp+0x24]'),(0x5d8bac,'mulss','xmm8,DWORD PTR [rip+0x4825fb]'),
        (0x5d8bc6,'divss','xmm8,DWORD PTR [rsp+0x58]'),(0x5d8bf0,'movss','xmm0,DWORD PTR [rsp+0x4c]'),
        (0x5d8bf6,'mulss','xmm0,DWORD PTR [r14+rdi*4+0x344]'),(0x5d8c20,'mulss','xmm7,DWORD PTR [rsp+0x48]'),
        (0x5d8c26,'addss','xmm7,xmm0'),(0x5d8c2d,'movss','DWORD PTR [r14+rdi*4+0x344],xmm7'),
        (0x5d8c0e,'mulss','xmm6,DWORD PTR [r14+rdi*4+0x364]'),(0x5d8c37,'mulss','xmm0,DWORD PTR [rsp+0x54]'),
        (0x5d8c3d,'addss','xmm6,xmm0'),(0x5d8c49,'movss','DWORD PTR [r14+rdi*4+0x364],xmm6'),
        (0x5d8c1c,'movaps','xmm1,xmm8'),(0x5d8c41,'movss','xmm0,DWORD PTR [rip+0x33104f]'),
        (0x5d8c5c,'subss','xmm7,xmm6'),(0x5d8c6d,'mulss','xmm8,xmm7'),
        (0x5d8c74,'mulss','xmm8,xmm9'),(0x5d8c86,'movaps','xmm0,xmm9'),(0x5d8c93,'divss','xmm1,xmm0'),
        (0x5d8c97,'mulss','xmm8,xmm1')],
        'Base delay seconds d=lerp(two delay anchors,morph)*scale; base delay samples=d*Fs before modulation. Two one-pole states p=a*p_old+(1-a)*tap, q=b*q_old+(1-b)*p; feedback lane v=(p-q)*10^(-3*d/T). Optional nonlinear v=tanh(h*v)/tanh(h). Actual broadband decay depends on damping, modulation and nonlinear processing.',
        [(0x5d8b20,'sinf'),(0x5d8ba7,'floorf'),(0x5d8c53,'powf'),(0x5d8c7d,'tanhf'),(0x5d8c8a,'tanhf')])
    # Confirm that the complement coefficients are indeed 1-a and 1-b.
    add('damping_complements','Damping setup and complementary one-pole coefficients',0x5d80d6,0x5d82bc,[
        (0x5d80d6,'mulss','xmm2,DWORD PTR [rip+0x33c3b2]'),(0x5d80de,'divss','xmm2,xmm14'),
        (0x5d80f7,'movss','DWORD PTR [rsp+0x4c],xmm8'),(0x5d80eb,'mulss','xmm7,DWORD PTR [rip+0x33c39d]'),
        (0x5d80fe,'divss','xmm7,xmm14'),(0x5d811b,'movss','DWORD PTR [rsp+0x50],xmm7'),
        (0x5d8284,'movaps','xmm0,xmm12'),(0x5d828a,'subss','xmm0,xmm8'),
        (0x5d829d,'movss','DWORD PTR [rsp+0x48],xmm0'),(0x5d82a3,'movaps','xmm0,xmm12'),
        (0x5d82a7,'subss','xmm0,xmm7'),(0x5d82ab,'movss','DWORD PTR [rsp+0x54],xmm0')],
        'a=exp(-2*pi*f_a/Fs), b=exp(-2*pi*f_b/Fs). Complement weights 1-a and 1-b. Input cutoff-control mappings remain incomplete.',[(0x5d80e6,'expf'),(0x5d8106,'expf')])
    add('sum_all_lanes','Eight-lane accumulation',0x5d8a61,0x5d8ec3,[
        (0x5d8a61,'movaps','xmm14,xmm13'),(0x5d8ca5,'addss','xmm14,xmm8'),
        (0x5d8caa,'movss','DWORD PTR [rsp+rdi*4+0xb0],xmm8'),
        (0x5d8e9e,'addss','xmm14,xmm8'),(0x5d8ea9,'add','esi,0x2'),
        (0x5d8eac,'movss','DWORD PTR [rsp+rdi*4+0xb4],xmm8'),(0x5d8eb6,'add','rdi,0x2'),
        (0x5d8eba,'cmp','esi,0x8'),(0x5d8ebd,'jl','0x1805d8a90')],
        'Accumulate the eight per-lane values v_i and store them before feedback writes. xmm13 is zeroed in setup.')
    add('householder','Householder feedback mixing with alternating input polarity',0x5d9074,0x5d9218,[
        (0x5d907b,'movss','xmm1,DWORD PTR [rip+0x330b7d]'),(0x5d9083,'movss','xmm9,DWORD PTR [rsp+0xb0]'),
        (0x5d908d,'movss','xmm2,DWORD PTR [rsp+0x2c]'),(0x5d90d9,'xorps','xmm3,XMMWORD PTR [rip+0x330db0]'),
        (0x5d90e9,'mulss','xmm14,xmm1'),(0x5d90ee,'mulss','xmm3,xmm1'),(0x5d90f2,'subss','xmm0,xmm14'),
        (0x5d90f7,'mulss','xmm2,xmm1'),(0x5d90ff,'subss','xmm1,xmm14'),
        (0x5d9104,'addss','xmm0,xmm2'),(0x5d9108,'addss','xmm1,xmm2'),(0x5d910c,'movss','DWORD PTR [rax+rcx*4],xmm0'),
        (0x5d911c,'subss','xmm0,xmm14'),(0x5d9128,'addss','xmm0,xmm3'),(0x5d912c,'movss','DWORD PTR [rax+rcx*4],xmm0'),
        (0x5d913b,'subss','xmm0,xmm14'),(0x5d914f,'movss','DWORD PTR [rax+rcx*4],xmm1'),(0x5d9154,'addss','xmm0,xmm3'),
        (0x5d9169,'subss','xmm1,xmm14'),(0x5d916e,'movss','DWORD PTR [rax+rcx*4],xmm0'),(0x5d917d,'subss','xmm0,xmm14'),
        (0x5d9189,'addss','xmm1,xmm2'),(0x5d918d,'addss','xmm0,xmm3'),(0x5d9191,'movss','DWORD PTR [rax+rcx*4],xmm1'),
        (0x5d91a0,'subss','xmm1,xmm14'),(0x5d91ac,'movss','DWORD PTR [rax+rcx*4],xmm0'),(0x5d91b1,'addss','xmm1,xmm2'),
        (0x5d91d7,'movss','DWORD PTR [rax+rcx*4],xmm1'),(0x5d91dc,'subss','xmm0,xmm14'),
        (0x5d91ef,'addss','xmm0,xmm3'),(0x5d91f3,'movss','DWORD PTR [rax+rcx*4],xmm0'),
        (0x5d920a,'and','eax,DWORD PTR [r14+0x318]'),(0x5d9211,'mov','DWORD PTR [r14+0x320],eax')],
        'For i=0..7, delay_write_i=v_i-(2/8)*sum(v)+(-1)^i*input/4. The linear matrix H=I-(2/8)11^T is orthogonal. Lane damping and input injection are separate; orthogonality alone does not prove whole-loop stability.')
    mask=struct.unpack('<I',pe.at_rva(0x909e90,4))[0]
    if mask!=0x80000000:raise ValueError('Expected sign-bit mask')
    phase_checks=[(0x5d8ec3,'movsd','xmm1,QWORD PTR [r14+0x180]'),(0x5d8edb,'movsd','xmm15,QWORD PTR [rip+0x3107cc]')]
    # All 8 state increments and wrap stores, not merely a single example.
    starts=[0x5d8ed3,0x5d8f0f,0x5d8f42,0x5d8f75,0x5d8fa8,0x5d8fdb,0x5d900e,0x5d9041]
    for i,start in enumerate(starts):
        div=start+(17 if i==0 else 8)
        field=hex(0x388+i*8)
        phase_checks.extend([(div,'divsd','xmm0,xmm1'),(div+4,'addsd',f'xmm0,QWORD PTR [r14+{field}]'),
                             (div+18,'movsd',f'QWORD PTR [r14+{field}],xmm0'),(div+29,'subsd','xmm0,xmm15'),
                             (div+34,'movsd',f'QWORD PTR [r14+{field}],xmm0')])
    add('modulation_phases','Eight separate phase accumulators with wrap',0x5d8ec3,0x5d9074,phase_checks,
        'phi_i <- phi_i+f_i/Fs; if phi_i>=1 subtract 1. Per-lane sine modulation. No vendor calibration arrays exported.')
    add('ducking','Input-linked ducking envelope and wet gain',0x5d924c,0x5d938b,[
        (0x5d9267,'andps','xmm3,xmm15'),(0x5d9270,'andps','xmm0,xmm15'),(0x5d927d,'maxss','xmm3,xmm0'),
        (0x5d929f,'movss','xmm2,DWORD PTR [r14+0x418]'),(0x5d92a8,'comiss','xmm3,xmm2'),
        (0x5d92b6,'movss','xmm1,DWORD PTR [rsp+0x8c]'),(0x5d92c1,'movss','xmm1,DWORD PTR [rsp+0x90]'),
        (0x5d92ce,'mulss','xmm2,xmm1'),(0x5d92d2,'subss','xmm0,xmm1'),(0x5d92d6,'mulss','xmm0,xmm3'),
        (0x5d92e4,'addss','xmm0,xmm2'),(0x5d92e8,'movss','DWORD PTR [r14+0x418],xmm0'),
        (0x5d9310,'mulss','xmm0,xmm1'),(0x5d9314,'maxss','xmm0,DWORD PTR [rip+0x34f7c0]'),
        (0x5d932e,'addss','xmm0,DWORD PTR [rip+0x48352e]'),(0x5d9336,'divss','xmm0,xmm1'),
        (0x5d934a,'minss','xmm2,xmm0'),(0x5d9351,'mulss','xmm1,DWORD PTR [rip+0x33099f]'),
        (0x5d9359,'mulss','xmm1,xmm2'),(0x5d9366,'mulss','xmm1,DWORD PTR [rip+0x33087e]'),
        (0x5d937b,'movaps','xmm8,xmm0'),(0x5d9381,'movaps','xmm8,xmm13'),(0x5d9387,'movaps','xmm8,xmm12')],
        'E=a*Eprev+(1-a)*max(abs(L),abs(R)), separate rise/fall coefficients. For positive E, d=max(-60,20*log10(E)); otherwise d=-60. u=clamp((d+35)/20,0,1). For positive duck amount q, reduction=-15*q*u dB, wet factor=10^(reduction/20) above -100 dB, otherwise zero. Nonpositive q gives unity. Host range of q remains unknown.',[(0x5d92fd,'log10f'),(0x5d9376,'powf')])
    add('wet_output','Wet highpass-shaped tone and additive output',0x5d93ef,0x5d9548,[
        (0x5d93f6,'subss','xmm7,xmm12'),(0x5d940a,'mulss','xmm6,xmm8'),
        (0x5d941a,'mulss','xmm0,DWORD PTR [r14+0x3c8]'),(0x5d9427,'mulss','xmm1,DWORD PTR [rsp+0x74]'),
        (0x5d942d,'addss','xmm1,xmm0'),(0x5d9435,'subss','xmm0,xmm1'),(0x5d9439,'movss','DWORD PTR [r14+0x3c8],xmm1'),
        (0x5d9442,'mulss','xmm0,xmm7'),(0x5d9446,'addss','xmm0,xmm11'),(0x5d9459,'call','0x1805d9a70'),
        (0x5d9494,'mulss','xmm2,DWORD PTR [rsp+0x74]'),(0x5d949a,'addss','xmm2,xmm1'),
        (0x5d94a6,'movss','DWORD PTR [r14+0x3cc],xmm2'),(0x5d94af,'mulss','xmm0,xmm7'),
        (0x5d94b3,'addss','xmm0,xmm10'),(0x5d94b8,'call','0x1805d9a70'),
        (0x5d9505,'mulss','xmm0,xmm9'),(0x5d9517,'addss','xmm0,DWORD PTR [rsp+0x78]'),
        (0x5d9523,'movss','DWORD PTR [rcx+rdx*4],xmm0'),(0x5d9536,'mulss','xmm6,xmm3'),
        (0x5d953e,'addss','xmm6,xmm14'),(0x5d9543,'movss','DWORD PTR [rcx+rdx*4],xmm6')],
        'One-pole state per wet channel, then wet+(tone-1)*(wet-state); pass to normalized tanh helper. Output is dry plus shaped wet multiplied by smoothed wet gain and duck factor. Exact host control mapping remains unverified.')
    add('wet_saturation','Output color helper',0x5d9a70,0x5d9ae8,[
        (0x5d9a74,'movss','xmm2,DWORD PTR [rip+0x33a820]'),(0x5d9a89,'comiss','xmm2,xmm8'),
        (0x5d9a8d,'jae','0x1805d9add'),(0x5d9a8f,'mulss','xmm8,DWORD PTR [rip+0x33a940]'),
        (0x5d9aaa,'addss','xmm8,xmm7'),(0x5d9ab3,'mulss','xmm0,xmm3'),
        (0x5d9ac8,'divss','xmm7,xmm0'),(0x5d9acc,'mulss','xmm6,xmm7'),(0x5d9ad5,'movaps','xmm0,xmm6')],
        'For color c>0.0001, h=1+4*c and y=tanh(h*x)/tanh(h); otherwise identity.',[(0x5d9ab7,'tanhf'),(0x5d9ac3,'tanhf')])
    if struct.unpack('<d',pe.at_rva(0x8e96b0,8))[0]!=1:raise ValueError('Unexpected wrap value')
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'regions':regions,
            'checkpoint_count':sum(r['checkpoint_count'] for r in regions),
            'constants':constants(pe,[(0x909c00,.25),(0x909bf0,.1),(0xa5b1b0,-3),(0x909c98,10),(0x914490,-2*math.pi),(0x8e96ac,1),(0x928a70,20),(0x928adc,-60),(0xa5c864,35),(0x909cf8,-15),(0x928ae8,-100),(0x909bec,.05),(0x91429c,.0001),(0x9143d8,4)]),
            'limits':'Verified local reverb algebra only. No full control mapping, vendor runtime measurement or claim of sound parity.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary');p.add_argument('--objdump',default='objdump');a=p.parse_args()
    print(json.dumps(verify_reverb(PE(a.binary),a.objdump),indent=2,allow_nan=False))

if __name__=='__main__':main()
