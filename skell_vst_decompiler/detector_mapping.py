"""Exact-build evidence for detector interpolation and rate-dependent setup.

No vendor calibration arrays or implementation are exported. The report records
short mathematical relationships and hashes, not a reconstructed processor.
"""
import hashlib
import math
import struct
from .equations import TVB_SHA256
from .disasm import disassemble, imported_call_sites
from .curve_provenance import require
from .fieldrefs import field_refs


def fingerprint_record(pe,rva,words):
    if not 1<=words<=256:raise ValueError('Invalid record length')
    data=pe.at_rva(rva,4*words)
    if not all(math.isfinite(x[0]) for x in struct.iter_unpack('<f',data)):
        raise ValueError('Nonfinite calibration record')
    section=next(s for s in pe.sections if s.rva<=rva and rva+len(data)<=s.rva+s.file_size)
    return {'rva':hex(rva),'float32_words':words,'sha256':hashlib.sha256(data).hexdigest(),'section':section.name,'writable':bool(section.characteristics&0x80000000)}


def verify_detector_mapping(pe,objdump='objdump'):
    if pe.sha256!=TVB_SHA256:raise ValueError('Unexpected source fingerprint')
    setup=disassemble(pe,0x5cfcb8,0x321,objdump)
    entry=disassemble(pe,0x5cfb36,0x24,objdump)
    detector=disassemble(pe,0x5d172e,0x1a8,objdump)
    consumer=disassemble(pe,0x5d18d6,0x1ba,objdump)
    checks=require(pe,entry,[(0x5cfb53,'mov','r9d,DWORD PTR [rsi+0x18c]')])
    checks+=require(pe,setup,[(0x5cfcc9,'movd','xmm4,r9d'),(0x5cfcd5,'mov','BYTE PTR [rsp+0x24],bl'),(0x5cfd1d,'xor','ecx,ecx'),(0x5cfd16,'movss','DWORD PTR [rsp+0x6c],xmm10'),(0x5cfd21,'mov','ecx,0x4'),(0x5cfd2b,'mov','ecx,0x3'),(0x5cfd32,'mov','ecx,r10d'),(0x5cfd37,'mov','ecx,0x1'),(0x5cfd3e,'xor','ecx,ecx'),(0x5cfd46,'movss','xmm0,DWORD PTR [rdx+rax*4+0xa5c550]'),(0x5cfd4f,'subss','xmm4,xmm0'),(0x5cfd53,'subss','xmm1,xmm0'),(0x5cfd57,'divss','xmm4,xmm1'),(0x5cfd5b,'movss','DWORD PTR [rsp+0x6c],xmm4'),(0x5cfd61,'mov','eax,DWORD PTR [rsi+0x190]'),(0x5cfd67,'mov','DWORD PTR [rsp+0x34],ecx'),(0x5cfd7f,'minss','xmm15,xmm0'),(0x5cfe18,'subss','xmm15,DWORD PTR [rcx]'),(0x5cfe1d,'subss','xmm2,DWORD PTR [rcx]'),(0x5cfe21,'movss','xmm0,DWORD PTR [rax]'),(0x5cfe25,'subss','xmm0,DWORD PTR [rdx]'),(0x5cfe29,'divss','xmm15,xmm2'),(0x5cfe2e,'mulss','xmm15,xmm0'),(0x5cfe33,'addss','xmm15,DWORD PTR [rdx]'),(0x5cfe38,'movss','DWORD PTR [rsp+0x70],xmm15'),(0x5cfe3f,'movsd','xmm1,QWORD PTR [rsi+0x198]'),(0x5cfe7c,'divsd','xmm0,xmm1'),(0x5cfea7,'movss','DWORD PTR [rbp-0x50],xmm3'),(0x5cfeb6,'movss','DWORD PTR [rbp-0x5c],xmm0'),(0x5cfec4,'mulss','xmm2,xmm3'),(0x5cfec8,'divss','xmm2,xmm0'),(0x5cfedf,'movss','DWORD PTR [rbp-0x54],xmm2'),(0x5cfef0,'divss','xmm2,xmm0'),(0x5cfefc,'movss','DWORD PTR [rbp-0x58],xmm2'),(0x5cff0b,'divss','xmm0,xmm1'),(0x5cff37,'subss','xmm2,xmm1'),(0x5cff44,'movss','DWORD PTR [rbp-0x64],xmm2'),(0x5cff7b,'movss','DWORD PTR [rbp-0x4c],xmm1'),(0x5cffbf,'movss','DWORD PTR [rbp-0x60],xmm1'),(0x5cffcf,'minss','xmm1,xmm0'),(0x5cffd3,'movss','DWORD PTR [rsp+0x40],xmm1')])
    checks+=require(pe,detector,[(0x5d172e,'movss','xmm0,DWORD PTR [rsi+rbx*4+0xd18]'),(0x5d1763,'movss','xmm0,DWORD PTR [rsi+rbx*4+0xd30]'),(0x5d176c,'addss','xmm0,xmm0'),(0x5d17a9,'subss','xmm12,DWORD PTR [rsp+0x40]'),(0x5d17b0,'mulss','xmm7,DWORD PTR [rsp+0x40]'),(0x5d17cc,'mulss','xmm11,xmm12'),(0x5d17d1,'addss','xmm11,xmm7'),(0x5d17bf,'movss','xmm0,DWORD PTR [rsi+rbx*4+0xd1c]'),(0x5d1803,'movss','xmm0,DWORD PTR [rsi+rbx*4+0xd34]'),(0x5d180c,'addss','xmm0,xmm0'),(0x5d1841,'movzx','edi,BYTE PTR [rsp+0x24]'),(0x5d1846,'mulss','xmm8,DWORD PTR [rsp+0x40]'),(0x5d1851,'movss','xmm14,DWORD PTR [rsp+0x6c]'),(0x5d185c,'imul','rcx,rdi,0x134'),(0x5d1863,'mulss','xmm7,xmm12'),(0x5d1868,'addss','xmm7,xmm8'),(0x5d1870,'subss','xmm7,xmm11'),(0x5d1875,'mulss','xmm7,xmm14'),(0x5d187a,'addss','xmm7,xmm11'),(0x5d1887,'subss','xmm7,DWORD PTR [rsp+0x70]')])
    checks+=require(pe,consumer,[(0x5d18fa,'divss','xmm0,DWORD PTR [rbp-0x5c]'),(0x5d190d,'mulss','xmm11,DWORD PTR [rbp-0x58]'),(0x5d1920,'mulss','xmm0,DWORD PTR [rbp-0x54]'),(0x5d1a33,'movss','xmm8,DWORD PTR [rbp-0x50]'),(0x5d1a79,'mulss','xmm1,DWORD PTR [rbp-0x4c]')])
    for address,value in [(0x928a70,20),(0x928a80,40),(0x914428,60),(0x928a90,80),(0x91442c,100),(0x928a7c,36),(0x928a84,50),(0x94f9fc,75),(0x8e96ac,1),(0x9142a0,.001),(0x9142ac,.01),(0x8f04c8,-1),(0x909bf0,.1),(0x8e96a8,.5),(0x974224,-90),(0x94fa3c,-180),(0xa5c720,3.01029995664),(0xa5b808,-70)]:
        if not math.isclose(pe.f32(address),value,rel_tol=1e-6):raise ValueError('Numerical evidence mismatch')
    if struct.unpack('<d',pe.at_rva(0x8fd018,8))[0]!=1000:raise ValueError('Timebase constant mismatch')
    if struct.unpack('<5f',pe.at_rva(0xa5c550,20))!=(0,20,40,60,80):raise ValueError('Detector anchors differ')
    calibration=struct.unpack('<10f',pe.at_rva(0xa5c528,40))
    if calibration[::2]!=(0,36,50,75,100) or not all(a>b for a,b in zip(calibration[1::2],calibration[3::2])):raise ValueError('Calibration curve differs')
    exp_sites=imported_call_sites(pe,setup)
    log_sites=imported_call_sites(pe,detector)
    if [x['symbol'] for x in exp_sites]!=['expf']*3 or [x['symbol'] for x in log_sites]!=['log10f']*4:raise ValueError('Math import mismatch')
    records=[fingerprint_record(pe,a,14) for a in (0x77a0b28,0x77a0b60)]
    if any(not r['writable'] for r in records):raise ValueError('Expected file-backed writable calibration')
    # Confirm the selected record addresses and arithmetic constants used by the code.
    by={i.address-pe.image_base:i for i in setup+detector}
    links={0x5cfcc0:0x77a0b60,0x5cfcce:0x77a0b28,0x5cfe47:0x77a0b64,0x5cfe56:0x77a0b2c,0x5cfe80:0x77a0b68,0x5cfe94:0x77a0b30,0x5cfeac:0x77a0b84,0x5cfed0:0x77a0b4c,0x5cff18:0x77a0b80,0x5cff2a:0x77a0b48,0x5cff60:0x77a0b8c,0x5cff70:0x77a0b54,0x5cff9d:0x77a0b90,0x5cffa4:0x77a0b58,0x5cfe4e:0x8fd018,0x5d179d:0x8e96a8,0x5d182b:0x8e96a8,0x5d187f:0xa5c720,0x5d188d:0xa5b808}
    for site,target in links.items():
        if site not in by or not by[site].operands.endswith(hex(pe.image_base+target)):raise ValueError(f'RIP evidence mismatch {site:#x}')
    regions=[
      {'id':'detector_morph','title':'Continuous adjacent detector selection','start_rva':'0x5cfcb8','end_rva_exclusive':'0x5cfd67','confidence':'instruction-verified for valid 0..100 inputs','equation':'Choose adjacent detector groups at anchors 0,20,40,60,80,100; interpolate with t=(v-lo)/(hi-lo). Source field 0x18c. Above 100 the code instead uses index 0 and weight 0; do not infer out-of-range behavior as clamping.'},
      {'id':'target_calibration','title':'Nonlinear target-coordinate calibration','start_rva':'0x5cfd61','end_rva_exclusive':'0x5cfe3f','confidence':'instruction-verified structure','equation':'Object field 0x190 is clamped to 0..100, then interpolated through a five-point decreasing offset curve. Raw values withheld; curve coordinates 0,36,50,75,100.'},
      {'id':'rate_setup','title':'Rate-dependent adaptive coefficients','start_rva':'0x5cfe3f','end_rva_exclusive':'0x5cffd9','confidence':'instruction-verified structure','equation':'Two file-backed 14-word calibration records feed the setup. For positive F, step=1000/F; rate-dependent exponentials produce peak decay and two one-pole update coefficients. The attack increment factor is B*step/max(T,0.01); the reciprocal gain-dependence factor is 1/max(D,0.5). Record selection is controlled by a flag. F units inferred from sample-rate-like source field.'},
      {'id':'blended_detector','title':'Two-stage interpolation of peak and power in logarithmic units','start_rva':'0x5d172e','end_rva_exclusive':'0x5d18d6','confidence':'instruction-verified for positive finite envelopes','equation':'Within each adjacent group blend floored 20*log10(peak) with floored 10*log10(2*power), using the selected calibration weight. Interpolate the two group levels, subtract 3.0103 dB and the control-dependent offset, then subtract the lookup origin (-70). The zero-input branch requires separate path validation.'}
    ]
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'checkpoint_count':checks,'constant_reference_count':len(links),'calibration_records':records,'offset_curve':fingerprint_record(pe,0xa5c528,10),'math_calls':exp_sites+log_sites,'regions':regions,'field_references':{hex(off):field_refs(setup,pe.image_base,'rsi',off) for off in (0x190,0x198)},'limits':['No vendor arrays or complete implementation exported. File-backed calibration values may be changed at runtime.','Numeric control fields are not proven APVTS/GUI parameter mappings. No real audio, CPU or VMR dynamics claim.']}
