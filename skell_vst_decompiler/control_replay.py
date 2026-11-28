"""Compare repeated public-control observations without assuming internal topology."""
import math
import re
from pathlib import Path
import json
import soundfile as sf
from .extended_probes import digest
import numpy as np

SHA = re.compile(r'[a-f0-9]{64}\Z')


def compare(rows, control, *, atol=1e-6, rtol=1e-4):
    """Rows: (metadata, aligned stereo array), baseline twice, changed twice.

    No time shift or gain fitting. A stable effect is evidence only for these
    settings and stimulus, never an internal parameter/address mapping.
    """
    if len(rows)!=4 or not isinstance(control,str) or not control or not math.isfinite(atol) or not math.isfinite(rtol) or not 0<atol<=.001 or not 0<rtol<=.01:
        raise ValueError('invalid replay settings')
    a,b,c,d=(m for m,_ in rows)
    fields=('binary_sha256','host_module_sha256','source_sha256','plugin','version','target_stage','sample_rate','frames','block_size','host','offset_samples','alignment_status','backend','reported_latency_samples','reset')
    identity=tuple(a[k] for k in fields)
    if any(tuple(m[k] for k in fields)!=identity for m in (b,c,d)):
        raise ValueError('replay identity, alignment or reported latency mismatch')
    if any(not isinstance(a[k],str) or not SHA.fullmatch(a[k]) for k in fields[:3]):
        raise ValueError('missing exact identity')
    if a['backend']!='installed_vst3' or a['reset'] is not True or type(a['frames']) is not int or not 1<=a['frames']<=5760000:
        raise ValueError('invalid capture metadata')
    if type(a['sample_rate']) is not int or not 8000<=a['sample_rate']<=192000 or a['offset_samples']!=0:
        raise ValueError('unsupported rate or alignment')
    params=[m['parameter_readback'] for m,_ in rows]
    keys=set(params[0])
    if control not in keys or not 1<=len(keys)<=2048 or any(set(p)!=keys or any(type(v) not in (float,int) or not math.isfinite(v) or not 0<=v<=1 for v in p.values()) for p in params):
        raise ValueError('invalid normalized controls')
    if params[0]!=params[1] or params[2]!=params[3]:raise ValueError('unstable control readback')
    others=sorted(k for k in keys if k!=control and params[0][k]!=params[2][k])
    if params[0][control]==params[2][control]:raise ValueError('control was not changed')
    signals=[np.asarray(x,float) for _,x in rows]
    if any(x.shape!=(a['frames'],2) or not np.isfinite(x).all() or np.max(abs(x))>64 for x in signals):raise ValueError('invalid samples')
    rms=lambda x:float(np.sqrt(np.mean(x*x)))
    base,repeat,changed,changed_repeat=signals
    floor=max(atol,rtol*max(rms(base),rms(changed)))
    noise=max(rms(base-repeat),rms(changed-changed_repeat))
    effect=min(rms(x-y) for x in (base,repeat) for y in (changed,changed_repeat))
    status='CONFOUNDED' if others else 'UNSTABLE' if noise>floor else 'STABLE_EFFECT' if effect>max(5*noise,5*floor) else 'NO_RESOLVED_EFFECT'
    return {'status':status,'control':control,'baseline':params[0][control],'changed':params[2][control],'other_changed_controls':others,'repeat_rms_error':noise,'minimum_effect_rms':effect,'resolution_floor':floor,'note':'One declared stimulus and setting pair; metadata must be independently verified against actual render files. No internal DSP or whole-plugin coverage claim.'}


def compare_files(source, folders, control, **kwargs):
    """Verify the source and four actual render files before comparison."""
    if len(folders)!=4 or len({Path(p).resolve() for p in folders})!=4:
        raise ValueError('four distinct capture folders required')
    source=Path(source); source_sha=digest(source); info=sf.info(source)
    if info.channels!=2 or not 1<=info.frames<=5760000:raise ValueError('invalid source')
    rows=[]
    for folder in map(Path,folders):
        meta=json.loads((folder/'metadata.json').read_text()); wet=folder/'render.wav'
        expected=meta['render_sha256']; actual=digest(wet)
        if expected!=actual or meta['source_sha256']!=source_sha:raise ValueError('capture hash mismatch')
        wi=sf.info(wet)
        if (wi.samplerate,wi.channels,wi.frames)!=(info.samplerate,2,info.frames) or meta['sample_rate']!=info.samplerate or meta['frames']!=info.frames:
            raise ValueError('capture format mismatch')
        x,_=sf.read(wet,always_2d=True)
        if digest(wet)!=actual:raise ValueError('render changed during read')
        rows.append((meta,x))
    if digest(source)!=source_sha:raise ValueError('source changed during read')
    return compare(rows,control,**kwargs)
