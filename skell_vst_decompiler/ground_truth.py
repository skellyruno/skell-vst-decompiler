"""Bounded, label-blind static fingerprints; candidates, never semantic proof."""
from collections import Counter
import math
from .pe import PE
from .disasm import disassemble


def fingerprint(path, tool='objdump'):
    pe=PE(path)
    text=pe.section('.text')
    if text is None or not 0<text.virtual_size<=32768 or text.virtual_size>text.file_size:
        raise ValueError('Choose a bounded executable fixture; not a whole large plugin')
    counts=Counter()
    for ins in disassemble(pe,text.rva,text.virtual_size,tool):
        op=ins.mnemonic.removeprefix('v')
        if op.startswith('nop') or op in ('int3','ret'):continue
        if op.startswith(('mul','add','sub','div','min','max','sqrt','cmp','comi','ucomi')) and ('ss' in op or 'sd' in op or 'ps' in op or 'pd' in op):
            counts[op]+=1
        elif op.startswith('j') or op.startswith('cmov'):counts['branch']+=1
        elif op.startswith('cvt'):counts['convert']+=1
        elif op in ('and','andps','andpd','xorps','orps'):counts['bitwise']+=1
        elif op=='movss' and '[' in ins.operands:counts['scalar_memory']+=1
    return {'sha256':pe.sha256,'features':dict(counts),'scope_bytes':text.virtual_size}


def rank(features, labeled, min_margin=.08):
    """Training labels are supplied explicitly; target names/hashes are not features."""
    if not labeled:raise ValueError('Empty training corpus')
    def distance(a,b):
        keys=a.keys()|b.keys()
        total=sum(abs(a.get(k,0)-b.get(k,0)) for k in keys)
        return total/max(1,sum(a.values())+sum(b.values()))
    scores={}
    for label,ref in labeled:
        d=distance(features,ref)
        scores[label]=min(d,scores.get(label,math.inf))
    ordered=sorted(scores.items(),key=lambda x:(x[1],x[0]))
    margin=ordered[1][1]-ordered[0][1] if len(ordered)>1 else 0
    chosen=ordered[0][0] if sum(features.values()) and ordered[0][1]<=.45 and margin>=min_margin else None
    return {'candidate':chosen,'ranking':ordered,'margin':margin,'status':'CANDIDATE' if chosen else 'UNRESOLVED'}


def evaluate(predictions, truth):
    if not truth or set(predictions)!=set(truth):raise ValueError('Evaluation requires exact case IDs')
    correct=sum(predictions[k]==v for k,v in truth.items() if predictions[k] is not None)
    attempted=sum(v is not None for v in predictions.values())
    unknown_correct=sum(v is None and predictions[k] is None for k,v in truth.items())
    known=sum(v is not None for v in truth.values())
    return {'cases':len(truth),'known_cases':known,'correct_known':correct,'attempted':attempted,
            'incorrect':attempted-correct,'abstained':len(truth)-attempted,'unknown_correct':unknown_correct,
            'known_recall':correct/known if known else None,'precision':correct/attempted if attempted else None}
