"""Exact-build static evidence for compound gain, dynamic EQ and split-band dynamics.
Read-only. No vendor executable, coefficient table or reconstructed processor is exported.
"""
import hashlib
import math
import struct
from .pe import PE
from .equations import TVB_SHA256
from .disasm import disassemble, imported_call_sites
from .curve_provenance import require, summary
from .dispatch import trace_dispatch


def check_region(pe, start, end, checks, imports=(), objdump='objdump'):
    ins=disassemble(pe,start,end-start,objdump)
    n=require(pe,ins,checks)
    calls={int(c['site_rva'],16):c['symbol'] for c in imported_call_sites(pe,ins)}
    if any(calls.get(r)!=s for r,s in imports):
        raise ValueError('Unexpected math call')
    return {'checkpoint_rvas':[hex(r) for r,_,_ in checks],'start_rva':hex(start),'end_rva_exclusive':hex(end),
            'sha256':hashlib.sha256(pe.at_rva(start,end-start,executable=True)).hexdigest(),
            'checkpoint_count':n,'math_call_count':len(imports)}


def constants(pe, values):
    for r, expected in values:
        actual=struct.unpack('<f',pe.at_rva(r,4))[0]
        if not math.isclose(actual,expected,rel_tol=1e-6,abs_tol=1e-9):
            raise ValueError(f'Unexpected constant at {r:#x}')
    return {hex(r):v for r,v in values}


