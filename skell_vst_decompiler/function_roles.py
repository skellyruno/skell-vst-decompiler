"""Conservative local code-role evidence, never an algorithm or utility proof."""
import re
from collections import Counter

FP = re.compile(r'(?:v)?(?:add|sub|mul|div|min|max|sqrt|fmadd\d*|fmsub\d*)(?:ss|sd|ps|pd)$')
VEC = re.compile(r'\b(?:xmm|ymm|zmm)\d+\b',re.I)
MEM = re.compile(r'\[([^\]]+)\]')
STACK = re.compile(r'\b(?:rsp|rbp|rip)\b',re.I)
TARGET = re.compile(r'^(?:0x)?([0-9a-f]+)(?:\s|$)',re.I)


def role_evidence(instructions):
    """Count bounded local observations; RBP is conservatively excluded as stack.

    No reaching definitions, alias or loop membership is established. A non-stack
    store may be a state update, graphics, or ordinary numerical computation.
    """
    c=Counter()
    if not instructions:return {'role':'UNRESOLVED','features':{}}
    lo,hi=instructions[0].address,instructions[-1].address
    for ins in instructions:
        op=ins.mnemonic.lower()
        args=ins.operands.split('#',1)[0].lower().strip()
        operands=args.split(',')
        c['instructions']+=1
        if FP.fullmatch(op):c['fp_arithmetic']+=1
        if op=='call':c['calls']+=1
        if op.startswith('j'):
            m=TARGET.match(args)
            if m and lo<=int(m[1],16)<ins.address<=hi:c['back_edges']+=1
        for i,operand in enumerate(operands):
            m=MEM.search(operand)
            if not m or STACK.search(m[1]):continue
            if VEC.search(args):
                c['vector_memory']+=1
                if i==0 and op.startswith(('mov','vmov')) and len(operands)==2:
                    c['nonstack_vector_stores']+=1
                    if '*' in m[1]:c['indexed_vector_stores']+=1
                elif i>0:c['nonstack_vector_reads']+=1
            elif 'byte ptr' in operand and 'dword ptr' not in operand:
                c['byte_memory']+=1
    # Preserve the distinction between computation and a sample-buffer loop.
    if c['fp_arithmetic']>=2 and c['back_edges'] and c['nonstack_vector_stores'] and c['nonstack_vector_reads']:
        role='PROCESSING_CANDIDATE'
    elif not c['fp_arithmetic'] and not c['vector_memory'] and c['byte_memory'] and c['back_edges']:
        role='BYTE_PROCESSING_CANDIDATE'
    else:role='UNRESOLVED'
    return {'role':role,'features':dict(c)}


def annotate(pe, candidates, tool='objdump'):
    """Add scoped evidence without changing legacy candidate rank/status."""
    from .disasm import disassemble
    import hashlib
    if len(candidates)>128:raise ValueError('Too many candidate regions')
    out=[]
    for row in candidates:
        lo,hi=int(row['start_rva'],16),int(row['end_rva_exclusive'],16)
        if not 1<=hi-lo<=8192:raise ValueError('Invalid candidate range')
        raw=pe.at_rva(lo,hi-lo,executable=True)
        if hashlib.sha256(raw).hexdigest()!=row['region_sha256']:raise ValueError('Candidate fingerprint mismatch')
        out.append({**row,'local_role_evidence':role_evidence(disassemble(pe,lo,hi-lo,tool))})
    return out
