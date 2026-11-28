"""Exact-build TVB dynamics evidence. Read-only; never calls vendor code.

Short opcode checkpoints and constants support mathematical descriptions,
not a portable vendor implementation or a proof of the complete signal path.
"""
import hashlib
import math
from .disasm import disassemble, imported_call_sites
from .equations import TVB_SHA256

# Half-open RVA intervals, independently inspectable using the trace command.
REGIONS = [
    ('input_detector', 0x5d0740, 0x5d07bf, 'Input gain and channel iteration', 'instruction-verified', 'x_g = x * input_gain; store x_g; iterate channels'),
    ('peak_level', 0x5d1246, 0x5d12ef, 'Linked peak / level detector', 'instruction-verified', 'p=max_c(abs(filtered x_g)); e=p if p>e_old else e_old+a*(p-e_old); L=max(-90,20*log10(e)) for e>0, otherwise -90'),
    ('mode0_knee', 0x5d1b2c, 0x5d1bac, 'Conventional compressor target gain reduction', 'instruction-verified', 'u=L-T; s=1-1/R; K>0.001: 0 below -K/2; s*(u+K/2)^2/(2*K) inside knee; s*u above K/2. K<=0.001: max(0,u)*s'),
    ('dual_recovery', 0x5d1bac, 0x5d1c1b, 'Two independent gain-reduction states', 'instruction-verified', 'g_j <- g_j + alpha_j*(G-g_j); alpha_j selected by G>g_j; output max(g_1,g_2)'),
    ('single_recovery', 0x5d1c1b, 0x5d1c52, 'Single gain-reduction state', 'instruction-verified', 'g <- g + alpha*(G-g); attack alpha if G>g, release alpha otherwise'),
    ('gain_conversion', 0x5d1c9a, 0x5d1cd9, 'dB to linear multiplier', 'instruction-verified', 'gain=10^(-g/20) if -g>-100 dB; else zero; then two additional gain factors'),
    ('output_blend', 0x5d1ee1, 0x5d1f1e, 'Output gain and optional parallel blend', 'instruction-verified', 'y=out_gain*((1-m)*dry+m*processed) when blend flag is set; otherwise out_gain*processed'),
    ('time_helper', 0x5d22e0, 0x5d231c, 'Time-to-coefficient helper', 'instruction-verified', 'alpha=1-exp(-1/(0.001*t*F)); arguments t and F; no zero-time guard in helper'),
    ('attack_release_setup', 0x5d0379, 0x5d04f7, 'Attack/release coefficient construction', 'instruction-verified', 'mode 0 single alpha=1-exp(-1/(0.001*t*F)); auxiliary recovery coefficients use 0.08*F, 0.30*F, 1.50*F; mode 0 peak time uses 15 ms'),
    ('mode2_filter_bank', 0x5d07bf, 0x5d117e, 'Six groups of four detector biquads', 'instruction-verified-structure', 'six group inputs restart at x_g; p_j=max_c(w_j*abs(group_j(x_g))); each group has four two-state sections'),
    ('mode2_envelopes', 0x5d15be, 0x5d172e, 'Six parallel peak and power states', 'instruction-verified', 'P_j=max(decay*P_j,p_j); E_j=E_j+alpha*(p_j^2-E_j), j=0..5'),
    ('mode2_peak_rms', 0x5d172e, 0x5d17bf, 'First indexed peak/power blend', 'instruction-verified', 'Pdb=max(-90,20*log10(P)); Edb=max(-180,20*log10(2*E)); L=blend*Pdb+(1-blend)*max(-90,0.5*Edb) (nonpositive inputs use floors)'),
    ('mode1_lookup', 0x5d30b0, 0x5d3121, 'Indexed 61-point gain curve interpolation', 'instruction-verified-structure', 'u = input - origin; clamp endpoints; i=floor(u); y=C[i]+(u-i)*(C[i+1]-C[i]); row stride 244 bytes; runtime table values not recovered'),
    ('mode2_lookup', 0x5d1833, 0x5d18d6, 'Indexed 77-point gain curve interpolation', 'instruction-verified-structure', 'row stride 308 bytes; clamp endpoints; i=floor(u); y=C[i]+(u-i)*(C[i+1]-C[i]); runtime table values not recovered'),
    ('knee_helper', 0x5d3130, 0x5d31a3, 'Standalone soft-knee helper', 'instruction-verified-structure', 'same quadratic knee motif as mode0_knee; exact caller relationships not established'),
    ('mode1_custom', 0x5d12f9, 0x5d15b4, 'Alternate gain curve and adaptive state', 'partial', 'table interpolation and two coupled state updates; complete curve and control mapping unresolved'),
]
# Exact operand checks, not merely mnemonic counts. Region-specific checks
# make earlier mistakes (e.g. treating six banks as 24 serial stages) visible.
CHECKS = [
 (0x5cfb0e,'xorps','xmm10,xmm10'),(0x5cfb29,'movss','xmm9,DWORD PTR [rip+0x319b7a]'),
 (0x5cfe3f,'movsd','xmm1,QWORD PTR [rsi+0x198]'),(0x5cfe87,'cvtpd2ps','xmm8,xmm1'),
 (0x5cfb08,'mov','ecx,DWORD PTR [rcx+0x150]'),(0x5cfb12,'mov','eax,DWORD PTR [rsi+0x154]'),(0x5cfb3c,'mov','DWORD PTR [rbp-0x40],eax'),
 (0x5cfc5c,'movss','DWORD PTR [rsp+0x38],xmm1'),(0x5cfc6b,'movss','DWORD PTR [rsp+0x38],xmm1'),(0x5cfc86,'movss','DWORD PTR [rsp+0x3c],xmm13'),
 (0x5d07b5,'cmp','r12d,0x2'),(0x5d07b9,'jne','0x1805d117e'),(0x5d12ef,'cmp','r12d,0x1'),(0x5d12f3,'jne','0x1805d15b4'),(0x5d15b4,'cmp','r12d,0x2'),(0x5d15b8,'jne','0x1805d1b2c'),
 (0x5d07a9,'mulss','xmm7,DWORD PTR [rax+r14*4]'),(0x5d07af,'movss','DWORD PTR [rax+r14*4],xmm7'),
 (0x5d124c,'andps','xmm7,xmm6'),(0x5d1255,'maxss','xmm7,xmm8'),(0x5d1266,'jl','0x1805d07a0'),
 (0x5d128e,'movss','xmm1,DWORD PTR [rsi+0x200]'),(0x5d129e,'ja','0x1805d12ad'),(0x5d12a0,'subss','xmm0,xmm1'),(0x5d12a4,'mulss','xmm0,DWORD PTR [rbp-0x30]'),(0x5d12a9,'addss','xmm0,xmm1'),(0x5d12b1,'movss','DWORD PTR [rsi+0x200],xmm0'),(0x5d12d8,'mulss','xmm1,xmm11'),(0x5d12dd,'maxss','xmm1,xmm7'),
 (0x5d1b2c,'movss','xmm3,DWORD PTR [rbp-0x40]'),(0x5d1b35,'divss','xmm0,DWORD PTR [rsp+0x3c]'),(0x5d1b3b,'subss','xmm1,DWORD PTR [rsp+0x38]'),(0x5d1b45,'subss','xmm2,xmm0'),(0x5d1b54,'jae','0x1805d1b9c'),(0x5d1b64,'jae','0x1805d1b9c'),(0x5d1b74,'jb','0x1805d1b7c'),(0x5d1b76,'mulss','xmm1,xmm2'),(0x5d1b7c,'addss','xmm0,xmm1'),(0x5d1b83,'mulss','xmm1,xmm2'),(0x5d1b87,'mulss','xmm1,xmm0'),(0x5d1b96,'divss','xmm1,xmm0'),(0x5d1ba0,'jbe','0x1805d1ba8'),(0x5d1ba8,'movaps','xmm1,xmm10'),
 (0x5d1bb3,'movss','xmm0,DWORD PTR [rsi+0x208]'),(0x5d1bc5,'jbe','0x1805d1bcf'),(0x5d1bc7,'mulss','xmm2,DWORD PTR [rsp+0x74]'),(0x5d1bcf,'mulss','xmm2,DWORD PTR [rbp-0x3c]'),(0x5d1bd4,'addss','xmm2,xmm0'),(0x5d1bdb,'movss','DWORD PTR [rsi+0x208],xmm2'),(0x5d1be3,'movss','xmm3,DWORD PTR [rsi+0x20c]'),(0x5d1bf2,'jbe','0x1805d1bfb'),(0x5d1bf4,'mulss','xmm0,DWORD PTR [rbp-0x38]'),(0x5d1bfb,'mulss','xmm0,DWORD PTR [rbp-0x34]'),(0x5d1c09,'addss','xmm0,xmm3'),(0x5d1c0d,'movss','DWORD PTR [rsi+0x20c],xmm0'),(0x5d1c15,'maxss','xmm0,xmm2'),
 (0x5d1c1b,'movss','xmm2,DWORD PTR [rsi+0x204]'),(0x5d1c29,'subss','xmm0,xmm2'),(0x5d1c2d,'jbe','0x1805d1c37'),(0x5d1c2f,'mulss','xmm0,DWORD PTR [rsp+0x74]'),(0x5d1c37,'mulss','xmm0,DWORD PTR [rsp+0x78]'),(0x5d1c46,'addss','xmm0,xmm2'),(0x5d1c4a,'movss','DWORD PTR [rsi+0x204],xmm0'),
 (0x5d1ca8,'jbe','0x1805d1cc5'),(0x5d1caa,'mulss','xmm0,xmm13'),(0x5d1caf,'movaps','xmm1,xmm0'),(0x5d1cc5,'movaps','xmm11,xmm10'),(0x5d1ccd,'mulss','xmm11,xmm7'),(0x5d1cd2,'mulss','xmm11,DWORD PTR [rsp+0x7c]'),(0x5d1d15,'subss','xmm12,xmm8'),(0x5d1ef7,'mulss','xmm1,xmm3'),(0x5d1eff,'mulss','xmm0,DWORD PTR [rcx+rdi*4]'),(0x5d1f04,'addss','xmm0,xmm1'),(0x5d1f08,'mulss','xmm0,xmm7'),(0x5d1f18,'movss','DWORD PTR [r15+rdi*4],xmm0'),
 (0x5d22f7,'cvtsd2ss','xmm1,xmm1'),(0x5d22fb,'mulss','xmm2,xmm1'),(0x5d22ff,'divss','xmm0,xmm2'),(0x5d2310,'subss','xmm1,xmm0'),
 (0x5d03c2,'movss','DWORD PTR [rsp+0x74],xmm1'),(0x5d044a,'movss','DWORD PTR [rsp+0x78],xmm1'),(0x5d0481,'movss','DWORD PTR [rbp-0x30],xmm1'),(0x5d04a6,'movss','DWORD PTR [rbp-0x3c],xmm1'),(0x5d04d6,'movss','DWORD PTR [rbp-0x38],xmm1'),(0x5d04f2,'movss','DWORD PTR [rbp-0x34],xmm1'),
 (0x5d15d7,'maxss','xmm0,xmm12'),(0x5d15dc,'mulss','xmm12,xmm12'),(0x5d15f4,'subss','xmm12,xmm1'),(0x5d15f9,'mulss','xmm12,xmm4'),(0x5d15fe,'addss','xmm12,xmm1'),
 (0x5d176c,'addss','xmm0,xmm0'),(0x5d17a5,'movaps','xmm12,xmm9'),(0x5d17a9,'subss','xmm12,DWORD PTR [rsp+0x40]'),(0x5d17b0,'mulss','xmm7,DWORD PTR [rsp+0x40]'),(0x5d17d1,'addss','xmm11,xmm7'),
]
CHECKS += [
 (0x5d30cd,'imul','rax,rax,0xf4'),(0x5d30df,'cmp','r8d,0x3c'),(0x5d30ec,'movss','xmm0,DWORD PTR [rax+rdx*1+0xf0]'),(0x5d30f6,'imul','rcx,rax,0x3d'),(0x5d3108,'subss','xmm3,xmm1'),(0x5d310c,'movss','xmm0,DWORD PTR [rdx+rcx*4+0x4]'),(0x5d3112,'subss','xmm0,DWORD PTR [rdx+rcx*4]'),(0x5d3117,'mulss','xmm0,xmm3'),(0x5d311b,'addss','xmm0,DWORD PTR [rdx+rcx*4]'),
 (0x5d185c,'imul','rcx,rdi,0x134'),(0x5d18a5,'cmp','ecx,0x4c'),(0x5d18aa,'movss','xmm7,DWORD PTR [rdx+0x130]'),(0x5d18be,'movss','xmm1,DWORD PTR [rdx+rax*4+0x4]'),(0x5d18c4,'subss','xmm1,DWORD PTR [rdx+rax*4]'),(0x5d18c9,'subss','xmm7,xmm0'),(0x5d18cd,'mulss','xmm7,xmm1'),(0x5d18d1,'addss','xmm7,DWORD PTR [rdx+rax*4]'),
 (0x5d3138,'subss','xmm0,xmm1'),(0x5d313f,'divss','xmm1,xmm2'),(0x5d3143,'subss','xmm4,xmm1'),(0x5d3174,'addss','xmm1,xmm0'),(0x5d3178,'addss','xmm3,xmm3'),(0x5d3183,'mulss','xmm0,xmm1'),(0x5d3187,'divss','xmm0,xmm3'),
]
CONSTANTS={0x974224:-90.,0x928a70:20.,0x9142a0:.001,0x909cd8:-.5,0x8e96a8:.5,0x909c40:2.,0x8e96ac:1.,0x909bec:.05,0x909c98:10.,0x928ae8:-100.,0x8f04c8:-1.,0x91441c:15.,0xa5c704:.08,0x9142d8:.3,0xa5c708:1.5,0x94fa3c:-180.,0x928ae0:-72.}
# Connect the constants to the actual consuming instructions as well as their values.
CONSTANT_USES={0x5d1b49:0x9142a0,0x5d1b59:0x909cd8,0x5d1b69:0x8e96a8,0x5d1b8e:0x909c40,
  0x5d12c0:0x928a70,0x5d126c:0x974224,0x5d1c3d:0x909bec,0x5d1ca1:0x928ae8,0x5d1cb2:0x909c98,
  0x5d22e7:0x8f04c8,0x5d22ef:0x9142a0,0x5d2308:0x8e96ac,0x5d0456:0x91441c,
  0x5d048a:0xa5c704,0x5d04af:0x9142d8,0x5d04c0:0xa5c708,0x5d177b:0x94fa3c}