def verify_extended(pe,objdump='objdump'):
    if pe.sha256!=TVB_SHA256:raise ValueError('Unexpected source fingerprint')
    regions=[]
    def add(name,title,start,end,checks,equation,imports=()):
        regions.append({'id':name,'title':title,'confidence':'instruction-verified local algebra/structure; runtime unverified',
                        'equation':equation,**check_region(pe,start,end,checks,imports,objdump)})
    add('compound_gain','Primary FET input calibration, threshold and output coupling',0x342fa8,0x3431c3,[
        (0x342fa8,'mov','rax,QWORD PTR [rdi+0x3b310]'),(0x342fb1,'mov','rax,QWORD PTR [rdi+0x3b378]'),
        (0x342ff5,'mov','r8d,DWORD PTR [rax]'),(0x343019,'mov','r9d,0x3a'),
        (0x343030,'movss','xmm1,DWORD PTR [r10+rax*4+0x928270]'),(0x34303a,'movss','xmm2,DWORD PTR [r10+rax*4+0x928274]'),
        (0x343044,'subss','xmm2,xmm1'),(0x343053,'mulss','xmm2,xmm3'),(0x343057,'addss','xmm2,xmm1'),(0x343060,'addss','xmm2,xmm0'),
        (0x34308c,'movss','DWORD PTR [rdi+0x344e4],xmm1'),(0x3430db,'movss','DWORD PTR [rdi+0x344b8],xmm1'),
        (0x3430e3,'movss','DWORD PTR [rdi+0x344d0],xmm6'),(0x3430eb,'mov','BYTE PTR [rdi+0x344d4],0x0'),
        (0x3430f2,'test','dl,dl'),(0x343106,'movss','DWORD PTR [rdi+0x344dc],xmm0'),
        (0x343137,'mov','rdx,QWORD PTR [rdi+0x3b370]'),(0x343161,'movss','xmm1,DWORD PTR [r10+rax*4+0x928360]'),
        (0x34316b,'movss','xmm3,DWORD PTR [r10+rax*4+0x928364]'),(0x343184,'mulss','xmm3,xmm4'),
        (0x343192,'addss','xmm3,xmm0'),(0x343196,'addss','xmm3,xmm2'),(0x3431bb,'movss','DWORD PTR [rdi+0x344bc],xmm0')],
        'Finite inputs: z=lerp(input_curve,clamp(threshold+59,0,59))+input_db; I=clamp(z,-12,24); e=z-I; T=clamp(-e,-72,0); O=clamp(lerp(output_curve,clamp(cla_output+59,0,59))+output_db+e,-120,24). If threshold or CLA output <= -59.95, O=-120. Fields 0x17c=input, 0x150=threshold, 0x174=output; makeup and auto makeup zeroed. CLA default -18 if absent. Curves are file-backed and fingerprinted, not exported.')
    add('gain_consumers','Independent input/output gain ramps and dry blend',0x5d052e,0x5d07b5,[
        (0x5d052e,'mov','eax,DWORD PTR [rsi+0x168]'),(0x5d057d,'mov','eax,DWORD PTR [rsi+0x170]'),
        (0x5d0596,'mov','eax,DWORD PTR [rsi+0x174]'),(0x5d05bb,'lea','rcx,[rsi+0xed0]'),
        (0x5d05c7,'mov','eax,DWORD PTR [rsi+0x17c]'),(0x5d05cd,'lea','rbx,[rsi+0xee4]'),
        (0x5d072e,'addss','xmm11,DWORD PTR [rbx]'),(0x5d07a9,'mulss','xmm7,DWORD PTR [rax+r14*4]')],
        'Field 0x17c is converted to a smoothed linear input multiplier, field 0x174 to output gain; db<=-100 maps to zero, else 10^(db/20).',[(0x5d05ae,'powf'),(0x5d05e6,'powf')])
    add('mix','Final output blend',0x5d1c9a,0x5d1f25,[
        (0x5d1ccd,'mulss','xmm11,xmm7'),(0x5d1cd2,'mulss','xmm11,DWORD PTR [rsp+0x7c]'),
        (0x5d1d15,'subss','xmm12,xmm8'),(0x5d1d07,'lea','rdi,[rsi+0xed0]'),
        (0x5d1ef7,'mulss','xmm1,xmm3'),(0x5d1eff,'mulss','xmm0,DWORD PTR [rcx+rdi*4]'),
        (0x5d1f04,'addss','xmm0,xmm1'),(0x5d1f08,'mulss','xmm0,xmm7')],
        'Output = O_linear*((1-mix)*saved_dry + mix*colored_wet), or O_linear*wet when blend branch inactive. Makeup path includes further factors; exact mode-dependent calibration not asserted.')
    add('deess_crossover','De-esser complementary two-section crossover',0x5b6b20,0x5b6c2a,[
        (0x5b6b4a,'mulss','xmm0,DWORD PTR [rax+r8*4]'),(0x5b6b50,'subss','xmm7,xmm0'),
        (0x5b6b54,'subss','xmm7,DWORD PTR [rdx+r8*4]'),(0x5b6b5a,'mulss','xmm7,DWORD PTR [rcx+0x8]'),
        (0x5b6b79,'movss','DWORD PTR [rax+r8*4],xmm0'),(0x5b6b9a,'movss','DWORD PTR [rdx+r8*4],xmm0'),
        (0x5b6bdb,'movss','DWORD PTR [rax+r8*4],xmm0'),(0x5b6bfb,'movss','DWORD PTR [rcx+r8*4],xmm0'),
        (0x5b6c01,'movss','DWORD PTR [r9],xmm1'),(0x5b6c06,'mulss','xmm6,DWORD PTR [r10+0x4]'),
        (0x5b6c0c,'subss','xmm5,xmm6'),(0x5b6c15,'addss','xmm5,xmm7'),(0x5b6c1d,'subss','xmm5,xmm1'),
        (0x5b6c21,'movss','DWORD PTR [rax],xmm5')],
        'Two TPT lowpass sections with shared g,k. low=LP2(LP1(x)); high=HP1+LP1-k*BP1-low. Sum is allpass1, not sample-identical dry.')
    add('deess_setup','De-esser crossover and time coefficient setup',0x5d3c5e,0x5d3dfd,[
        (0x5d3c73,'cmovg','eax,ecx'),(0x5d3c7f,'movss','xmm1,DWORD PTR [rcx+rax*4]'),(0x5d3c8f,'mulss','xmm1,xmm0'),
        (0x5d3cb2,'minss','xmm9,xmm1'),(0x5d3d11,'call','0x1805b9dc0'),(0x5d3d1f,'movsd','xmm7,QWORD PTR [r14+0x180]'),
        (0x5d3d4d,'movss','DWORD PTR [rsp+0x3c],xmm0'),(0x5d3d6b,'movss','DWORD PTR [rsp+0x44],xmm0'),
        (0x5d3d95,'movss','DWORD PTR [rsp+0x50],xmm0'),(0x5d3dcd,'movss','DWORD PTR [rsp+0x54],xmm0'),
        (0x5d3deb,'divss','xmm2,xmm1'),(0x5d3df3,'subss','xmm0,xmm2')],
        'Crossover cutoff=clamp(field150*mode_scale,2000,12000) with scale 1.3,1,0.75. Detector retention exp(-1/(Fs*t)) with t=.00012 or .028 seconds; gain envelope retention uses fields 0x16c/0x170 in ms. Ratio slope=1-1/R.',[(0x5d3d48,'expf'),(0x5d3d66,'expf'),(0x5d3d90,'expf'),(0x5d3dc8,'expf')])
    add('deess_gain','De-esser linked level, progressive gain law and output choices',0x5d3e44,0x5d401e,[
        (0x5d3e82,'call','0x1805b6b20'),(0x5d3e8b,'andps','xmm0,xmm10'),(0x5d3e8f,'maxss','xmm0,xmm6'),
        (0x5d3ed0,'mulss','xmm0,xmm6'),(0x5d3ed4,'mulss','xmm1,xmm2'),(0x5d3edc,'movss','DWORD PTR [r14+0x20c],xmm0'),
        (0x5d3f05,'subss','xmm2,xmm13'),(0x5d3f12,'mulss','xmm0,xmm14'),(0x5d3f25,'minss','xmm1,xmm0'),
        (0x5d3f31,'addss','xmm1,xmm8'),(0x5d3f3c,'mulss','xmm0,xmm2'),(0x5d3f44,'minss','xmm1,DWORD PTR [rsp+0x4c]'),
        (0x5d3f7f,'movss','DWORD PTR [r14+0x210],xmm2'),(0x5d3fcd,'cmp','DWORD PTR [rsp+0x58],0x1'),
        (0x5d3feb,'addss','xmm0,DWORD PTR [rsp+rdx*4+0x88]'),(0x5d3ff4,'mulss','xmm0,xmm1')],
        'Linked p=max(abs(high[channel])). E=retain*Eold+(1-retain)*p; L=max(-120,20log10(E)); u=L-T. For u>0, target=min(cap,(1-1/R)*u*(1+0.55*clamp(u/8,0,1))), else 0. Separate attack/release GR smoothing, gain=10^(-GR/20) above -100dB. Mode field 0x160 selects wideband (1) versus split-band; flag0x164 excludes low component.',[(0x5d3eea,'log10f'),(0x5d3fb4,'powf')])
    add('deess_split','Split-band output sample write',0x5d4112,0x5d4137,[
        (0x5d4115,'mulss','xmm0,DWORD PTR [rsp+rdx*4+0x68]'),(0x5d411b,'test','r12b,r12b'),
        (0x5d4120,'addss','xmm0,DWORD PTR [rsp+rdx*4+0x88]'),(0x5d4131,'movss','DWORD PTR [rcx+r8*4],xmm0')],
        'Split output=high*gain+low, or high*gain with low excluded.')
    add('eq_schedule','24-band detector/output EQ handoff in 32-frame chunks',0x35bb80,0x35bc6c,[
        (0x35bba0,'mov','ecx,0x20'),(0x35bbaf,'cmovl','ecx,eax'),(0x35bbcd,'call','0x1805a5090'),
        (0x35bbe0,'imul','rbx,rbp,0x168'),(0x35bbec,'movss','xmm2,DWORD PTR [rbx+rdi*1+0x17ea0]'),
        (0x35bbf5,'call','0x1805a3d90'),(0x35bc11,'cmp','esi,0x18'),(0x35bc67,'call','0x1805a3dd0')],
        'For each <=32-frame chunk, call detector then transfer 24 per-band signed gain adjustments to audio EQ before processing the chunk.')
    add('eq_detector','Dynamic EQ bandpass coefficient and detector recurrences',0x5a5090,0x5a5d70,[
        (0x5a50ce,'addsd','xmm1,xmm1'),(0x5a5258,'mulss','xmm0,xmm3'),(0x5a525c,'divss','xmm0,xmm1'),
        (0x5a5287,'divss','xmm2,xmm1'),(0x5a528b,'movss','DWORD PTR [rbx+0x40],xmm2'),
        (0x5a52a1,'movss','DWORD PTR [rbx+0x30],xmm0'),(0x5a52aa,'movss','DWORD PTR [rbx+0x34],xmm0'),(0x5a52b3,'movss','DWORD PTR [rbx+0x38],xmm0'),
        (0x5a5b65,'subss','xmm2,xmm5'),(0x5a5b90,'movss','DWORD PTR [r13+0x0],xmm0'),(0x5a5b96,'movss','DWORD PTR [r12],xmm1'),
        (0x5a5bbb,'andps','xmm7,xmm13'),(0x5a5be2,'movss','DWORD PTR [r15],xmm1'),(0x5a5bf0,'movss','DWORD PTR [rdi],xmm0'),
        (0x5a5c30,'mov','eax,DWORD PTR [rbx+0xc]'),(0x5a5c69,'subss','xmm6,xmm0'),(0x5a5c6d,'divss','xmm6,DWORD PTR [rsp+0x24]'),
        (0x5a5c83,'minss','xmm0,xmm6'),(0x5a5c9e,'mulss','xmm0,xmm1'),(0x5a5cb7,'movss','DWORD PTR [rbx+0x150],xmm0'),
        (0x5a5cc6,'add','rbx,0x168'),(0x5a5ce7,'jne','0x1805a51d0')],
        'TPT bandpass branch: g=tan(pi*clamp(f,1,0.49*Fs)/Fs), k=1/max(Q,.025), a1=1/(1+g*(g+k)), a2=g*a1,a3=g*a2; output=k*v1. Fast and slow absolute envelopes. Signed adjustment = range*clamp((L-T)/clamp(6+0.5*abs(range),6,24),0,1); fixed threshold or slow-envelope dB+3. Fast retention is frequency/control-dependent; slow retention exp(-1/(2*Fs)). 24 records of 0x168 bytes. Other detector routing branches exist.',[(0x5a50e0,'exp'),(0x5a5260,'tanf'),(0x5a5588,'exp'),(0x5a55be,'exp'),(0x5a5c0a,'log10f'),(0x5a5c4e,'log10f')])
    vals=constants(pe,[(0x928ac8,-18),(0x928ad8,-59.95),(0x928a88,59),(0x928ac4,-12),(0x918858,24),(0x928ae0,-72),(0x928aec,-120),(0x928ae8,-100),(0x909bec,.05),(0x909c98,10),(0x928ab0,2000),(0x928abc,12000),(0xa5c774,.00012),(0xa5c778,.028),(0x9142a0,.001),(0xa5b128,.125),(0x914300,.55),(0x928a70,20),(0x974198,.025),(0x9143f0,6),(0x909c80,3)])
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'regions':regions,'checkpoint_count':sum(r['checkpoint_count'] for r in regions),'scalar_constants':vals,'gain_table_fingerprints':[summary(pe.at_rva(r,240),1,60) for r in (0x928270,0x928360)],'limits':['Exact source only. Local equations for finite valid values, not an end-to-end implementation.','Original tables excluded; GUI normalization, all routing, dynamic EQ audio filter modes and runtime DSP not verified.']}


