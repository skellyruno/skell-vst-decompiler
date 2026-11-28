"""Read-only post-gain coloration evidence and generic SOS stability summaries.
No raw third-party coefficient tables or reconstructed processor are exported.
"""
import cmath
import hashlib
import math
import struct
import re
from .disasm import disassemble, imported_call_sites
from .equations import TVB_SHA256
from .curve_provenance import require
from .detector_mapping import fingerprint_record


def sos_summary(data, rates, stages, probes=(20,100,1000,5000,10000,20000)):
    """Summarize normalized real DF2T coefficients b0,b1,b2,a1,a2 as float64.
    Hash the source; return aggregate response and pole bounds, not coefficients.
    """
    rates=tuple(rates)
    if not 1<=len(rates)<=64 or not 1<=stages<=64 or len(data)!=len(rates)*stages*40:
        raise ValueError('Unexpected coefficient bank dimensions')
    if any(not math.isfinite(f) or f<=0 for f in rates) or len(set(rates))!=len(rates):
        raise ValueError('Invalid sample rates')
    if len(probes)>128 or any(not math.isfinite(f) or f<=0 for f in probes):
        raise ValueError('Invalid probe frequencies')
    sections=list(struct.iter_unpack('<5d',data))
    if any(not all(math.isfinite(x) and abs(x)<1e8 for x in s) for s in sections):
        raise ValueError('Invalid coefficient')
    rows=[]
    for k,rate in enumerate(rates):
        ss=sections[k*stages:(k+1)*stages]
        radii=[]
        for _,_,_,a1,a2 in ss:
            root=cmath.sqrt(a1*a1-4*a2)
            radii.extend((abs((-a1+root)*.5),abs((-a1-root)*.5)))
        response={}
        for f in probes:
            if f>=rate/2:continue
            z=cmath.exp(-2j*math.pi*f/rate); db=0.0
            for b0,b1,b2,a1,a2 in ss:
                numerator=abs(b0+b1*z+b2*z*z)
                denominator=abs(1+a1*z+a2*z*z)
                if denominator==0:raise ValueError('Singular probe response')
                db+=20*math.log10(max(numerator,1e-300)/denominator)
            response[str(f)]=round(db,6)
        rows.append({'sample_rate':rate,'max_pole_radius':max(radii),'stable':max(radii)<1,'linear_response_db':response})
    return {'rows':len(rates),'stages_per_row':stages,'coefficient_count':len(sections)*5,'sha256':hashlib.sha256(data).hexdigest(),'rate_summaries':rows,'limits':'Linear filter-only math, not a measurement of a plugin output.'}


def nearest_rate(rates,requested):
    if not rates or not math.isfinite(requested) or requested<=0 or any(not math.isfinite(f) or f<=0 for f in rates):raise ValueError('Invalid rates')
    return min(range(len(rates)),key=lambda k:abs(rates[k]-requested))


def lookup_slots(pe, instructions):
    """Recognize exact 7-instruction native handle lookup pattern, not dataflow proof.
    The caller must establish object identity and the two called functions separately.
    """
    result=[]
    for k in range(len(instructions)-6):
        a,b,c,d,e,f,g=instructions[k:k+7]
        if (a.mnemonic,b.mnemonic,c.mnemonic,d.mnemonic,e.mnemonic,f.mnemonic,g.mnemonic)!=('lea','lea','call','mov','mov','call','mov'):continue
        m=re.fullmatch(r'rdx,\[rip[+-]0x[0-9a-f]+\]\s*#\s*0x([0-9a-f]+)',a.operands)
        dest=re.fullmatch(r'QWORD PTR \[(rbx|r15)\+0x([0-9a-f]+)\],rax',g.operands)
        if not m or not dest or not b.operands.startswith('rcx,[rbp+') or d.operands!='rdx,QWORD PTR [rax]' or e.operands!='rcx,r12':continue
        if not all(re.fullmatch(r'0x[0-9a-f]+',i.operands) for i in (c,f)):continue
        target=int(m[1],16)-pe.image_base
        try: name=pe.cstring_rva(target,128)
        except ValueError:continue
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,100}',name):continue
        result.append({'name':name,'string_rva':hex(target),'lookup_rva':hex(a.address-pe.image_base),'slot_write_rva':hex(g.address-pe.image_base),'literal_base':dest[1],'slot_offset':hex(int(dest[2],16)),'string_helper_rva':hex(int(c.operands,16)-pe.image_base),'lookup_helper_rva':hex(int(f.operands,16)-pe.image_base)})
    return result


