"""Bounded direct-transfer audit. Never resolve indirect destinations."""
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
import re
import subprocess
from .disasm import Instruction
from .flow_guards import direct_target, entry_guards
from .pe import PEFormatError


@dataclass(frozen=True)
class RawInstruction:
    instruction: Instruction
    raw: bytes


_RAW = re.compile(r'^\s*([0-9a-fA-F]+):[ \t]*([0-9a-fA-F]{2}(?: +[0-9a-fA-F]{2})*)[ \t]*\t[ \t]*([a-z.][a-z0-9.]*)\s*(.*?)\s*$')


def parse_raw(stdout, raw, va):
    """Only retain complete rows matching the actual bounded input bytes."""
    result = {}
    for line in stdout.splitlines():
        m = _RAW.match(line)
        if not m:
            continue
        site = int(m[1],16); data = bytes.fromhex(m[2]); offset=site-va
        if not 0<=offset<len(raw) or not 1<=len(data)<=15 or offset+len(data)>len(raw):
            continue
        if raw[offset:offset+len(data)]!=data:
            raise PEFormatError('Decoder bytes disagree with original window')
        if site in result or (result and site<=next(reversed(result))):
            raise ValueError('Duplicate or unordered raw decoder row')
        result[site]=RawInstruction(Instruction(site,m[3],m[4]),data)
    return result


def raw_decode(pe,start,length,tool):
    if tool not in ('objdump','llvm-objdump'):
        raise ValueError('Unsupported raw decoder')
    if type(start) is not int or type(length) is not int or not 1<=length<=32768:
        raise ValueError('Invalid bounded scope')
    raw=pe.at_rva(start,length,executable=True); va=pe.image_base+start
    args=[tool,'-d','-M','intel']
    if tool=='objdump': args.extend(['--show-raw-insn','--insn-width=15'])
    r=subprocess.run(args+[f'--start-address={hex(va)}',f'--stop-address={hex(va+length)}',str(pe.path)],capture_output=True,text=True,timeout=25,check=False)
    if r.returncode or len(r.stdout)>6_000_000:
        raise RuntimeError('Raw decoder failed or exceeded bound: '+r.stderr[:300])
    return parse_raw(r.stdout,raw,va)


def relative(raw,site,mnemonic):
    t=direct_target(raw,site,mnemonic)
    if t is not None:return t
    # Short count-register branches, no prefix variants or far transfers.
    if len(raw)==2 and raw[0] in (0xe0,0xe1,0xe2,0xe3):
        aliases={0xe0:('loopne','loopnz'),0xe1:('loope','loopz'),0xe2:('loop',),0xe3:('jrcxz',)}
        if mnemonic in aliases[raw[0]]:
            return site+2+int.from_bytes(raw[1:],'little',signed=True)
    return None


def indirect_kind(raw,mnemonic,operands):
    """Validate ordinary FF /2 or /4 form and addressing length, not target."""
    i=1 if raw and 0x40<=raw[0]<=0x4f else 0
    if len(raw)<i+2 or raw[i]!=0xff:return None
    mr=raw[i+1]; op=(mr>>3)&7; mod=mr>>6; rm=mr&7
    if op not in (2,4) or mnemonic!=('call' if op==2 else 'jmp'):return None
    n=i+2
    if mod==3:
        if n!=len(raw) or '[' in operands:return None
        regs=('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi')+tuple('r%d'%n for n in range(8,16))
        rex=raw[0] if i else 0
        return 'indirect_register' if operands.strip().lower()==regs[rm+8*bool(rex&1)] else None
    if rm==4:
        if n>=len(raw):return None
        sib=raw[n];n+=1
        if mod==0 and sib&7==5:n+=4
    elif mod==0 and rm==5:n+=4
    n+={0:0,1:1,2:4}[mod]
    if n!=len(raw) or '[' not in operands or ']' not in operands:return None
    return 'indirect_memory'


def target_agrees(row):
    x=row.instruction
    t=relative(row.raw,x.address,x.mnemonic)
    m=re.match(r'^0x([0-9a-fA-F]+)(?:\s|$)',x.operands)
    return t if t is not None and m and int(m[1],16)==t else None


def boundary_kind(target,maps):
    """Describe existing raw decoder spans; never re-decode at a conflict."""
    kinds=[]
    for rows in maps:
        if target in rows:kinds.append('start');continue
        keys=sorted(rows); j=bisect_right(keys,target)-1
        if j>=0 and target<keys[j]+len(rows[keys[j]].raw):kinds.append('interior')
        else:kinds.append('uncovered')
    return '/'.join(kinds)


def triage(left,right,raw_maps,raw,va):
    """Reproduce previous denominator, classify old gaps, retain uncertainty."""
    guards,baseline=entry_guards(left,right,raw,va); end=va+len(raw)
    ss=[{x.address:x for x in s if va<=x.address<end} for s in (left,right)]
    nxt=[{a:b for a,b in zip(sorted(s),sorted(s)[1:])} for s in ss]
    gaps=Counter(); conflicts=Counter(); additions=set(); recovered=Counter()
    for site in sorted(ss[0].keys()|ss[1].keys()):
        a,b=(s.get(site) for s in ss)
        if not any(x and (x.mnemonic in ('call','jmp') or x.mnemonic.startswith(('j','loop'))) for x in (a,b)):continue
        old_target=None
        if a and b and site in nxt[0] and site in nxt[1] and nxt[0][site]==nxt[1][site]:
            chunk=raw[site-va:nxt[0][site]-va]
            ts=[]
            for x in (a,b):
                t=direct_target(chunk,site,x.mnemonic); m=re.match(r'^0x([0-9a-fA-F]+)(?:\s|$)',x.operands)
                ts.append(t if t is not None and m and int(m[1],16)==t else None)
            if ts[0] is not None and ts[0]==ts[1]:old_target=ts[0]
        if old_target is not None:
            if va<=old_target<end and (old_target not in ss[0] or old_target not in ss[1]):
                conflicts[boundary_kind(old_target,raw_maps)]+=1
            continue
        ra,rb=(m.get(site) for m in raw_maps)
        if not ra or not rb or ra.raw!=rb.raw:
            gaps['raw_span_unreconciled']+=1;continue
        ta,tb=target_agrees(ra),target_agrees(rb)
        if ta is not None and ta==tb:
            gaps['direct_byte_verified']+=1
            if not va<=ta<end:recovered['outside_window']+=1
            elif ta in ss[0] and ta in ss[1] and ta in raw_maps[0] and ta in raw_maps[1]:
                recovered['common_boundary']+=1;additions.add(ta)
            else:recovered['noncommon_boundary']+=1
            continue
        ia,ib=[indirect_kind(x.raw,x.instruction.mnemonic,x.instruction.operands) for x in (ra,rb)]
        gaps[ia if ia is not None and ia==ib else 'other_unresolved']+=1
    if sum(gaps.values())!=baseline.get('unresolved',0) or sum(conflicts.values())!=baseline.get('in_window_noncommon_boundary',0):
        raise ValueError('Prior denominator mismatch')
    return guards|additions, {'baseline':baseline,'unresolved_classification':dict(gaps),'prior_boundary_conflicts':dict(conflicts),'recovered_direct':dict(recovered),'added_unique_guards':len(additions-guards)}
