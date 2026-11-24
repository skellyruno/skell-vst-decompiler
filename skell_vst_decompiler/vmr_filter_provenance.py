"""Bounded FG-2A filter setup and downstream nonlinear feedback evidence.

Read-only exact-build analysis. Reports expose location/role evidence, not
vendor coefficient arrays, pseudocode dumps, or a reconstructed processor.
"""
import argparse
import json
import struct
from .pe import PE
from .disasm import disassemble, direct_calls
from .extended_dsp import VMR_COPY, check_region

# block, producer call, three copy stores, first/second channel state read starts
BANKS = (
    (0x2f0, 0x14b82b, (0x14b91c,0x14b927,0x14b932), 0x14d674,0x14d6e0),
    (0x360, 0x14b85e, (0x14b93d,0x14b948,0x14b953), 0x14db5f,0x14dbc6),
    (0x3d0, 0x14b888, (0x14b95e,0x14b969,0x14b974), 0x14dc9f,0x14dd0e),
    (0x440, 0x14b8bb, (0x14b97f,0x14b98a,0x14b995), 0x14de8f,0x14defc),
    (0x4b0, 0x14b8e5, (0x14b9a0,0x14b9a7,0x14b9c5), 0x14df7f,0x14dfe8),
    (0x520, 0x14b90f, (0x14b9d3,0x14b9e1,0x14b9e8), 0x14e0df,0x14e14c),
)
ACTIVE = (('b0',0),('b1',8),('b2',16),('a1',32),('a2',40))


