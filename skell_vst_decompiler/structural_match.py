"""Bounded dual-decoder mnemonic comparison of explicit native function scopes.

Mnemonics are weak structural evidence only, not a statement of equivalent DSP.
No target modules execute, and no disassembly/pseudocode is written to reports.
"""
import argparse
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
from .pe import PE
from .navigation import runtime_ranges, containing_range
from .disasm import disassemble


def canonical(ins):
    # GNU represents some prefix NOPs with the pseudo-instruction 'data16'.
    if ins.mnemonic == 'data16' and ins.operands.lstrip().startswith(('nop','data16 nop')):
        return 'nop'
    return ins.mnemonic


def signature(pe, rva, tools=('objdump','llvm-objdump')):
    if type(rva) is not int or rva<0 or not tools or any(t not in ('objdump','llvm-objdump') for t in tools):
        raise ValueError('Invalid native scope or disassembler')
    region=containing_range(runtime_ranges(pe),rva)
    if region is None or not 32<=region['bytes']<=8192:
        raise ValueError('No supported bounded unwind region')
    start=int(region['start_rva'],16)
    a=[]
    for t in tools:
        a.append([(x.address-pe.image_base,canonical(x)) for x in disassemble(pe,start,region['bytes'],t)])
    if any(other!=a[0] for other in a[1:]):
        raise ValueError('Disassemblers disagree on scoped instruction addresses/opcodes')
    return {'region':region,'start':start,'region_sha256':hashlib.sha256(pe.at_rva(start,region['bytes'],executable=True)).hexdigest(),
            'instruction_count':len(a[0]),'mnemonics':[op for _,op in a[0]]}


def compare(path_a,rva_a,path_b,rva_b,tools=('objdump','llvm-objdump')):
    paths=(Path(path_a),Path(path_b))
    if any(not p.is_file() or p.is_symlink() or not 0<p.stat().st_size<=256*1024*1024 for p in paths):
        raise ValueError('Use two bounded local PE files')
    left,right=PE(paths[0]),PE(paths[1])
    a=signature(left,rva_a,tools);b=signature(right,rva_b,tools)
    score=SequenceMatcher(None,a['mnemonics'],b['mnemonics'],autojunk=False).ratio()
    # No full function token sequence leaves this function.
    return {'schema_version':1,'type':'native_mnemonic_comparison',
        'left':{'source':paths[0].name,'binary_sha256':left.sha256,'region_rva':a['region']['start_rva'],'bytes':a['region']['bytes'],'region_sha256':a['region_sha256'],'instruction_count':a['instruction_count']},
        'right':{'source':paths[1].name,'binary_sha256':right.sha256,'region_rva':b['region']['start_rva'],'bytes':b['region']['bytes'],'region_sha256':b['region_sha256'],'instruction_count':b['instruction_count']},
        'ordered_mnemonic_similarity':round(score,6),'ordered_mnemonics_identical':a['mnemonics']==b['mnemonics'],
        'exact_region_bytes_identical':a['region_sha256']==b['region_sha256'],
        'decoder_consensus':True,'decoders':list(tools),
        'limits':'Identical opcode sequences and/or exact function bytes do not prove identical coefficients, object state, routing, sound, source code or runtime DSP. External data and callee targets may differ.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('left',type=Path);p.add_argument('left_rva',type=lambda v:int(v,0));p.add_argument('right',type=Path);p.add_argument('right_rva',type=lambda v:int(v,0))
    x=p.parse_args();print(json.dumps(compare(x.left,x.left_rva,x.right,x.right_rva),indent=2))


if __name__=='__main__':main()
