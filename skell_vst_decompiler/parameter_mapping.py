"""Build-specific parameter-to-object joins. Never infer identity from offset alone."""
import re
from .coloration import lookup_slots
from .curve_provenance import require
from .disasm import disassemble
from .equations import TVB_SHA256


def indexed_slot_names(pe,ins,start_offset,dest_offset,count):
    """Decode a bounded list of adjacent LEA string / MOV stack-slot pairs.
    The calling verifier must separately establish the loop consuming the list.
    """
    if not 1<=count<=128 or start_offset<0 or dest_offset<0:raise ValueError('Invalid indexed slot range')
    found={}
    for a,b in zip(ins,ins[1:]):
        m=re.fullmatch(r'rax,\[rip[+-]0x[0-9a-f]+\]\s*#\s*0x([0-9a-f]+)',a.operands)
        n=re.fullmatch(r'QWORD PTR \[rbp\+0x([0-9a-f]+)\],rax',b.operands)
        if a.mnemonic!='lea' or b.mnemonic!='mov' or not m or not n:continue
        off=int(n[1],16)
        if not start_offset<=off<start_offset+8*count or (off-start_offset)%8:continue
        idx=(off-start_offset)//8
        if idx in found:raise ValueError('Duplicate indexed initializer')
        rva=int(m[1],16)-pe.image_base; name=pe.cstring_rva(rva,128)
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,100}',name):raise ValueError('Unexpected parameter name')
        found[idx]={'name':name,'slot_offset':hex(dest_offset+8*idx),'string_rva':hex(rva),'initializer_rva':hex(a.address-pe.image_base)}
    if set(found)!=set(range(count)):raise ValueError('Incomplete indexed initializer')
    return [found[i] for i in range(count)]


