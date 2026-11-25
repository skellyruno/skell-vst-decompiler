"""Conservative cross-control evidence from repeated, exact-source sweeps."""
import re
import math
import numpy as np

MAX_STATE = 4 * 1024 * 1024
SHA = re.compile(r'[0-9a-f]{64}\Z')


def replicated_delta(a, b, c, d):
    """Only changes stable in both independent baseline and changed captures."""
    if any(not isinstance(x, bytes) or len(x) > MAX_STATE for x in (a,b,c,d)):
        raise ValueError('Invalid state bytes')
    lengths = [len(x) for x in (a,b,c,d)]
    if len(set(lengths)) != 1:
        return {'status':'VARIABLE_LENGTH','lengths':lengths}
    a,b,c,d = (np.frombuffer(x,dtype=np.uint8) for x in (a,b,c,d))
    unstable = (a != b) | (c != d)
    idx = np.flatnonzero(~unstable & (a != c))
    spans = []
    if idx.size:
        splits = np.flatnonzero(np.diff(idx) != 1)
        starts = np.r_[idx[0],idx[splits+1]]
        ends = np.r_[idx[splits]+1,idx[-1]+1]
        spans = [[int(lo),int(hi)] for lo,hi in zip(starts[:256],ends[:256])]
    return {'status':'CANDIDATE','length':len(a),'unstable_bytes':int(np.count_nonzero(unstable)),
            'stable_changed_bytes':int(idx.size),'spans':spans,
            'truncated':bool(idx.size and len(starts)>256)}


def summarize_map(reports):
    """Join repeated sweeps only when source, baseline controls/state/metrics agree.

    Exclusive offsets are exclusive only among controls in this experiment.
    Does not infer serialized data types, hidden DSP endpoints, or numeric IDs.
    """
    if not isinstance(reports,list) or not 1<=len(reports)<=32:
        raise ValueError('Choose 1..32 sweep reports')
    identity = None
    names = set()
    summary = []
    offsets = {}
    complete = True
    for report in reports:
        key = report['parameter']
        rows = report['rows']
        if not isinstance(key,str) or not key or key in names or not 4<=len(rows)<=32 or len(rows)%2:
            raise ValueError('Invalid repeated sweep')
        names.add(key)
        if not report.get('repeat_changed') or not report.get('repeat_metrics_stable'):
            raise ValueError('Replicated baseline required')
        a,b = rows[:2]
        def readback_matches(r):
            value,actual=r.get('value'),r.get('parameters',{}).get(key)
            return (type(value) in (int,float) and type(actual) in (int,float) and
                    math.isfinite(value) and math.isfinite(actual) and 0<=value<=1 and abs(actual-value)<=1e-5)
        def base(r):
            return tuple(r[k] for k in ('binary_sha256','host_module_sha256','version','state_sha256','parameters','metrics','reported_latency','sample_rate'))
        if any(r.get('status')!='captured' for r in (a,b)) or base(a)!=base(b) or not all(readback_matches(r) for r in (a,b)) or a['value']!=b['value']:
            raise ValueError('Baseline identity or state unstable')
        fingerprint = base(a)
        if any(not isinstance(x,str) or not SHA.fullmatch(x) for x in (fingerprint[0],fingerprint[1],fingerprint[3])):
            raise ValueError('Missing source/state fingerprint')
        if identity is None: identity=fingerprint
        elif identity!=fingerprint: raise ValueError('Sweeps need identical baseline and exact source')
        obs = []
        seen = set()
        for c,d in zip(rows[2::2],rows[3::2]):
            evidence=c.get('state_difference',{})
            valid=(c.get('status')==d.get('status')=='captured' and c.get('replicate_verified') is True
                   and c.get('value')==d.get('value') and c.get('value')!=a.get('value')
                   and c.get('value') not in seen and base(c)[:3]==base(d)[:3]==identity[:3]
                   and c.get('parameters')==d.get('parameters') and c.get('metrics')==d.get('metrics')
                   and c.get('reported_latency')==d.get('reported_latency')
                   and readback_matches(c) and readback_matches(d) and c['sample_rate']==d['sample_rate']==identity[-1]
                   and evidence.get('status')=='CANDIDATE' and not evidence.get('truncated'))
            seen.add(c.get('value'))
            if not valid:
                obs.append({'value':c.get('value'),'status':'UNRESOLVED'});complete=False;continue
            params=c['parameters']; baseline=a['parameters']
            other=sorted(k for k in params.keys()|baseline.keys() if k!=key and params.get(k)!=baseline.get(k))
            state=set()
            length=evidence.get('length'); spans=evidence.get('spans',[])
            if type(length) is not int or not 0<=length<=MAX_STATE or len(spans)>256:
                raise ValueError('Invalid state spans')
            # Cap the map output and memory even for broad state changes.
            if evidence.get('stable_changed_bytes',MAX_STATE)>65536:
                obs.append({'value':c.get('value'),'status':'UNRESOLVED','reason':'state change too broad'});complete=False;continue
            last=0
            for lo,hi in spans:
                if type(lo) is not int or type(hi) is not int or not last<=lo<hi<=length or hi-lo>65536 or len(state)+hi-lo>65536:
                    raise ValueError('Invalid state span')
                state.update(range(lo,hi));last=hi
            if len(state)!=evidence.get('stable_changed_bytes'):
                raise ValueError('State span count mismatch')
            audio=c['metrics']!=a['metrics']
            timing=c.get('reported_latency')!=a.get('reported_latency')
            status=('CONFOUNDED' if other else 'STATE_AND_AUDIO' if state and audio else
                    'STATE_ONLY' if state else 'AUDIO_ONLY' if audio else 'LATENCY_ONLY' if timing else 'NO_OBSERVED_CHANGE')
            if other: complete=False
            else:
                combined=offsets.setdefault(key,set())
                if len(combined|state)>65536:
                    raise ValueError('Per-control state map exceeds limit')
                combined.update(state)
            obs.append({'value':c['value'],'status':status,'state_spans':spans,'audio_changed':audio,
                        'reported_latency_changed':timing,'other_changed_controls':other})
        summary.append({'parameter':key,'observations':obs})
    # Compare only controls with successfully isolated perturbations.
    for entry in summary:
        key=entry['parameter']; here=offsets.get(key,set())
        shared=set().union(*(v for k,v in offsets.items() if k!=key))
        entry['observed_state_byte_count']=len(here)
        entry['shared_state_byte_count']=len(here & shared)
        entry['unshared_observed_byte_count']=len(here-shared)
    return {'binary_sha256':identity[0],'host_module_sha256':identity[1],'version':identity[2],
            'sample_rate':identity[-1],'complete_comparison':complete,'controls':summary,
            'note':'Repeated public-control observations; exclusivity only among tested isolated settings. No raw state or inferred DSP addresses.'}
