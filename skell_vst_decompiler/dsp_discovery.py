"""Bounded, read-only PE DSP candidate ranking; never loads target code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from .pe import PE
from .navigation import runtime_ranges
from .disasm import disassemble


def features(instructions):
    arithmetic=memory=backward=0
    for ins in instructions:
        op=ins.mnemonic.removeprefix('v')
        if re.fullmatch(r'(add|sub|mul|div|min|max|sqrt|fmadd\d*|fmsub\d*)(ss|sd|ps|pd)',op):
            arithmetic+=1
        if '[' in ins.operands and ('xmm' in ins.operands or 'ymm' in ins.operands):
            memory+=1
        target=re.match(r'(?:0x)?([0-9a-fA-F]+)(?:\s|$)',ins.operands)
        if op.startswith('j') and target and int(target[1],16)<ins.address:
            backward+=1
    score=arithmetic+min(memory,arithmetic)+4*min(backward,4)
    return {'arithmetic':arithmetic,'vector_memory':memory,'backward_branches':backward,'score':score}


def discover(path, limit=64, rvas=(), tool='objdump'):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or not 0<path.stat().st_size<=256*1024*1024:
        raise ValueError('Choose one bounded PE module file, not a VST3 bundle directory')
    if type(limit) is not int or not 1<=limit<=128 or len(rvas)>limit:
        raise ValueError('Invalid discovery budget')
    pe=PE(path);entries=runtime_ranges(pe)
    eligible=[r for r in entries if 32<=r[1]-r[0]<=8192]
    if rvas:
        selected=[]
        for addr in rvas:
            matches=[r for r in eligible if r[0]<=addr<r[1]]
            if len(matches)!=1:raise ValueError('RVA has no eligible unwind range')
            if matches[0] not in selected:selected.append(matches[0])
    else:
        n=min(limit,len(eligible))
        selected=[eligible[i*len(eligible)//n] for i in range(n)] if n else []
    rows=[]
    for lo,hi,_ in selected:
        data=pe.at_rva(lo,hi-lo,executable=True)
        f=features(disassemble(pe,lo,hi-lo,tool))
        rows.append({'start_rva':hex(lo),'end_rva_exclusive':hex(hi),'region_sha256':hashlib.sha256(data).hexdigest(),**f,
                     'status':'CANDIDATE' if f['arithmetic']>=4 and f['vector_memory']>=2 else 'UNRESOLVED'})
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pe.sha256:raise ValueError('Source changed during scan')
    rows.sort(key=lambda r:(r['status']!='CANDIDATE',-r['score'],r['start_rva']))
    return {'schema_version':1,'type':'dsp_discovery','binary_sha256':pe.sha256,'source':path.name,
            'runtime_records':len(entries),'eligible_records':len(eligible),'scanned_records':len(rows),'candidates':rows,
            'limits':'Sampled unwind ranges, not all functions. Arithmetic heuristic only; no algorithm identity, parameter mapping or vendor execution.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('binary');p.add_argument('--limit',type=int,default=64);p.add_argument('--rva',type=lambda x:int(x,0),action='append',default=[]);p.add_argument('--objdump',choices=['objdump','llvm-objdump'],default='objdump')
    a=p.parse_args();print(json.dumps(discover(a.binary,a.limit,a.rva,a.objdump),indent=2,allow_nan=False))


if __name__=='__main__':main()