def verify(pe, objdump='objdump'):
    if pe.path.name!='FG-2A.epl' or pe.sha256!=VMR_COPY['FG-2A.epl'][0]:
        raise ValueError('Unsupported source fingerprint')
    regions=[]
    def add(key,title,start,end,checks,description):
        ins=disassemble(pe,start,end-start,objdump)
        regions.append(dict(id=key,title=title,equation=description,
            confidence='exact-build static instruction evidence; runtime dispatch and audio unverified',
            direct_calls=direct_calls(pe,ins),**check_region(pe,start,end,checks,objdump=objdump)))
    add('fg2a_rate_setup_context','FG-2A shared filter setup context',0x14b5e0,0x14b624,[
        (0x14b5fe,'movsd','xmm0,QWORD PTR [rcx+0x10]'),(0x14b605,'mov','rdx,QWORD PTR [rcx]'),
        (0x14b608,'mov','rdi,rcx')],
        'The setup routine preserves the context in RDI; its first pointer supplies the parent object. The +0x10 scalar is subsequently passed to each coefficient generator.')
    setup_checks=[(0x14b7fd,'mov','rbx,QWORD PTR [rdi]'),(0x14b800,'movsd','xmm6,QWORD PTR [rdi+0x10]'),
                  (0x14b805,'add','rbx,0x1360'),(0x14b80c,'movsd','xmm8,QWORD PTR [rdi+0x18]')]
    # Explicit stack destinations of six coefficient generator calls; then copy
    # three 128-bit chunks per record. None of the coefficient values are exported.
    generators=((0x14b81a,'rbp-0x50',0x14b82b,0xbf7cd0),
        (0x14b837,'rbp-0x80',0x14b85e,0xbfa810),
        (0x14b872,'rbp-0x20',0x14b888,0xbf5290),
        (0x14b894,'rbp+0x10',0x14b8bb,0xbfc260),
        (0x14b8cf,'rbp+0x40',0x14b8e5,0xbf5290),
        (0x14b8f9,'rbp+0x70',0x14b90f,0xbf5290))
    for lea,dest,call,target in generators:
        setup_checks += [(lea,'lea',f'rdx,[{dest}]'),(call,'call',hex(pe.image_base+target))]
    # Store instructions are verified with decoded exact operands; use a fixed
    # expected register order from the inspected dataflow, not arbitrary writes.
    regs=(('xmm0','xmm1','xmm0'),('xmm1','xmm0','xmm1'),('xmm0','xmm1','xmm0'),
          ('xmm1','xmm0','xmm1'),('xmm0','xmm1','xmm0'),('xmm1','xmm0','xmm1'))
    copy_ins=disassemble(pe,0x14b914,0x14b9ef-0x14b914,objdump)
    stack_starts=(-0x50,-0x80,-0x20,0x10,0x40,0x70)
    for (base,_,stores,_,_),rr,stack_start in zip(BANKS,regs,stack_starts):
        for i,(site,reg) in enumerate(zip(stores,rr)):
            setup_checks.append((site,'movups',f'XMMWORD PTR [rbx+{base+16*i:#x}],{reg}'))
            # Confirm the latest register definition is the intended chunk from
            # that generator's stack record, not an adjacent coefficient bank.
            defs=[x for x in copy_ins if x.address-pe.image_base<site and x.operands.split(',')[0]==reg]
            if not defs:raise ValueError('Missing stack-copy source')
            latest=defs[-1]
            offset=stack_start+16*i
            expected=f'{reg},XMMWORD PTR [rbp{offset:+#x}]'
            if latest.mnemonic!='movups' or latest.operands!=expected:
                raise ValueError('Unexpected generator stack-copy source')
            setup_checks.append((latest.address-pe.image_base,'movups',expected))
    setup_checks += [(0x14b9b7,'mov','QWORD PTR [rsp+0x50],rbx'),(0x14b9fc,'call','0x180149a90')]
    add('fg2a_six_filter_writers','Six filter coefficient generator/copy endpoints',0x14b7fd,0x14ba01,setup_checks,
        'Six 48-byte coefficient records are generated in separate stack locations, then copied to the +0x1360 processing subobject. The five active coefficients in each are read below; the sixth slot is not read in these recurrences and is not counted. Generator internals and runtime selection remain unverified.')
    add('fg2a_filter_processing_context','Matching processing context',0x14d590,0x14d5df,[
        (0x14d5bd,'mov','rax,QWORD PTR [rcx+0x30]'),(0x14d5c8,'mov','rbx,QWORD PTR [rcx]'),
        (0x14d5d8,'movsxd','rsi,DWORD PTR [rax+0x4]')],
        'The candidate processor uses RBX as the supplied subobject and a per-stream count from context +0x30.')
    add('fg2a_filter_processing_parent','Processing caller passes identical relative subobject',0x156f04,0x156f54,[
        (0x156f04,'lea','rax,[rbx+0x1360]'),(0x156f0b,'mov','QWORD PTR [rsp+0x20],rax'),
        (0x156f4a,'lea','rcx,[rsp+0x20]'),(0x156f4f,'call','0x18014d590')],
        'The caller supplies the same parent-relative offset +0x1360 as the setup path. Runtime object identity is not asserted.')
    # Verify two channel passes for every block, including distinct state stores.
    links=[]
    for base,call,stores,ch0,ch1 in BANKS:
        end=ch1+0x68
        ins=disassemble(pe,ch0,end-ch0,objdump)
        checks=[]; endpoints=[]
        for ch,start in enumerate((ch0,ch1)):
            window=[i for i in ins if start<=i.address-pe.image_base<start+0x60]
            state=base-0x40+0x20*ch
            sites={}
            for role,delta in ACTIVE:
                matches=[i for i in window if i.mnemonic in ('mulsd','movsd') and i.operands.endswith(f'QWORD PTR [rbx+{base+delta:#x}]')]
                if len(matches)!=1:raise ValueError(f'Ambiguous coefficient read {base:#x}/{ch}/{role}')
                i=matches[0];site=i.address-pe.image_base
                checks.append((site,i.mnemonic,i.operands));sites[role]=hex(site)
            for off in (state,state+8):
                matches=[i for i in window if i.mnemonic=='movsd' and i.operands.startswith(f'QWORD PTR [rbx+{off:#x}],')]
                if len(matches)!=1:raise ValueError(f'Missing distinct channel state {off:#x}')
                i=matches[0];checks.append((i.address-pe.image_base,i.mnemonic,i.operands))
            # The first two subtraction operations establish the negative feedback
            # sign in the state equations. Validate rather than infer from offsets.
            subs=[i for i in window if i.mnemonic=='subsd']
            if len(subs)!=2:raise ValueError(f'Unexpected filter recurrence {base:#x}/{ch}')
            for i in subs:checks.append((i.address-pe.image_base,i.mnemonic,i.operands))
            endpoints.append({'channel':ch,'state_offsets':[hex(state),hex(state+8)],'read_sites':sites})
        add(f'fg2a_filter_{base:x}',f'FG-2A stereo biquad block {base:#x}',ch0,end,checks,
            'Two independent state pairs share five active coefficients. Local DF2T relationship: y=b0*x+z1; z1_next=b1*x-a1*y+z2; z2_next=b2*x-a2*y. Setup copy endpoints verified; generator equations and live audio remain open.')
        links.append({'record_offset':hex(base),'generator_call_rva':hex(call),'copy_store_rvas':[hex(x) for x in stores],'channels':endpoints})
    for r,val in ((0xeaa4b8,-1.0),(0xea9448,1.0),(0xeaa428,2.0)):
        if struct.unpack('<d',pe.at_rva(r,8))[0]!=val:raise ValueError('Unexpected sign constant')
    if struct.unpack('<Q',pe.at_rva(0xeaa880,8))[0]!=0x8000000000000000:raise ValueError('Unexpected sign mask')
    # A call with the identical subobject pointer leads to the feedback setup.
    # Seven curve fields per polarity and three scalar gain/feedback fields.
    curve_writes=((0x160,0x149d1e,'xmm2'),(0x168,0x149d41,'xmm1'),(0x170,0x149d5c,'xmm0'),
                  (0x178,0x149ced,'xmm11'),(0x180,0x149d77,'xmm0'),(0x188,0x149ce1,'xmm3'),(0x190,0x149d02,'xmm4'),
                  (0x198,0x149dcd,'xmm2'),(0x1a0,0x149de5,'xmm1'),(0x1a8,0x149e40,'xmm0'),
                  (0x1b0,0x149dff,'xmm8'),(0x1b8,0x149e37,'xmm10'),(0x1c0,0x149e0d,'xmm3'),(0x1c8,0x149e1a,'xmm4'),
                  (0x1d0,0x149b44,'xmm6'),(0x1d8,0x149b79,'xmm0'),(0x1e0,0x149b85,'xmm1'))
    add('fg2a_feedback_setup_context','Feedback setup receives the processing subobject',0x149a90,0x149ab8,[
        (0x149ab2,'mov','r14,rcx'),(0x149ab5,'mov','rsi,QWORD PTR [rcx]')],
        'RSI is the first pointer of the setup context previously populated with the same +0x1360 relative subobject.')
    curve_checks=[(r,'movsd',f'QWORD PTR [rsi+{f:#x}],{reg}') for f,r,reg in curve_writes]
    curve_checks += [(0x149c96,'movsd','xmm6,QWORD PTR [rip+0xd6078a]'),
        (0x149cf6,'subsd','xmm2,xmm10'),(0x149d0a,'subsd','xmm0,xmm3'),
        (0x149d16,'mulsd','xmm0,xmm6'),(0x149d1a,'divsd','xmm2,xmm0'),
        (0x149d29,'mulsd','xmm0,xmm6'),(0x149d31,'mulsd','xmm0,xmm3'),(0x149d35,'subsd','xmm1,xmm0'),
        (0x149d3d,'subsd','xmm0,xmm1'),(0x149d49,'subsd','xmm0,xmm2'),(0x149d4d,'mulsd','xmm0,xmm3'),
        (0x149dbe,'subsd','xmm0,xmm3'),(0x149dc2,'mulsd','xmm0,xmm6'),(0x149dc6,'divsd','xmm2,xmm0'),
        (0x149dd5,'mulsd','xmm0,xmm6'),(0x149dd9,'mulsd','xmm0,xmm3'),(0x149ddd,'subsd','xmm1,xmm0'),
        (0x149ded,'subsd','xmm0,xmm1'),(0x149e25,'subsd','xmm0,xmm2'),(0x149e33,'mulsd','xmm0,xmm3')]
    add('fg2a_feedback_curve_setup','Two polarity curve writers and quadratic transition setup',0x149b36,0x149e48,curve_checks,
        'All fourteen piecewise curve fields and three associated scale/feedback fields have local setup writes. With ordered distinct breakpoints L,H and high-region slope m, the quadratic transition uses A=(m-1)/(2*(H-L)), B=1-2*A*L, C=(1-B-A*L)*L. This establishes value and slope continuity at L and matching slope at H; the independently calculated affine intercept is not assumed continuous at H. Full calibration scalar origins and runtime behavior remain open.')
    add('fg2a_feedback_handoff','Nonlinear processor downstream handoff',0x14e238,0x14e2ab,[
        (0x14e23d,'mov','QWORD PTR [rbp+0x150],rbx'),(0x14e29f,'lea','rcx,[rbp+0x150]'),
        (0x14e2a6,'call','0x18014f340')], 'The polynomial processor passes its subobject as the first pointer of the downstream context.')
    add('fg2a_feedback_context','Downstream feedback context and history',0x14f340,0x14f40b,[
        (0x14f361,'mov','rsi,QWORD PTR [rcx]'),(0x14f36e,'movsd','xmm6,QWORD PTR [rip+0xd5b142]'),
        (0x14f37c,'movsd','xmm7,QWORD PTR [rip+0xd5a0c4]'),(0x14f3c9,'movsd','xmm1,QWORD PTR [rsi+0x1d0]'),
        (0x14f3ee,'call','0x18006f820'),(0x14f3f3,'movsd','xmm2,QWORD PTR [rbx+rdi*1+0xa0]')],
        'The downstream context recovers the same subobject pointer, reads input scale and per-stream feedback history. The scalar helper paths are previously cataloged.')
    add('fg2a_feedback_nonlinearity','Sign-selected piecewise feedback transform',0x14f69d,0x14f75e,[
        (0x14f6b3,'addsd','xmm2,QWORD PTR [rdx]'),(0x14f6cb,'movaps','xmm3,xmm6'),(0x14f6d0,'movaps','xmm3,xmm7'),
        (0x14f6d8,'lea','rax,[rsi+0x160]'),(0x14f6e1,'lea','rax,[rsi+0x198]'),
        (0x14f6eb,'mulsd','xmm2,xmm0'),(0x14f6ef,'movsd','xmm0,QWORD PTR [rax+0x28]'),
        (0x14f6f8,'jae','0x18014f72c'),(0x14f6fa,'comisd','xmm2,QWORD PTR [rax+0x30]'),
        (0x14f6ff,'jbe','0x18014f70d'),(0x14f701,'mulsd','xmm2,QWORD PTR [rax+0x18]'),
        (0x14f706,'addsd','xmm2,QWORD PTR [rax+0x20]'),(0x14f713,'mulsd','xmm0,QWORD PTR [rax+0x8]'),
        (0x14f718,'mulsd','xmm1,xmm2'),(0x14f71c,'mulsd','xmm1,QWORD PTR [rax]'),
        (0x14f727,'addsd','xmm2,QWORD PTR [rax+0x10]'),(0x14f72c,'mulsd','xmm2,xmm3'),
        (0x14f730,'movsd','QWORD PTR [rcx+rdx*1],xmm2'),(0x14f73d,'mulsd','xmm2,QWORD PTR [rsi+0x1d8]'),
        (0x14f745,'jns','0x18014f6b3'),(0x14f755,'movsd','QWORD PTR [rbx+rdi*1+0xa0],xmm2')],
        'Finite-input scalar tail: previous scaled output feeds the next input; sign chooses one of two piecewise identity/quadratic/affine magnitude curves. The signed output is stored before feedback multiplication. This establishes a local nonlinear feedback loop, not the final gain-reduction law.')
    add('fg2a_feedback_difference','First difference and residual branch',0x14facd,0x14fb22,[
        (0x14facd,'movsd','xmm1,QWORD PTR [rdx+rcx*1]'),(0x14fad5,'subsd','xmm0,QWORD PTR [rbx+rdi*1+0xa8]'),
        (0x14fade,'movsd','QWORD PTR [rcx],xmm0'),(0x14fae6,'movsd','QWORD PTR [rbx+rdi*1+0xa8],xmm1'),
        (0x14faf3,'jne','0x18014facd'),(0x14faf5,'movsd','xmm1,QWORD PTR [rsi+0x1e0]'),
        (0x14fb09,'call','0x18006f820'),(0x14fb1d,'call','0x18006f880')],
        'First difference d[n]=v[n]-v[n-1], followed by scaling and a residual difference on the previously inspected scalar helper paths.')
    add('fg2a_feedback_output','Downstream final local output and two-channel stride',0x14fdef,0x14fe25,[
        (0x14fdef,'mov','r8,QWORD PTR [rbp+0x1e8]'),(0x14fdfe,'mov','rdx,r13'),
        (0x14fe01,'call','0x18006f880'),(0x14fe11,'inc','r12d'),(0x14fe14,'add','rbx,0xb0'),
        (0x14fe1b,'cmp','r12d,0x2'),(0x14fe1f,'jb','0x18014f3c0')],
        'The candidate local output difference is written to a supplied output buffer; repeat for two streams at 0xb0-byte state stride. Final host output routing is not proven.')
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'regions':regions,
        'checkpoint_count':sum(r['checkpoint_count'] for r in regions), 'filter_records_total':6,
        'filter_records_linked':len(links),'active_coefficient_fields_total':30,'active_coefficient_fields_linked':sum(len(x['channels'][0]['read_sites']) for x in links),
        'channel_read_endpoints_verified':sum(len(c['read_sites']) for x in links for c in x['channels']), 'filter_links':links,
        'feedback_curve_write_endpoints_verified':len(curve_writes),'feedback_curve_write_endpoints_total':17,
        'feedback_curve_write_sites':[{'field':hex(f),'site_rva':hex(r)} for f,r,_ in curve_writes],
        'limits':'Scoped writer-to-reader endpoint coverage only. Generator formula internals, six rational-field roles across two records, complete gain law and vendor runtime/audio remain unverified. No raw coefficient values or runnable processor exported.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary');p.add_argument('--objdump',default='objdump');a=p.parse_args()
    print(json.dumps(verify(PE(a.binary),a.objdump),indent=2,allow_nan=False))

if __name__=='__main__':main()
