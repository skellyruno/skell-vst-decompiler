"""Class-anchored DSP navigation; static candidates, not recovered algorithms."""
import hashlib
from pathlib import Path
import re
from .pe import PE
from .classgraph import class_graph
from .navigation import runtime_ranges, containing_range
from .disasm import disassemble
from .dsp_discovery import features, discover


def call_edges(pe, instructions):
    for ins in instructions:
        if ins.mnemonic != "call":continue
        m=re.fullmatch(r"0x([0-9a-fA-F]+)(?:\s+<[^>]+>)?",ins.operands)
        if m:
            yield {"site_rva":hex(ins.address-pe.image_base),"target_rva":hex(int(m[1],16)-pe.image_base)}

def processor_names(pe):
    names=set()
    for s in pe.sections:
        if s.name not in ('.data','.rdata') or s.executable:
            continue
        for m in re.finditer(rb'\.\?AV([A-Za-z_][A-Za-z_0-9]{0,100}AudioProcessor)@@\x00',pe.at_rva(s.rva,s.file_size)):
            names.add(m[1].decode('ascii'))
            if len(names)>16:
                raise ValueError('Too many processor names; choose explicit roots')
    return sorted(names)


def anchored(path, limit=64, tool='objdump'):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or not 0<path.stat().st_size<=256*1024*1024:
        raise ValueError('Expected bounded PE module')
    if type(limit) is not int or not 8<=limit<=128:
        raise ValueError('Invalid discovery budget')
    pe=PE(path); entries=runtime_ranges(pe)
    rows={}; roots={}; edges=[]; unresolved=0
    for name in processor_names(pe):
        for cls in class_graph(pe,name,max_classes=32)['classes']:
            if cls['type']!='.?AV'+name+'@@':continue
            for table in cls['vtables']:
                if not any(b['type']=='.?AVAudioProcessor@juce@@' for b in table['hierarchy']['base_records']):continue
                for slot in table['candidate_slots']:
                    r=slot['unwind_region']
                    if r and 32<=r['bytes']<=8192:
                        start=int(r['start_rva'],16)
                        roots.setdefault(start,[]).append({'class':cls['type'],'vtable_rva':table['vtable_rva'],'slot':slot['slot'],'target_rva':slot['rva']})
    if not roots:
        report=discover(path,limit=limit,tool=tool)
        report['strategy']='sampled_fallback_no_validated_processor_class'
        return report
    def scan(start, region, depth):
        ins=disassemble(pe,start,region['bytes'],tool)
        f=features(ins)
        # Local arithmetic plus loop structure, not a semantic proof.
        row={'start_rva':hex(start),'end_rva_exclusive':region['end_rva_exclusive'],
             'region_sha256':hashlib.sha256(pe.at_rva(start,region['bytes'],executable=True)).hexdigest(),
             **f,'depth':depth,'root_slots':roots.get(start,[]),
             'status':'CANDIDATE' if f['arithmetic']>=4 and f['vector_memory']>=2 else 'UNRESOLVED'}
        rows[start]=row
        return list(call_edges(pe,ins))
    # Reserve half the budget for following calls rather than spending it all on wrappers.
    selected=sorted(roots,key=lambda s:(-containing_range(entries,s)['bytes'],s))[:limit//2]
    pending={s:scan(s,containing_range(entries,s),0) for s in selected}
    expanded=[]
    for depth in (0,1):
        candidates=sorted((s for s in pending if rows[s]['depth']==depth and rows[s]['status']=='CANDIDATE'),key=lambda s:(-rows[s]['score'],s))[:4]
        for s in candidates:
            expanded.append(hex(s))
            for call in pending[s]:
                target=int(call['target_rva'],16);region=containing_range(entries,target)
                if not region or not 32<=region['bytes']<=8192:
                    unresolved+=1;continue
                dest=int(region['start_rva'],16)
                if dest not in rows:
                    if len(rows)>=limit:
                        unresolved+=1;continue
                    pending[dest]=scan(dest,region,depth+1)
                edges.append({'caller_rva':hex(s),**call,'containing_rva':hex(dest)})
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pe.sha256:raise ValueError('Source changed')
    return {'schema_version':1,'type':'dsp_discovery','strategy':'validated_processor_slots_then_direct_calls',
            'source':path.name,'binary_sha256':pe.sha256,'runtime_records':len(entries),
            'root_region_count':len(roots),'scanned_records':len(rows),'expanded_roots':expanded,'unfollowed_call_sites':unresolved,
            'candidates':sorted(rows.values(),key=lambda r:(r['status']!='CANDIDATE',r['depth'],-r['score'],r['start_rva'])),
            'direct_edges':edges,'limits':'Validated RTTI base class and candidate slots; no proven slot semantics or runtime dispatch. Arithmetic can include math/library helpers. Bounded direct calls only; indirect calls, leaf functions and omitted roots unresolved.'}
