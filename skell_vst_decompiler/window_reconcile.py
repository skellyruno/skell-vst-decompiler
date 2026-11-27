"""Reconcile existing bounded evidence windows without decoding new targets."""
from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from .transfer_triage import target_agrees, indirect_kind


@dataclass(frozen=True)
class Window:
    start: int
    stop: int
    maps: tuple


def rex_w_indirect(a,b):
    """Recognize an ordinary FF /2 or /4 with redundant REX.W display.

    Both raw rows must match. Check the exact GNU prefix annotation and
    matching normalized operand text. No target address is inferred.
    """
    if not a or not b or a.raw!=b.raw or a.raw[:2]!=b'\x48\xff':return None
    for pref,plain in ((a,b),(b,a)):
        x,y=pref.instruction,plain.instruction
        m=re.fullmatch(r'W (call|jmp) (.+)',x.operands)
        if x.mnemonic!='rex.' or not m or y.mnemonic!=m[1]:continue
        normalize=lambda z:re.sub(r'\s+','',z.split('#',1)[0].lower())
        if normalize(m[2])!=normalize(y.operands):continue
        k=indirect_kind(a.raw,y.mnemonic,y.operands)
        if k:return k
    return None


def inspect(window):
    """Classify raw-row transfer observations; never resolve indirect targets."""
    a,b=window.maps
    out={}
    for site in sorted(a.keys()|b.keys()):
        x,y=a.get(site),b.get(site)
        if not any(r and (r.instruction.mnemonic in ('call','jmp') or r.instruction.mnemonic.startswith(('j','loop'))) for r in (x,y)):
            continue
        if not x or not y or x.raw!=y.raw:
            out[site]=('unreconciled',None);continue
        tx,ty=target_agrees(x),target_agrees(y)
        if tx is not None and tx==ty:
            out[site]=('direct',tx);continue
        k,l=[indirect_kind(r.raw,r.instruction.mnemonic,r.instruction.operands) for r in (x,y)]
        out[site]=(k if k is not None and k==l else rex_w_indirect(x,y) or 'unreconciled',None)
    return out


def reconcile_windows(windows):
    """Same-binary windows only. A disagreeing site never becomes a guard.

    Return per-window common-boundary guards and aggregate observation counts.
    Cross-window evidence is not a claim of complete control flow or execution.
    """
    windows=list(windows)
    if len(windows)>2048:raise ValueError('Too many bounded windows')
    for w in windows:
        if not 0<=w.start<w.stop or w.stop-w.start>32768 or len(w.maps)!=2:
            raise ValueError('Invalid window')
        for m in w.maps:
            if any(not w.start<=s<w.stop or s!=r.instruction.address or not 1<=len(r.raw)<=15 or s+len(r.raw)>w.stop for s,r in m.items()):
                raise ValueError('Invalid raw row')
            if any(s+len(m[s].raw)>t for s,t in zip(sorted(m),sorted(m)[1:])):
                raise ValueError('Overlapping raw rows')
    observations=[inspect(w) for w in windows]
    by_site=defaultdict(set); multiplicity=Counter(); counts=Counter()
    for obs in observations:
        for s,k in obs.items():by_site[s].add(k);multiplicity[s]+=1;counts['observation_'+k[0]]+=1
    accepted={s:next(iter(k))[1] for s,k in by_site.items() if len(k)==1 and next(iter(k))[0]=='direct'}
    # Reject propagation when an overlapping window covers a transfer site
    # but fails to report that exact transfer. Do not infer hidden code.
    accepted={s:t for s,t in accepted.items() if all(not w.start<=s<w.stop or obs.get(s)==('direct',t) for w,obs in zip(windows,observations))}
    for ks in by_site.values():
        counts['unique_'+(next(iter(ks))[0] if len(ks)==1 else 'disagreement')]+=1
    counts['repeated_observations']=sum(multiplicity.values())-len(by_site)
    counts['unique_sites']=len(by_site)
    # A destination must be a common raw start in the receiving window.
    guards=[]
    for w,obs in zip(windows,observations):
        local={t for s,t in accepted.items() if s in obs and t in w.maps[0] and t in w.maps[1]}
        all_guards={t for t in accepted.values() if w.start<=t<w.stop and t in w.maps[0] and t in w.maps[1]}
        guards.append(all_guards)
        counts['cross_window_guard_observations']+=len(all_guards-local)
        for s,(kind,t) in obs.items():
            if kind!='direct' or not w.start<=t<w.stop:continue
            if t in w.maps[0] and t in w.maps[1]:continue
            counts['raw_boundary_conflict_observations']+=1
            others=[v for v in windows if v is not w and v.start<=t<v.stop]
            common=any(t in v.maps[0] and t in v.maps[1] for v in others)
            counts['conflict_has_other_common_start' if common else 'conflict_no_other_common_start']+=1
    return guards,dict(counts)
