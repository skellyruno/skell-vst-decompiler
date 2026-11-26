"""Static candidate table navigation for validated module-processor RTTI wrappers.

Select explicit class/slot; identify the local indexed-call shape, compatible
RIP-address loads and relocation-backed table entries. No runtime target proof,
protection analysis, or claim of exact table extent.
"""
import re
import struct
from .classgraph import class_graph
from .disasm import disassemble
from .dispatch_audit import agreement, canonical
from .pe import PEFormatError
from .relocation_navigation import relocated_slots


def inspect_wrapper(pe,start,length,relocations=None):
    left,right=[disassemble(pe,start,length,t) for t in ('objdump','llvm-objdump')]
    by_address={i.address:i for i in left}
    good={i.address for i in right if i.address in by_address and agreement(pe,by_address[i.address],i)}
    relocations=set(relocated_slots(pe)) if relocations is None else relocations
    rows=[]
    for j,i in enumerate(right):
        op,arg=canonical(i);m=re.fullmatch(r'qwordptr\[(r[a-z0-9]+)\+rdx\*8\]',arg)
        if op!='call' or not m or j==0 or i.address not in good:continue
        prev=right[j-1];p,arg=canonical(prev)
        selector=re.fullmatch(r'rdx,dwordptr\[rax(?:\+(\d+))?\]',arg)
        if p!='movsxd' or not selector or prev.address not in good:continue
        base=m[1]; candidates=[]
        # Look back only within this bounded decoded wrapper. Every compatible
        # RIP LEA is a candidate, NOT a reaching definition on every CFG path.
        for k in right[:j-1]:
            o,a=canonical(k)
            if o!='lea' or k.address not in good:continue
            ref=re.fullmatch(re.escape(base)+r',\[rip([+-])(\d+)\]',a)
            if not ref:continue
            site=k.address-pe.image_base
            try:raw=pe.at_rva(site,7,executable=True)
            except PEFormatError:continue
            if raw[0] not in (0x48,0x4c) or raw[1]!=0x8d or raw[2]&0xc7!=5:continue
            disp=struct.unpack_from('<i',raw,3)[0];parsed=int(ref[2])*(-1 if ref[1]=='-' else 1)
            regs=['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15']
            if regs[((raw[2]>>3)&7)+(8 if raw[0]&4 else 0)]!=base or parsed not in (disp,disp%(1<<64)):continue
            table=site+7+disp
            region=next((s for s in pe.sections if not s.executable and s.rva<=table and table+8<=s.rva+min(s.file_size,s.virtual_size)),None)
            if region is None:continue
            count=0
            for slot in range(8):
                loc=table+8*slot
                if loc not in relocations or loc+8>region.rva+min(region.file_size,region.virtual_size):break
                target=struct.unpack('<Q',pe.at_rva(loc,8))[0]-pe.image_base
                try:pe.at_rva(target,1,executable=True)
                except PEFormatError:break
                count+=1
            if count:candidates.append({'load_rva':hex(site),'table_rva':hex(table),'relocated_code_pointer_prefix':count,'writable':bool(region.characteristics&0x80000000)})
        rows.append({'call_rva':hex(i.address-pe.image_base),'selector_read_rva':hex(prev.address-pe.image_base),'selector_offset':int(selector[1] or 0),'table_load_candidates':candidates})
    return {'wrapper_rva':hex(start),'bytes':length,'rows':rows,'limits':'Compatible earlier RIP loads and adjacent selector reads only. No CFG reaching definition or actual runtime dispatch; maximum eight relocation-backed entries sampled, not table extent.'}


def module_wrappers(pe):
    graph=class_graph(pe,'ModuleProcessor');relocs=set(relocated_slots(pe));out=[]
    for c in graph['classes']:
        if not c['type'].startswith('.?AV?$') or 'ModuleProcessor@' not in c['type']:continue
        for t in c['vtables']:
            if t['subobject_offset']!=0:continue
            for s in t['candidate_slots']:
                if s['slot']!=8:continue
                r=s['unwind_region'];start=int(s['rva'],16)
                if not r or int(r['start_rva'],16)!=start or not 32<=r['bytes']<=8192:continue
                out.append({'class':c['type'],'vtable_rva':t['vtable_rva'],'slot':8,**inspect_wrapper(pe,start,r['bytes'],relocs)})
    return {'sha256':pe.sha256,'wrappers':out}
