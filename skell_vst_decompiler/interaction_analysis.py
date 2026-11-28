"""Bounded offline behavioral analysis of aligned, repeated audio observations.

No plugin loading, fitting, alignment, or claim of internal implementation.
Array callers are responsible for verifying source and render provenance.
"""
import math
import numpy as np


def _limits(atol, rtol):
    if not math.isfinite(atol) or not math.isfinite(rtol) or not 0 < atol <= .001 or not 0 < rtol <= .01:
        raise ValueError('invalid measurement floor')


def _audio(x):
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or not 1 <= len(a) <= 5760000 or not np.isfinite(a).all() or np.max(np.abs(a)) > 64:
        raise ValueError('invalid stereo samples')
    return a


def _rms(x):
    return float(np.sqrt(np.mean(x*x)))


def _pairs(cells, keys):
    if not isinstance(cells, dict) or set(cells) != set(keys):
        raise ValueError('missing or unexpected condition')
    out = {}
    shape = None
    for key in keys:
        pair = cells[key]
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise ValueError('two independent repeats required')
        a, b = map(_audio, pair)
        if shape is None: shape = a.shape
        if a.shape != shape or b.shape != shape:
            raise ValueError('unaligned condition')
        out[key] = (a, b)
    return out


def factorial(cells, *, atol=1e-6, rtol=1e-4):
    """Two controls, two levels each; paired repeats for all four cells.

    The 11 observation is withheld from the three-cell additive predictor.
    Interaction is a waveform residual, not proof of nonlinear internals.
    A cascade of linear filters can also produce control interaction.
    """
    _limits(atol, rtol)
    cells = _pairs(cells, ('00', '10', '01', '11'))
    a, b, c, d = (cells[k][0] for k in ('00', '10', '01', '11'))
    floor = max(atol, rtol * max(_rms(x) for pair in cells.values() for x in pair))
    repeat = max(_rms(x-y) for x,y in cells.values())
    # Independent replicate residuals, not a fit to the joint observation.
    residuals = [cells['11'][i] - (cells['10'][i]+cells['01'][i]-cells['00'][i]) for i in range(2)]
    magnitude = min(map(_rms, residuals))
    residual_repeat = _rms(residuals[0]-residuals[1])
    gate = 5*max(floor, 4*repeat)
    status = 'UNSTABLE' if repeat > floor else 'INTERACTION' if magnitude > gate and residual_repeat <= 4*floor else 'NO_RESOLVED_INTERACTION'
    denom = _rms(d)
    return {'status':status, 'frames':len(a), 'repeat_rms':repeat, 'resolution_rms':floor,
            'interaction_gate_rms':gate, 'interaction_rms':magnitude,
            'interaction_repeat_rms':residual_repeat,
            'additive_relative_error':_rms(residuals[0])/denom if denom > floor else None,
            'main_a_rms':_rms(b-a), 'main_b_rms':_rms(c-a),
            'conditional_a_rms':_rms(d-c), 'conditional_b_rms':_rms(d-b),
            'note':'Only these four settings and this stimulus; repeat noise is not a confidence interval.'}


def history(dry_a, dry_b, cells, fs, prefix_frames, *, block_ms=20, atol=1e-6, rtol=1e-4):
    """Different histories, identical exact input suffix; measure state persistence.

    Report the last detected window, not an inferred internal release constant.
    A differing suffix invalidates the experiment. No offset correction.
    """
    _limits(atol, rtol)
    a,b=map(_audio,(dry_a,dry_b))
    if type(fs) is not int or not 8000 <= fs <= 192000 or type(prefix_frames) is not int or not 1 <= prefix_frames < len(a) or a.shape != b.shape or not math.isfinite(block_ms) or not 1 <= block_ms <= 1000:
        raise ValueError('invalid history geometry')
    if not np.array_equal(a[prefix_frames:],b[prefix_frames:]) or np.array_equal(a[:prefix_frames],b[:prefix_frames]):
        raise ValueError('require differing prefix and identical suffix')
    cells=_pairs(cells,('a','b'))
    if cells['a'][0].shape != a.shape: raise ValueError('unaligned dry/wet')
    x,y=cells['a']; z,w=cells['b']; block=max(1,round(fs*block_ms/1000))
    rows=[]
    for lo in range(prefix_frames,len(a),block):
        hi=min(lo+block,len(a)); p,q,r,s=(v[lo:hi] for v in (x,y,z,w))
        floor=max(atol,rtol*max(map(_rms,(p,q,r,s))))
        noise=max(_rms(p-q),_rms(r-s)); effect=min(_rms(i-j) for i in (p,q) for j in (r,s))
        status='UNSTABLE' if noise>floor else 'DETECTED' if effect>5*max(floor,noise) else 'UNRESOLVED'
        rows.append({'start_ms':(lo-prefix_frames)*1000/fs,'end_ms':(hi-prefix_frames)*1000/fs,'status':status,'effect_rms':effect,'repeat_rms':noise})
    found=[r for r in rows if r['status']=='DETECTED']
    return {'status':'UNSTABLE' if any(r['status']=='UNSTABLE' for r in rows) else 'HISTORY_DETECTED' if found else 'NO_RESOLVED_HISTORY',
            'last_detected_end_ms':found[-1]['end_ms'] if found else None,
            'right_censored':rows[-1]['status']=='DETECTED','windows':rows,
            'note':'Observed state persistence only; tail, latency, phase, and modulation can contribute.'}