def verify_coloration(pe,objdump='objdump'):
    if pe.sha256!=TVB_SHA256:raise ValueError('Unexpected source fingerprint')
    prologue=disassemble(pe,0x5cfa7f,0x2564,objdump)
    if pe.f32(0x8e96ac)!=1.0 or pe.u32(0x8e9820)!=0x7fffffff:raise ValueError('Coloration unity/absolute-value constants differ')
    writes=[i for i in prologue if i.operands.startswith(('xmm9,','xmm6,')) and i.mnemonic not in ('cmp','comiss','ucomiss','test')]
    if [i.address-pe.image_base for i in writes if i.operands.startswith('xmm9,') and i.address-pe.image_base<0x5d1d60]!=[0x5cfb29]:raise ValueError('Unity register provenance differs')
    if not any(i.address-pe.image_base==0x5d031e and i.operands.endswith(hex(pe.image_base+0x8e9820)) for i in writes):raise ValueError('Abs mask provenance differs')
    audio=disassemble(pe,0x5d1d60,0x1c4,objdump)
    helper=disassemble(pe,0x5d2330,0xed,objdump)
    prepare=disassemble(pe,0x5cf350,0x118,objdump)
    setup=disassemble(pe,0x5d29e6,0x160,objdump)
    n=require(pe,audio,[(0x5d1d65,'movaps','xmm3,xmm11'),(0x5d1d69,'mulss','xmm3,DWORD PTR [r15+rdi*4]'),(0x5d1d6f,'cmp','r12d,0x2'),(0x5d1d73,'jne','0x1805d1e8a'),(0x5d1d95,'andps','xmm1,xmm6'),(0x5d1d9c,'mulss','xmm0,xmm1'),(0x5d1da8,'mulss','xmm2,xmm3'),(0x5d1dac,'addss','xmm1,xmm9'),(0x5d1db1,'addss','xmm2,xmm0'),(0x5d1db5,'divss','xmm2,xmm1'),(0x5d1db9,'addss','xmm2,xmm3'),(0x5d1d98,'shl','rax,0x5'),(0x5d1dca,'mulsd','xmm4,QWORD PTR [rsi+0xd58]'),(0x5d1dd2,'mulsd','xmm1,QWORD PTR [rsi+0xd60]'),(0x5d1dda,'addsd','xmm4,QWORD PTR [rax+rsi*1+0xda8]'),(0x5d1de9,'mulsd','xmm0,QWORD PTR [rsi+0xd70]'),(0x5d1df1,'subsd','xmm1,xmm0'),(0x5d1df8,'addsd','xmm1,QWORD PTR [rax+rsi*1+0xdb0]'),(0x5d1e01,'movsd','QWORD PTR [rax+rsi*1+0xda8],xmm1'),(0x5d1e0d,'mulsd','xmm0,QWORD PTR [rsi+0xd78]'),(0x5d1e15,'mulsd','xmm3,QWORD PTR [rsi+0xd68]'),(0x5d1e1d,'subsd','xmm3,xmm0'),(0x5d1e21,'movsd','QWORD PTR [rax+rsi*1+0xdb0],xmm3'),(0x5d1e2a,'mulsd','xmm2,QWORD PTR [rsi+0xd80]'),(0x5d1e32,'mulsd','xmm1,QWORD PTR [rsi+0xd88]'),(0x5d1e3a,'addsd','xmm2,QWORD PTR [rax+rsi*1+0xdb8]'),(0x5d1e46,'mulsd','xmm0,QWORD PTR [rsi+0xd98]'),(0x5d1e52,'subsd','xmm1,xmm0'),(0x5d1e59,'addsd','xmm1,QWORD PTR [rax+rsi*1+0xdc0]'),(0x5d1e62,'movsd','QWORD PTR [rax+rsi*1+0xdb8],xmm1'),(0x5d1e6b,'mulsd','xmm4,QWORD PTR [rsi+0xd90]'),(0x5d1e73,'mulsd','xmm0,QWORD PTR [rsi+0xda0]'),(0x5d1e7b,'subsd','xmm4,xmm0'),(0x5d1e7f,'movsd','QWORD PTR [rax+rsi*1+0xdc0],xmm4'),(0x5d1e8a,'cmp','r12d,0x1'),(0x5d1e8e,'jne','0x1805d1ee1'),(0x5d1ea2,'shl','rdx,0x4'),(0x5d1eb4,'add','rdx,0x220'),(0x5d1ebb,'andps','xmm2,xmm6'),(0x5d1ebe,'mulss','xmm1,xmm3'),(0x5d1ec5,'mulss','xmm2,xmm0'),(0x5d1ec9,'addss','xmm1,xmm3'),(0x5d1ecd,'addss','xmm2,xmm1'),(0x5d1ed9,'call','0x1805d2330'),(0x5d1ee1,'cmp','BYTE PTR [rsp+0x30],0x0'),(0x5d1ef7,'mulss','xmm1,xmm3'),(0x5d1eff,'mulss','xmm0,DWORD PTR [rcx+rdi*4]'),(0x5d1f04,'addss','xmm0,xmm1'),(0x5d1f08,'mulss','xmm0,xmm7'),(0x5d1f18,'movss','DWORD PTR [r15+rdi*4],xmm0')])
    # Confirm each section's coefficient accesses and two state writes; no table payload exported.
    n+=require(pe,helper,[(0x5d2330,'movsxd','rax,DWORD PTR [rcx+0x21c]'),(0x5d233a,'imul','rcx,rax,0x78'),(0x5d2373,'movsd','QWORD PTR [rdx],xmm1'),(0x5d238a,'movsd','QWORD PTR [rdx+0x8],xmm3'),(0x5d23b8,'movsd','QWORD PTR [rdx+0x10],xmm1'),(0x5d23d0,'movsd','QWORD PTR [rdx+0x18],xmm2'),(0x5d23fe,'movsd','QWORD PTR [rdx+0x20],xmm1'),(0x5d2417,'movsd','QWORD PTR [rdx+0x28],xmm3'),(0x5d241c,'ret','')])
    actual=[]
    for i in helper:
        m=re.search(r'QWORD PTR \[rcx\+rax\*1(?:\+0x([0-9a-f]+))?\]',i.operands)
        if m:actual.append(int(m[1] or '0',16))
    if sorted(actual)!=list(range(0,120,8)):raise ValueError('Unexpected coefficient access coverage')
    n+=require(pe,prepare,[(0x5cf383,'mov','QWORD PTR [rcx+0x198],rax'),(0x5cf3bd,'cmova','r8d,eax'),(0x5cf3e6,'cmova','r8d,eax'),(0x5cf40f,'cmova','r8d,eax'),(0x5cf438,'cmova','r8d,eax'),(0x5cf458,'cmova','r8d,eax'),(0x5cf45c,'mov','DWORD PTR [rsi+0x21c],r8d'),(0x5cf463,'call','0x1805d24a0')])
    n+=require(pe,setup,[(0x5d29ee,'divsd','xmm0,xmm13'),(0x5d2a2b,'movsd','QWORD PTR [rsi+0xd58],xmm0'),(0x5d2a3e,'movsd','QWORD PTR [rsi+0xd60],xmm1'),(0x5d2a46,'mov','QWORD PTR [rsi+0xd68],0x0'),(0x5d2a51,'movsd','QWORD PTR [rsi+0xd70],xmm6'),(0x5d2a59,'mov','QWORD PTR [rsi+0xd78],0x0'),(0x5d2a72,'divsd','xmm12,xmm13'),(0x5d2a8b,'divsd','xmm6,QWORD PTR [rip+0x489c7d]'),(0x5d2aa2,'divsd','xmm9,xmm0'),(0x5d2afa,'movsd','QWORD PTR [rsi+0xd80],xmm1'),(0x5d2b06,'movsd','QWORD PTR [rsi+0xd88],xmm2'),(0x5d2b26,'movsd','QWORD PTR [rsi+0xd90],xmm1'),(0x5d2b2e,'movsd','QWORD PTR [rsi+0xd98],xmm2'),(0x5d2b3e,'movsd','QWORD PTR [rsi+0xda0],xmm1')])
    links={0x5d1d7f:0x77a0b9c,0x5d1d8d:0x77a0b98,0x5d1da0:0x77a0ba0,0x5d1e97:0x77a0b18,0x5d1ea9:0x77a0b1c,0x5d1ed1:0x77a0b20,0x5d2342:0xa5bff0,0x5cf393:0xa5bfb8,0x5d29e6:0xa5c718,0x5d2a64:0xa5c728}
    by={i.address-pe.image_base:i for i in audio+helper+prepare+setup}
    if any(site not in by or not by[site].operands.endswith(hex(pe.image_base+target)) for site,target in links.items()):raise ValueError('Coloration reference mismatch')
    calls=imported_call_sites(pe,setup)
    if [c['symbol'] for c in calls]!=['tan','pow','sin','pow','cos']:raise ValueError('Unexpected coefficient setup imports')
    rates=struct.unpack('<6d',pe.at_rva(0xa5bfb8,48))
    if rates!=(44100,48000,88200,96000,176400,192000):raise ValueError('Unexpected sample rate anchors')
    bank=sos_summary(pe.at_rva(0xa5bff0,720),rates,3)
    if not all(row['stable'] for row in bank['rate_summaries']):raise ValueError('Unstable coefficient bank')
    handles=lookup_slots(pe,disassemble(pe,0x33c7e4,0x8b,objdump))
    expected=['fx_comp_compress','fx_comp_algorithm','fx_comp_la2a_limit','fx_comp_la2a_hifreq']
    if [r['name'] for r in handles]!=expected or [r['slot_offset'] for r in handles]!=['0x48','0x50','0x58','0x60']:raise ValueError('Unexpected handle slots')
    # Guard against matching unrelated objects based on a displacement alone.
    ctor=disassemble(pe,0x34c7a0,0x130,objdump)
    n+=require(pe,ctor,[(0x34c87d,'mov','DWORD PTR [rdi+0x18c],0x42c80000'),(0x34c887,'mov','DWORD PTR [rdi+0x190],0x42200000'),(0x34c8bd,'mov','QWORD PTR [rdi],rax')])
    if not next(i for i in ctor if i.address-pe.image_base==0x34c7d8).operands.endswith(hex(pe.image_base+0x9273d0)):raise ValueError('Wrong constructor vtable')
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'checkpoint_count':n,'linked_reference_count':len(links),'mode1_filter_bank':bank,'rate_selection_examples':{str(f):rates[nearest_rate(rates,f)] for f in (44100,50000,64000,70000,192000)},'color_calibration_fingerprints':[fingerprint_record(pe,a,3) for a in (0x77a0b18,0x77a0b98)],'coefficient_setup_math_calls':calls,'host_lookup_slots':handles,'regions':[
        {'id':'mode1_audio_color','title':'FET mode output coloration','start_rva':'0x5d1e8a','end_rva_exclusive':'0x5d1ee1','confidence':'instruction-verified local recurrence','equation':'With x the post-gain sample, asymmetric polynomial max(floor,x+a*x*x+b*x*abs(x)) feeds three serial DF2T stages. Scalar constants fingerprinted, not exported.'},
        {'id':'mode2_audio_color','title':'Optical mode output coloration','start_rva':'0x5d1d79','end_rva_exclusive':'0x5d1e88','confidence':'instruction-verified local recurrence','equation':'With x the post-gain sample, x+(a*x*x+b*x*abs(x))/(1+abs(x)/c) feeds two serial DF2T-shaped double-precision stages. Mode-specific data references verified.'},
        {'id':'fet_color_filter','title':'Three post-gain filter sections','start_rva':'0x5d2330','end_rva_exclusive':'0x5d241d','confidence':'instruction-verified structure','equation':'Selected row contains 15 double coefficients in 120 bytes, three stages with 6 double state values per channel. Linear responses computed locally, no vendor coefficient arrays published.'},
        {'id':'nearest_rate','title':'FET filter coefficient row selection','start_rva':'0x5cf350','end_rva_exclusive':'0x5cf468','confidence':'instruction-verified structure','equation':'Choose row by minimum absolute difference from six rate anchors; strict comparisons preserve earlier index at ties. Actual host behavior not measured.'},
        {'id':'opto_color_filter_setup','title':'Rate-dependent optical output filter coefficients','start_rva':'0x5d29e6','end_rva_exclusive':'0x5d2b46','confidence':'instruction-verified structure','equation':'First filter is first order (b2=a2=0); second is a biquad with b1=a1. Coefficient generation uses tan, pow, sin, cos with stored rate. Full runtime response not measured.'},
        {'id':'parameter_lookup','title':'Four named host lookup slots','start_rva':'0x33c7e4','end_rva_exclusive':'0x33c86f','confidence':'instruction-verified handle lookup; DSP binding unresolved','equation':'Names resolve through common lookup helpers to literal pointer slots. This does not establish the destination compressor fields or setter path.'}], 'limits':['No raw vendor coefficient or calibration arrays, binary code, or reconstructed processor exported.','The host lookup object is not proven identical to the DSP object. Matching displacement alone is insufficient.','No VST3 execution, actual sound equivalence, VMR algorithm or production DSP changes.']}