def verify_parameter_mapping(pe,objdump='objdump'):
    if pe.sha256!=TVB_SHA256:raise ValueError('Unexpected source fingerprint')
    host=disassemble(pe,0x33baa0,0x63b7,objdump)
    init=disassemble(pe,0x34b730,0xf16,objdump)
    constructor=disassemble(pe,0x34c7a0,0x318,objdump)
    process=disassemble(pe,0x342840,0x229d,objdump)
    dsp=disassemble(pe,0x5cfa7f,0x2564,objdump)
    n=require(pe,host,[(0x33baf5,'mov','r15,rcx'),(0x33c00d,'lea','rcx,[r15+0x1e90]'),(0x33c014,'call','0x18034b730'),(0x33c6ca,'lea','rbx,[r15+0x160]'),(0x33c639,'xor','ebx,ebx'),(0x33c640,'mov','rdx,QWORD PTR [rbp+rbx*8+0x90]'),(0x33c64f,'call','0x1800b7fa0'),(0x33c65a,'call','0x180326b70'),(0x33c65f,'mov','QWORD PTR [r15+rbx*8+0xe80],rax'),(0x33c667,'inc','rbx'),(0x33c66a,'cmp','rbx,0x13'),(0x33c66e,'jb','0x18033c640')])
    n+=require(pe,init,[(0x34b749,'mov','rsi,rcx'),(0x34bd12,'lea','rcx,[rsi+0x324d8]'),(0x34bd19,'call','0x18034c7a0'),(0x34bd1f,'lea','rcx,[rsi+0x33500]'),(0x34bd26,'call','0x18034c7a0')])
    n+=require(pe,constructor,[(0x34c7af,'mov','rdi,rcx'),(0x34c8bd,'mov','QWORD PTR [rdi],rax')])
    vt=next(i for i in constructor if i.address-pe.image_base==0x34c7d8)
    if not vt.operands.endswith(hex(pe.image_base+0x9273d0)):raise ValueError('Unexpected constructor vtable')
    # Resolve the virtual processing entry from the actual table, not a coincident field offset.
    import struct
    if struct.unpack('<Q',pe.at_rva(0x9273d0+5*8,8))[0]!=pe.image_base+0x5cfa50:raise ValueError('Unexpected virtual process entry')
    n+=require(pe,process,[(0x34289e,'mov','rdi,rcx'),(0x342d4f,'mov','r14d,0x1'),(0x343a09,'mov','r12d,0x2'),(0x343ea2,'mov','DWORD PTR [rdi+0x344ec],r14d'),(0x343ea9,'mov','DWORD PTR [rdi+0x35514],r12d')])
    # Check register definitions of the two fixed mode writes within this code region.
    for reg,site in [('r14',0x342d4f),('r12',0x343a09)]:
        aliases={reg,reg+'d',reg+'w',reg+'b'}
        writes=[i.address-pe.image_base for i in process if i.address-pe.image_base<0x343ea2 and i.operands.split(',')[0] in aliases and i.mnemonic not in ('cmp','test','push')]
        if writes!=[site]:raise ValueError('Mode register provenance differs')
    main_names=lookup_slots(pe,[i for i in host if 0x340d06<=i.address-pe.image_base<0x340f31])
    expected=['comp_on','comp_threshold_db','comp_ratio','comp_knee_db','comp_attack_ms','comp_release_ms','comp_auto_release','comp_makeup_db','comp_auto_makeup','comp_mix','comp_schpf_on','comp_input_db','comp_all_in','comp_output_db','comp_cla_output_db']
    if [x['name'] for x in main_names]!=expected or [int(x['slot_offset'],16) for x in main_names]!=list(range(0x3b308,0x3b380,8)) or any(x['literal_base']!='r15' for x in main_names):raise ValueError('Primary name/slot mapping differs')
    second=indexed_slot_names(pe,[i for i in host if 0x33c52f<=i.address-pe.image_base<0x33c639],0x90,0xe80,19)
    expected2=['comp2_on','comp2_threshold_db','comp2_ratio','comp2_knee_db','comp2_attack_ms','comp2_release_ms','comp2_auto_release','comp2_makeup_db','comp2_auto_makeup','comp2_mix','comp2_schpf_on','comp2_input_db','comp2_all_in','comp2_output_db','fx_comp2_la2a_limit','fx_comp2_la2a_hifreq','fx_comp2_compress','fx_comp2_algorithm','comp2_on']
    if [x['name'] for x in second]!=expected2:raise ValueError('Secondary name/slot mapping differs')
    extras=lookup_slots(pe,[i for i in host if 0x33c7e4<=i.address-pe.image_base<0x33c86f])
    if [x['name'] for x in extras]!=['fx_comp_compress','fx_comp_algorithm','fx_comp_la2a_limit','fx_comp_la2a_hifreq']:raise ValueError('Extra names differ')
    slots={int(x['slot_offset'],16):x['name'] for x in main_names+second}
    for x in extras:
        if x['literal_base']!='rbx':raise ValueError('Unexpected alias base')
        slots[0x160+int(x['slot_offset'],16)]=x['name']
    # Verify read, dereference, conversion and final store endpoints. Intermediate branch math
    # is not claimed to be a complete parameter transfer function.
    rows=[]
    primary=[(0x3b318,0x154,0x34310e,0x343115,0x3431bb,'movss','xmm0'),(0x3b320,0x158,0x3431c3,0x3431ca,0x3431e2,'movss','xmm0'),(0x3b328,0x15c,0x3431ea,0x3431f1,0x343215,'movss','xmm0'),(0x3b330,0x160,0x34321d,0x343224,0x343242,'movss','xmm0'),(0x3b338,0x164,0x34324a,0x343251,0x34325d,'mov','al'),(0x3b350,0x170,0x343263,0x34326a,0x343282,'movss','xmm0'),(0x3b358,0x178,0x34328a,0x343291,0x34329d,'mov','al'),(0x3b368,0x180,0x3432a3,0x3432aa,0x3432b6,'mov','al'),(0x1b8,0x188,0x3441b4,0x3441bb,0x3441c7,'mov','al'),(0x1c0,0x18c,0x3441cd,0x3441d4,0x3441ea,'movss','xmm11')]
    secondary=[(0xe88,0x150,0x343ed4,0x343ee0,0x343f04,'movss','xmm0'),(0xe90,0x154,0x343f0c,0x343f18,0x343f3c,'movss','xmm0'),(0xe98,0x158,0x343f44,0x343f58,0x343f7c,'movss','xmm0'),(0xea0,0x15c,0x343f84,0x343f99,0x343fba,'movss','xmm2'),(0xea8,0x160,0x343fc2,0x343fce,0x343ff2,'movss','xmm2'),(0xeb0,0x164,0x343ffa,0x344006,0x344018,'mov','al'),(0xeb8,0x168,0x34401e,0x34402a,0x344046,'movss','xmm0'),(0xec0,0x16c,0x34404e,0x34405a,0x34406b,'mov','al'),(0xec8,0x170,0x344071,0x34407d,0x34409b,'movss','xmm0'),(0xed0,0x178,0x3440a3,0x3440af,0x3440c1,'mov','al'),(0xed8,0x17c,0x3440c7,0x3440d3,0x3440ed,'movss','xmm13'),(0xee8,0x174,0x3440f6,0x344102,0x344121,'movss','xmm0'),(0xef0,0x188,0x344129,0x344135,0x344146,'mov','al'),(0xef8,0x18c,0x34414c,0x344158,0x344176,'movss','xmm0'),(0xf00,0x190,0x34417e,0x34418a,0x3441ac,'movss','xmm0')]
    for base,group in ((0x34368,primary),(0x35390,secondary)):
        for slot,field,load,deref,store,op,value in group:
            size='BYTE' if op=='mov' else 'DWORD'; reg='ecx' if group is primary else 'eax'
            n+=require(pe,process,[(load,'mov',f'rax,QWORD PTR [rdi+{slot:#x}]'),(deref,'mov',f'{reg},DWORD PTR [rax]'),(store,op,f'{size} PTR [rdi+{base+field:#x}],{value}')])
            rows.append({'parameter_id':slots[slot],'host_slot_offset':hex(slot),'compressor_base_offset':hex(base),'dsp_field_offset':hex(field),'load_rva':hex(load),'store_rva':hex(store),'confidence':'instruction-verified source/destination endpoints; intervening range/default logic present'})
    n+=require(pe,dsp,[(0x5cfa9c,'mov','r14d,DWORD PTR [rcx+0x184]'),(0x5cfb08,'mov','ecx,DWORD PTR [rcx+0x150]'),(0x5cfb12,'mov','eax,DWORD PTR [rsi+0x154]'),(0x5cfb36,'mov','eax,DWORD PTR [rsi+0x158]'),(0x5cfb3f,'mov','eax,DWORD PTR [rsi+0x15c]'),(0x5cfb45,'mov','edx,DWORD PTR [rsi+0x160]'),(0x5cfb4b,'movzx','r8d,BYTE PTR [rsi+0x164]'),(0x5cfb53,'mov','r9d,DWORD PTR [rsi+0x18c]'),(0x5cfd61,'mov','eax,DWORD PTR [rsi+0x190]')])
    n+=require(pe,process,[(0x342fa8,'mov','rax,QWORD PTR [rdi+0x3b310]'),(0x342fb1,'mov','rax,QWORD PTR [rdi+0x3b378]'),(0x342fee,'mov','rax,QWORD PTR [rdi+0x3b360]'),(0x343060,'addss','xmm2,xmm0'),(0x34308c,'movss','DWORD PTR [rdi+0x344e4],xmm1'),(0x3430db,'movss','DWORD PTR [rdi+0x344b8],xmm1'),(0x343106,'movss','DWORD PTR [rdi+0x344dc],xmm0'),(0x343137,'mov','rdx,QWORD PTR [rdi+0x3b370]')])
    return {'schema_version':1,'source':pe.path.name,'binary_sha256':pe.sha256,'checkpoint_count':n,'constructor_chain':{'parent_initializer_rva':'0x33c014','embedded_offset':'0x1e90','child_constructor_rva':'0x34c7a0','vtable_rva':'0x9273d0','virtual_process_rva':'0x5cfa50','instance_base_offsets':['0x34368','0x35390']},'host_slots':{hex(k):v for k,v in sorted(slots.items())},'mapped_endpoints':rows,'regions':[{'id':'compressor_objects','title':'Two constructed compressor instances','start_rva':'0x34bd12','end_rva_exclusive':'0x34bd2b','confidence':'instruction-verified object base chain','equation':'Parent + 0x1e90 + child offsets 0x324d8 or 0x33500. Both use same verified compressor constructor/vtable.'},{'id':'mode_assignments','title':'Processing path assigns mode 1 and mode 2','start_rva':'0x343ea2','end_rva_exclusive':'0x343eb0','confidence':'instruction-verified mode writes for this path','equation':'Writes numeric mode 1 to first instance field 0x184, mode 2 to second. Does not prove all host paths use fixed modes.'},{'id':'primary_threshold_drive','title':'Primary threshold, input and output coupling','start_rva':'0x342fa8','end_rva_exclusive':'0x3431b3','confidence':'instruction-verified endpoints, intermediate equations incomplete','equation':'Primary threshold and CLA output feed conditional/table-based gain calculation with input and output parameters; destinations include threshold 0x150, field 0x174 and field 0x17c. Not simple one-to-one knob mapping.'},{'id':'secondary_optical','title':'Optical detector and compression amount bindings','start_rva':'0x344129','end_rva_exclusive':'0x3441b4','confidence':'instruction-verified endpoints','equation':'fx_comp2_la2a_limit -> 0x188; fx_comp2_la2a_hifreq -> 0x18c; fx_comp2_compress -> 0x190, after default and range logic.'}], 'limits':['Static endpoint mapping for one native host processing path; not a full APVTS automation trace. Exact threshold/input/output mapping, all alternate dispatch paths and actual audio remain unverified.','No vendor implementation or parameter tables exported.']}