VMR_COPY={'FG-116.epl':('1cf796db09bc6ce3455d3fa3506614fa990374fc2f2642ff8fc9c40e626dfbf2',0x6ffc0,0x6f780,0x6f7a0),
          'FG-2A.epl':('6b365ee15dbb94efb9d97b76923445f4ad4f3740194e21363cd9ffbe8df8d573',0x6ff40,0x6f780,0x6f7a0),
          'FG-Stress.epl':('2509a6f3480481feb15a0fde97abcb4acccfc6fc936f55f5e8c88b7c98edcd26',0x70080,0x6f7a0,0x6f7c0)}


def verify_vmr_utilities(pe,objdump='objdump'):
    if pe.path.name not in VMR_COPY:raise ValueError('Unsupported module name')
    sha,copy,expand,narrow=VMR_COPY[pe.path.name]
    if pe.sha256!=sha:raise ValueError('Unexpected source fingerprint')
    dispatch=trace_dispatch(pe,0x6f740,7,objdump)
    target=int(dispatch['sampled_slots'][0]['target_rva'],16)
    wrapper=disassemble(pe,target,0x35,objdump)
    if not any(i.mnemonic=='shl' and i.operands=='r8d,0x3' for i in wrapper) or not any(i.mnemonic=='call' and i.operands==hex(pe.image_base+copy) for i in wrapper):raise ValueError('Unexpected copy wrapper')
    kernel=disassemble(pe,copy,0x85,objdump)
    checks=[(copy+0x50,'mov','r11b,BYTE PTR [r10+r9*1]'),(copy+0x54,'mov','BYTE PTR [r10+rax*1],r11b'),(copy+0x6d,'movdqu','xmm0,XMMWORD PTR [rdx+r9*1]'),(copy+0x73,'movdqa','XMMWORD PTR [rdx+rax*1],xmm0')]
    require(pe,kernel,checks)
    records=[{'dispatcher_rva':hex(0x6f740),'slot0_rva':hex(target),'helper_rva':hex(copy),'kind':'8-byte element buffer copy','confidence':'instruction-verified byte and 16-byte vector copy'}]
    for disp,kind,ops in ((expand,'float32 to float64',('cvtss2sd','cvtps2pd')),(narrow,'float64 to float32 with clamp',('cvtsd2ss','minsd','maxsd'))):
        if disp is None:continue
        t=trace_dispatch(pe,disp,7,objdump);r=int(t['sampled_slots'][0]['target_rva'],16)
        ins=disassemble(pe,r,0x100,objdump); found={i.mnemonic for i in ins}
        if not set(ops)<=found:raise ValueError('Unexpected conversion kernel')
        records.append({'dispatcher_rva':hex(disp),'slot0_rva':hex(r),'kind':kind,'confidence':'decoded scalar/vector conversion evidence','verified_opcodes':list(ops)})
    if pe.path.name=='FG-Stress.epl':
        if struct.unpack('<Q',pe.at_rva(0xe9f848+8*8,8))[0]!=pe.image_base+0x160a30:
            raise ValueError('Unexpected FG-Stress processor vtable')
        checks=[(0x160a81,'mov','DWORD PTR [rbp+0x170],0x20'),
                (0x160b63,'mov','r8d,0x20'),(0x160b6f,'call','0x18006f740'),
                (0x160b96,'call','QWORD PTR [r15+rdx*8]'),(0x160bfd,'call','0x18006f740'),
                (0x160c25,'call','QWORD PTR [rsi+rdx*8]')]
        records.append({'kind':'32-frame wrapper and unresolved indirect calls','vtable_rva':'0xe9f848',
                        **check_region(pe,0x160a30,0x160c49,checks,objdump=objdump)})
    return {'source':pe.path.name,'binary_sha256':pe.sha256,'records':records,'limits':'Only sampled slot 0. These utilities are not effect gain-law or oversampling proof. Runtime dispatch and module-specific engines remain unresolved.'}
