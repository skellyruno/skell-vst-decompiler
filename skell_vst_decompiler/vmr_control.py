"""Exact-build checks for VMR local envelope and control-buffer arithmetic.
These are not full compressor models; runtime dispatch is not established.
"""
import argparse
import json
import math
import struct
from .pe import PE
from .extended_dsp import VMR_COPY, check_region
from .rack_paths import pointer_slots


def verify(pe, objdump='objdump'):
    name = pe.path.name
    if name not in ('FG-116.epl', 'FG-2A.epl', 'FG-Stress.epl') or pe.sha256 != VMR_COPY[name][0]:
        raise ValueError('Unsupported source fingerprint')
    regions = []
    constants = {}
    def constant(rva, expected):
        value, = struct.unpack('<d', pe.at_rva(rva, 8))
        if not math.isfinite(value) or value != expected:
            raise ValueError(f'Unexpected double at {rva:#x}')
        constants[hex(rva)] = value
    def add(key, title, start, end, checks, equation):
        regions.append({'id': key, 'title': title, 'equation': equation,
                        'confidence': 'instruction-verified local arithmetic; runtime selection unverified',
                        **check_region(pe, start, end, checks, objdump=objdump)})
    if name == 'FG-116.epl':
        constant(0xe7db78, .0025)
        add('fg116_input_slew', 'Fixed input scalar smoothing', 0x1619a0, 0x161be1, [
            (0x1619e7,'movsd','xmm7,QWORD PTR [rip+0xd1c189]'),
            (0x161ad0,'movsd','xmm3,QWORD PTR [r15+0x90]'),
            (0x161ae6,'movsd','QWORD PTR [r10+0x8],xmm3'),
            (0x161af3,'movsd','xmm2,QWORD PTR [r10+0x8]'),
            (0x161b26,'subsd','xmm0,xmm2'),(0x161b2a,'mulsd','xmm0,xmm7'),
            (0x161b2e,'addsd','xmm2,xmm0'),(0x161b39,'mulsd','xmm0,QWORD PTR [rdx]'),
            (0x161b45,'movsd','QWORD PTR [rcx],xmm0'),(0x161bd9,'movsd','QWORD PTR [r10+0x8],xmm2')],
            'g += 0.0025*(target-g); y=x*g. Initialization branch sets g=target. This is a local scalar gain stage, not the compression gain computer.')
        add('fg116_min_envelope','Minimum-constrained envelope',0x161880,0x161998,[
            (0x161880,'mov','r9,QWORD PTR [rsp+0x28]'),(0x1618b0,'movsd','xmm0,QWORD PTR [rdx]'),
            (0x1618b8,'movsd','xmm1,QWORD PTR [r9]'),(0x1618bd,'subsd','xmm1,xmm0'),
            (0x1618c1,'mulsd','xmm1,xmm3'),(0x1618c5,'addsd','xmm1,xmm0'),
            (0x1618c9,'minsd','xmm1,xmm0'),(0x1618cd,'movsd','QWORD PTR [r9],xmm1'),
            (0x1618d2,'movsd','QWORD PTR [rcx],xmm1'),(0x161980,'minsd','xmm1,xmm0')],
            'For finite inputs, s=min(x,x+a*(s_prev-x)); s stored to output and state. For 0<=a<=1 this captures decreases immediately and smooths increases. Input buffer semantics remain unknown.')
        add('fg116_envelope_call','Candidate envelope caller',0x161ca7,0x161d47,[
            (0x161cb0,'movsd','xmm6,QWORD PTR [r15+0x10]'),(0x161cd2,'lea','rbx,[rsi+0x70]'),
            (0x161d01,'mov','rdx,QWORD PTR [rsp+0x50]'),(0x161d06,'lea','rcx,[rbp+0x60]'),
            (0x161d11,'movaps','xmm3,xmm6'),(0x161d21,'mov','r8d,esi'),
            (0x161d3d,'mov','QWORD PTR [rsp+0x20],rbx'),(0x161d42,'call','0x180161880')],
            'The scalar retention argument comes from the object at r15+0x10; output scratch rbp+0x60 and persistent state rsi+0x70. Physical units and host knob mapping unverified.')
    elif name == 'FG-2A.epl':
        constant(0xeaa3a8,.0025)
        add('fg2a_dual_slew','Dual scalar gain and parallel sum',0x155960,0x155c3f,[
            (0x15598e,'movsd','xmm6,QWORD PTR [rip+0xd54a12]'),(0x1559ca,'movsd','xmm3,QWORD PTR [r14+0x8]'),
            (0x1559dc,'movsd','QWORD PTR [rbx+r10*1+0x18],xmm3'),(0x155a26,'subsd','xmm0,xmm2'),
            (0x155a2a,'mulsd','xmm0,xmm6'),(0x155a2e,'addsd','xmm2,xmm0'),(0x155a39,'mulsd','xmm0,QWORD PTR [r8]'),
            (0x155ad2,'movsd','QWORD PTR [rbx+r10*1+0x18],xmm2'),(0x155ade,'movsd','xmm3,QWORD PTR [r14]'),
            (0x155b36,'subsd','xmm0,xmm2'),(0x155b3a,'mulsd','xmm0,xmm6'),(0x155b3e,'addsd','xmm2,xmm0'),
            (0x155b49,'mulsd','xmm0,QWORD PTR [r9]'),(0x155be4,'movsd','QWORD PTR [rbx+r10*1+0x8],xmm2'),
            (0x155beb,'lea','rdx,[rsp+0x20]'),(0x155bf4,'lea','rcx,[rsp+0x130]'),(0x155c04,'call','0x18006f860'),
            (0x155c0f,'cmp','ebp,0x2'),(0x155c12,'jb','0x1801559b0')],
            'Two independent scalar gain ramps per channel use g+=.0025*(target-g), then sum two weighted scratch streams. Verified vector-add candidates below; identities of the two streams and complete gain law unknown.')
        if [x['target_rva'] for x in pointer_slots(pe,0x1015f58,7)] != ['0x72b60']+['0x72d40']*4+['0x72d80','0x72f00']:
            raise ValueError('Unexpected vector-add table')
        add('fg2a_sum_dispatch','Vector sum dispatch',0x6f860,0x6f872,[
            (0x6f860,'movsxd','rax,DWORD PTR [rip+0xff25ed]'),(0x6f867,'lea','r11,[rip+0xfa66ea]'),(0x6f86e,'jmp','QWORD PTR [r11+rax*8]')],
            'Seven inspected slots resolve to four entry points. Selected runtime slot unknown; all four candidate entries lead to vector addition.')
        add('fg2a_sum_scalar','Vector sum scalar and packed arithmetic',0x72b60,0x72d40,[
            (0x72bd1,'movsd','xmm0,QWORD PTR [rcx+r11*8]'),(0x72bd7,'addsd','xmm0,QWORD PTR [rdx+r11*8]'),
            (0x72bdd,'movsd','QWORD PTR [r8+r11*8],xmm0'),(0x72c14,'addpd','xmm1,xmm0')],
            'Scalar and packed paths sum src1+src2 into output.')
        add('fg2a_sum_bridge','Four slots share addition wrapper',0x72d40,0x72d78,[(0x72d62,'call','0x180074d90')],
            'Wrapper calls vector arithmetic helper.')
        add('fg2a_sum_helper','Scalar/packed sum helper',0x74d90,0x74e68,[(0x74d9f,'movsd','xmm0,QWORD PTR [rcx]'),(0x74daa,'addsd','xmm0,QWORD PTR [rdx]'),(0x74dae,'movsd','QWORD PTR [r8],xmm0'),(0x74e4e,'addpd','xmm2,xmm0')],
            'Addition verified in scalar and packed instructions.')
        add('fg2a_sum_avx','Two wide-vector sum candidates',0x72d80,0x73025,[(0x72e07,'vaddsd','xmm1,xmm0,QWORD PTR [rbx+r10*8]'),(0x72e41,'vaddpd','ymm4,ymm2,ymm3'),(0x72e45,'vmovupd','YMMWORD PTR [r8+rax*8],ymm4'),(0x72fb1,'vaddpd','ymm1,ymm0,YMMWORD PTR [rbx+rax*8]'),(0x72fc8,'vmovupd','YMMWORD PTR [r8+rax*8],ymm1')],
            'Both AVX candidate paths also perform addition. Not a distinct nonlinear compression algorithm.')
    else:
        constant(0xea0480,1.);constant(0xea0460,130.)
        if pe.at_rva(0xea0490,8)!=bytes.fromhex('ffffffffffffff7f'):
            raise ValueError('Unexpected absolute-value bitmask')
        add('stress_bounds_setup','Control range constants',0x163031,0x16304e,[
            (0x163031,'xorps','xmm7,xmm7'),(0x163046,'movaps','xmm6,XMMWORD PTR [rip+0xd3d433]')],
            'Local path establishes zero and one clamp boundaries; absolute-value mask and slope checked at consuming sites.')
        add('stress_control_pair','Coupled bounded detector controls',0x163442,0x163521,[
            (0x163442,'movsd','xmm4,QWORD PTR [rip+0xd3d046]'),(0x16344c,'movsd','xmm5,QWORD PTR [rip+0xd3d00c]'),
            (0x1634a5,'movsd','QWORD PTR [r12+0x390],xmm2'),(0x1634b2,'movsd','xmm0,QWORD PTR [r15+0x318]'),
            (0x1634bb,'maxsd','xmm1,xmm0'),(0x1634bf,'subsd','xmm1,xmm0'),
            (0x1634c6,'mulsd','xmm1,xmm5'),(0x1634ca,'minsd','xmm0,xmm1'),
            (0x1634d1,'maxsd','xmm3,xmm0'),(0x1634d5,'movsd','QWORD PTR [rbp+rdx*1+0xb50],xmm3'),
            (0x1634de,'subsd','xmm1,xmm3'),(0x1634e2,'movsd','xmm0,QWORD PTR [r15+0x310]'),
            (0x1634eb,'maxsd','xmm2,xmm0'),(0x1634ef,'subsd','xmm2,xmm0'),
            (0x1634f6,'mulsd','xmm2,xmm5'),(0x1634fa,'minsd','xmm0,xmm2'),
            (0x163501,'maxsd','xmm2,xmm0'),(0x163505,'mulsd','xmm2,xmm1'),
            (0x163509,'movsd','QWORD PTR [rbp+rdx*1+0xa40],xmm2')],
            'For finite P, U=clamp(130*(P-T1),0,1); V=(1-U)*clamp(130*(P-T0),0,1). These are bounded scratch control streams, not established audio gain.')
        add('stress_control_history','Control-stream history stores',0x1637d6,0x163866,[
            (0x1637dd,'lea','r8,[rbp+0xf10]'),(0x1637ec,'lea','rcx,[rbp+0xb50]'),
            (0x1637fe,'movsd','QWORD PTR [rbx+rax*8+0x4010],xmm0'),(0x16380f,'and','eax,0x3ff'),
            (0x16381a,'call','0x18006f9e0'),(0x16384a,'movsd','QWORD PTR [rbx+rax*8+0x2008],xmm0'),
            (0x16385b,'and','eax,0x3ff')],
            'The same bounded streams feed reduction/summary calls and 1024-position circular histories. The summary operation and whether these streams also affect audio remain unresolved.')
    return {'schema_version':1,'source':name,'binary_sha256':pe.sha256,'regions':regions,
            'constants':constants,'checkpoint_count':sum(r['checkpoint_count'] for r in regions),
            'limits':'Candidate processing paths only; no full compressor law or runtime validation.'}

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary');p.add_argument('--objdump',default='objdump');a=p.parse_args()
    print(json.dumps(verify(PE(a.binary),a.objdump),indent=2,allow_nan=False))