CALLS={0x5d12bb:'log10f',0x5d1cba:'powf',0x5d2303:'expf',0x5d03a5:'expf',0x5d043d:'expf',0x5d0471:'expf',0x5d0496:'expf',0x5d04bb:'expf',0x5d04de:'expf',0x5d173d:'log10f',0x5d1776:'log10f'}
GROUP_STARTS=[0x5d07bf,0x5d096f,0x5d0b0c,0x5d0ca9,0x5d0e46,0x5d0fe7]
GROUP_PEAKS=[0x5d0960,0x5d0afd,0x5d0c9a,0x5d0e37,0x5d0fd4,0x5d1167]
GROUP_WEIGHTS=[0x5d0950,0x5d0af5,0x5d0c92,0x5d0e2f,0x5d0fcc,0x5d115f]

def verify_dynamics(pe, objdump='objdump'):
    if pe.sha256 != TVB_SHA256:
        raise ValueError('Unknown build: cannot reuse TVB dynamics offsets')
    ins=disassemble(pe,0x5cfa50,0x5d231c-0x5cfa50,objdump)
    ins+=disassemble(pe,0x5d30b0,0x5d31a3-0x5d30b0,objdump)
    by={i.address-pe.image_base:i for i in ins}
    def require(addr, op, args):
        i=by.get(addr)
        if not i or i.mnemonic!=op or i.operands.split('#')[0].strip()!=args:
            raise ValueError(f'Dynamics checkpoint failed at {addr:#x}: {i}')
    for a,o,b in CHECKS: require(a,o,b)
    for a,v in CONSTANTS.items():
        if not math.isclose(pe.f32(a),v,rel_tol=2e-7,abs_tol=1e-10):
            raise ValueError(f'Dynamics constant mismatch at {a:#x}: {pe.f32(a)}')
    if pe.at_rva(0x8e9820,16)!=bytes.fromhex('ffffff7f'*4) or pe.at_rva(0x909e90,16)!=bytes.fromhex('00000080'*4):
        raise ValueError('Unexpected absolute/sign masks')
    for a,v in CONSTANT_USES.items():
        i=by.get(a)
        if not i or f'# {pe.image_base+v:#x}' not in i.operands:
            raise ValueError(f'Constant use missing at {a:#x}')
    calls={int(c['site_rva'],16):c['symbol'] for c in imported_call_sites(pe,ins)}
    for a,s in CALLS.items():
        if calls.get(a)!=s: raise ValueError(f'Math import mismatch at {a:#x}')
    groups=[]
    for j,(start,peak,weight) in enumerate(zip(GROUP_STARTS,GROUP_PEAKS,GROUP_WEIGHTS)):
        require(start,'movaps','xmm2,xmm7')
        require(weight,'mulss',f'xmm2,DWORD PTR [rsi+{0x700+4*j:#x}]')
        if by[peak].mnemonic!='maxss': raise ValueError('Missing channel maximum')
        # The compiler schedules the next group's b1 multiplication before
        # its predecessor's maximum; include that small overlap.
        chunk=[i for a,i in by.items() if max(GROUP_STARTS[0],start-48)<=a<=peak]
        for k in range(4):
            for offset in range(0x520+20*(4*j+k),0x520+20*(4*j+k)+20,4):
                if not any(i.mnemonic=='mulss' and f'[rsi+{offset:#x}]' in i.operands for i in chunk):
                    raise ValueError(f'Missing group {j} coefficient {offset:#x}')
            for off in [0x718+8*(4*j+k),0x71c+8*(4*j+k)]:
                if not any(i.mnemonic=='movss' and i.operands.startswith(f'DWORD PTR [rax+rsi*1+{off:#x}],') for i in chunk):
                    raise ValueError(f'Missing group {j} state {off:#x}')
        groups.append({'group':j,'start_rva':hex(start),'peak_rva':hex(peak),'weight_offset':hex(0x700+4*j),'sections':4})
    for j in range(6):
        for off in (0xd18+4*j,0xd30+4*j):
            if not any(0x5d15be<=a<0x5d172e and i.mnemonic=='movss' and i.operands.startswith(f'DWORD PTR [rsi+{off:#x}],') for a,i in by.items()):
                raise ValueError(f'Missing detector state {off:#x}')
    regions=[{'id':name,'start_rva':hex(start),'end_rva_exclusive':hex(end),'title':title,'confidence':confidence,'equation':equation,'region_sha256':hashlib.sha256(pe.at_rva(start,end-start,executable=True)).hexdigest(),'file_offset':hex(next(sec.file_offset+start-sec.rva for sec in pe.sections if sec.rva<=start and end-sec.rva<=sec.file_size)),'checkpoint_rvas':[hex(a) for a,_,_ in CHECKS if start<=a<end],'constant_refs':[{'instruction_rva':hex(a),'data_rva':hex(v),'float32':pe.f32(v)} for a,v in CONSTANT_USES.items() if start<=a<end],'math_calls':[{'rva':hex(a),'symbol':symbol} for a,symbol in CALLS.items() if start<=a<end]} for name,start,end,title,confidence,equation in REGIONS]
    return {'schema_version':1,'binary_sha256':pe.sha256,'source':pe.path.name,'regions':regions,'checkpoint_count':len(CHECKS),'constant_count':len(CONSTANTS),'constant_use_count':len(CONSTANT_USES),'import_checkpoint_count':len(CALLS),'constants':[{'rva':hex(a),'float32':pe.f32(a)} for a in CONSTANTS], 'six_groups':groups,'state_map':{'peak':'0x200','single_gain_reduction':'0x204','dual_gain_reduction':['0x208','0x20c'],'mode2_peak_array':'0xd18..0xd2c','mode2_power_array':'0xd30..0xd44','mode0_knee_field':'0x158','mode0_ratio_field':'0x154','mode0_threshold_field':'0x150 (clamped -72..0)','time_scale_field':'0x198 (double; sample-rate-like)'},'curve_tables':[{'role':'mode1','base_rva':'0x77e7cb0','entries_per_row':61,'row_stride_bytes':244,'values_status':'not recovered'},{'role':'mode2','base_rva':'0x77e7a40','entries_per_row':77,'row_stride_bytes':308,'values_status':'not recovered'}],'limits':['Normal finite input and valid parameters assumed; float rounding omitted in equations.','Filter topology and control mapping remain incomplete; no audio-render parity.','Mode 1 and mode 2 full gain curves unresolved.','No VMR vendor dynamics law recovered.']}
