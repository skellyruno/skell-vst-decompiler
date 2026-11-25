"""Read-only exact-string navigation; RIP LEA candidates are not parameter mappings."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from .pe import PE, PEFormatError
from .navigation import runtime_ranges, containing_range
from .disasm import disassemble

# Restrict candidate search to 64-bit RIP-relative LEA, then verify decoded
# instruction boundary and target in a real unwind region.
LEA = re.compile(rb'[\x48-\x4f]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]')
REF = re.compile(r'^([a-z0-9]+),\[rip(?:[+-](?:0x[0-9a-f]+|[0-9]+))?\]#(0x[0-9a-f]+)(?:<[^>]+>)?$')
CALL = re.compile(r'^0x([0-9a-f]+)(?:\s+<[^>]+>)?$')
ARGS = {'rcx','rdx','r8','r9'}
REGS = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')


def literals(pe, names):
    out={}
    for name in names:
        for encoding,term in [('ascii',b'\0'),('utf-16le',b'\0\0')]:
            raw=name.encode(encoding)+term
            for s in pe.sections:
                if s.executable or s.name not in ('.rdata','.data'):
                    continue
                data=pe.at_rva(s.rva,s.file_size)
                at=0
                while (pos:=data.find(raw,at))>=0:
                    at=pos+1
                    # Suffix pooling is legal. Mark rather than discard matches.
                    key=s.rva+pos
                    out.setdefault(key,[]).append({'name':name,'encoding':encoding})
                    if len(out)>4096:raise ValueError('Too many literal locations')
    return out


def raw_lea_hits(pe, targets):
    for s in pe.sections:
        if not s.executable or s.name!='.text':continue
        data=pe.at_rva(s.rva,s.file_size)
        for m in LEA.finditer(data):
            pos=m.start()
            if pos+7>len(data):continue
            dest=s.rva+pos+7+struct.unpack_from('<i',data,pos+3)[0]
            if dest in targets:yield s.rva+pos,dest


def local_references(pe, instructions, wanted, literals_by_rva):
    """Only LEA -> direct argument-register CALL within straight-line window.

    Any unrecognized instruction invalidates argument tracking. No alias,
    branch, return-value or stack propagation claimed.
    """
    rows=[];active={}
    for ins in instructions:
        addr=ins.address-pe.image_base
        op=ins.mnemonic.lower();arg=ins.operands.lower().strip()
        normalized=arg.replace(' ','').replace('\t','')
        ref=REF.fullmatch(normalized) if op=='lea' else None
        if ref and addr in wanted and int(ref[2],16)-pe.image_base==wanted[addr]:
            dest=wanted[addr]
            row={'site_rva':hex(addr),'string_rva':hex(dest),'register':ref[1],'literals':literals_by_rva[dest]}
            rows.append(row)
            active.pop(ref[1],None)
            if ref[1] in ARGS:active[ref[1]]=row
            continue
        if op=='call':
            call=CALL.fullmatch(arg)
            if call:
                for reg,row in active.items():
                    if addr-int(row['site_rva'],16)<=64:
                        row['direct_argument_call']={'site_rva':hex(addr),'target_rva':hex(int(call[1],16)-pe.image_base),'argument_register':reg}
            active.clear();continue
        # Conservative whitelist: operations writing an exact 64-bit GPR
        # remove its tracked value; no subregister/stack alias assumptions.
        if op in ('lea','mov') and normalized.split(',')[0] in REGS:
            active.pop(normalized.split(',')[0],None)
        elif op in ('nop','int3'):
            if op=='int3':active.clear()
        else:active.clear()
    return rows


def scalar_reader_chains(pe, instructions, references):
    """Recognize one explicit MSVC x64 call/dereference/float-transfer shape.

    This is a compiled endpoint candidate, not proof of a parameter API.
    The same shape may occur in unrelated object code. Require contiguous
    decoded instructions and the exact return-register use; no alias tracing.
    """
    index={i.address-pe.image_base:j for j,i in enumerate(instructions)}
    rows=[]
    for ref in references:
        first=ref.get('direct_argument_call')
        if not first or first['argument_register']!='rdx':continue
        j=index.get(int(first['site_rva'],16))
        if j is None:continue
        seq=instructions[j+1:j+6]
        if len(seq)!=5:continue
        args=[i.operands.split('#',1)[0].lower().replace(' ','').replace('\t','') for i in seq]
        call=CALL.fullmatch(seq[2].operands.lower().strip())
        if ([i.mnemonic for i in seq]!=['mov','mov','call','mov','movd'] or
            args[0]!='rdx,qwordptr[rax]' or not re.fullmatch(r'rcx,r(?:bx|si|di|12|13|14|15)',args[1]) or not call or
            args[3]!='ecx,dwordptr[rax]' or args[4]!='xmm0,ecx'):
            continue
        dest=int(call[1],16)-pe.image_base
        try:pe.at_rva(dest,1,executable=True)
        except PEFormatError:continue
        rows.append({'reference_rva':ref['site_rva'],'constructor_call_rva':first['site_rva'],
                     'reader_call_rva':hex(seq[2].address-pe.image_base),'reader_target_rva':hex(dest),
                     'scalar_load_rva':hex(seq[3].address-pe.image_base),'float_transfer_rva':hex(seq[4].address-pe.image_base)})
    return rows


def scan(path,names,limit=128,tools=('objdump','llvm-objdump')):
    path=Path(path)
    if not path.is_file() or path.is_symlink() or not 0<path.stat().st_size<=256*1024*1024:
        raise ValueError('Expected bounded PE module')
    if not 1<=len(names)<=128 or len(set(names))!=len(names) or any(not isinstance(n,str) or not re.fullmatch(r'[ -~]{1,128}',n) for n in names):
        raise ValueError('Expected unique printable ASCII names')
    if type(limit) is not int or not 1<=limit<=256 or not tools or any(t not in ('objdump','llvm-objdump') for t in tools):
        raise ValueError('Invalid scan budget or decoder')
    pe=PE(path);ranges=runtime_ranges(pe);strings=literals(pe,names);hits=dict(raw_lea_hits(pe,strings));groups={};uncovered=0
    for site,dest in hits.items():
        region=containing_range(ranges,site)
        if not region or region['bytes']>32768:uncovered+=1;continue
        start=int(region['start_rva'],16)
        groups.setdefault(start,(region,{}))[1][site]=dest
    # Prioritize functions referencing several distinct requested literals.
    ordered=sorted(groups,key=lambda r:(-len(set(groups[r][1].values())),r))
    rows=[];chains=[];disagreement=0
    for start in ordered[:limit]:
        region,wanted=groups[start]
        instructions=[disassemble(pe,start,region['bytes'],t) for t in tools]
        decoded=[local_references(pe,ins,wanted,strings) for ins in instructions]
        # Keep only fully identical observations across decoders.
        common=[r for r in decoded[0] if all(r in d for d in decoded[1:])]
        disagreement+=sum(1 for r in decoded[0] if r not in common)
        for r in common:r['region_start_rva']=hex(start)
        rows.extend(common)
        joined=[scalar_reader_chains(pe,ins,common) for ins in instructions]
        chains.extend(r for r in joined[0] if all(r in d for d in joined[1:]))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pe.sha256:raise ValueError('Source changed')
    return {'schema_version':1,'binary_sha256':pe.sha256,'source':path.name,'names':list(names),'literal_locations':len(strings),'raw_candidate_sites':len(hits),'uncovered_sites':uncovered,'eligible_regions':len(groups),'scanned_regions':min(limit,len(groups)),'decoder_disagreements':disagreement,'decoders':list(tools),'references':rows,'scalar_reader_candidates':chains,'limits':'Exact ASCII/UTF16LE substrings and RIP-relative LEA in selected unwind regions only. Direct argument-register evidence is straight-line and conservative; no semantic parameter identity, call role, return-value propagation or runtime dispatch. Raw candidates are not instructions.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('module');p.add_argument('names',nargs='+');p.add_argument('--limit',type=int,default=128);a=p.parse_args();print(json.dumps(scan(a.module,a.names,a.limit),indent=2))


if __name__=='__main__':main()