def factorial_files(source, folders, controls, **kwargs):
    """Eight verified host-capture folders; exactly two isolated control axes.

    File integrity and declared metadata are checked, not authenticated host origin.
    A latency-changing control is rejected, not automatically realigned.
    """
    import json
    import re
    from pathlib import Path
    import soundfile as sf
    from .extended_probes import digest
    keys=('00','10','01','11')
    if not isinstance(folders,dict) or set(folders)!=set(keys) or len(controls)!=2 or len(set(controls))!=2 or any(not isinstance(k,str) or not k for k in controls):
        raise ValueError('invalid factorial plan')
    if any(len(folders[k])!=2 for k in keys):raise ValueError('two folders per cell required')
    paths=[Path(p).resolve() for k in keys for p in folders[k]]
    if len(set(paths))!=8:raise ValueError('capture folders must be distinct')
    source=Path(source); sha=digest(source); info=sf.info(source)
    if info.channels!=2 or not 1<=info.frames<=5760000 or not 8000<=info.samplerate<=192000:raise ValueError('invalid source')
    identity=None; cells={}; values={}
    fields=('binary_sha256','host_module_sha256','plugin','version','target_stage','host','block_size','offset_samples','alignment_status','backend','reported_latency_samples','reset','source_sha256','sample_rate','frames')
    for cell in keys:
        signals=[]; params=[]
        for folder in map(Path,folders[cell]):
            meta_path=folder/'metadata.json'; raw=meta_path.read_bytes(); m=json.loads(raw)
            ident=tuple(m[k] for k in fields)
            if identity is None:identity=ident
            elif identity!=ident:raise ValueError('capture identity mismatch')
            if any(not isinstance(m[k],str) or not re.fullmatch('[0-9a-f]{64}',m[k]) for k in fields[:2]) or m['source_sha256']!=sha or m['backend']!='installed_vst3' or m['reset'] is not True or m['offset_samples']!=0 or m['sample_rate']!=info.samplerate or m['frames']!=info.frames:raise ValueError('invalid capture identity')
            p=m['parameter_readback']
            if not isinstance(p,dict) or not 1<=len(p)<=2048 or any(k not in p for k in controls) or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in p.values()):raise ValueError('invalid readback')
            wet=folder/'render.wav'; expected=m['render_sha256']; wi=sf.info(wet)
            if digest(wet)!=expected or (wi.samplerate,wi.channels,wi.frames)!=(info.samplerate,2,info.frames):raise ValueError('render hash or format mismatch')
            x,_=sf.read(wet,always_2d=True)
            if digest(wet)!=expected or meta_path.read_bytes()!=raw:raise ValueError('capture changed during read')
            signals.append(x);params.append(p)
        if params[0]!=params[1]:raise ValueError('replicate readback mismatch')
        cells[cell]=signals;values[cell]=params[0]
    base=values['00']; a,b=controls
    if values['10'][a]==base[a] or values['01'][b]==base[b]:raise ValueError('control levels must differ')
    for k,p in values.items():
        expected=dict(base);expected[a]=values['10'][a] if k[0]=='1' else base[a];expected[b]=values['01'][b] if k[1]=='1' else base[b]
        if p!=expected:raise ValueError('confounded or inconsistent factorial settings')
    if digest(source)!=sha:raise ValueError('source changed during read')
    result=factorial(cells,**kwargs)
    result.update({'controls':list(controls),'levels':{a:[base[a],values['10'][a]],b:[base[b],values['01'][b]]},'source_sha256':sha,'binary_sha256':identity[0],'host_module_sha256':identity[1]})
    return result
