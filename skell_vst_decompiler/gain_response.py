"""Measure gain behavior from explicitly sample-aligned offline audio arrays.

No target loading or plugin execution. Caller must establish matching source,
settings, sample rate and delay compensation; this cannot infer alignment.
"""
import math
import numpy as np


def gain_blocks(dry,wet,fs,block_ms=10.,floor_db=-70.):
    if not all(math.isfinite(v) for v in (fs,block_ms,floor_db)) or not 8000<=fs<=384000 or not .1<=block_ms<=1000 or not -140<=floor_db<=-20:
        raise ValueError('Invalid measurement settings')
    a,b=(np.asarray(x,dtype=np.float64) for x in (dry,wet))
    if a.ndim not in (1,2) or a.shape!=b.shape or not a.size or a.ndim==2 and a.shape[1] not in (1,2):
        raise ValueError('Matching mono/stereo sample arrays required')
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or max(np.max(np.abs(a)),np.max(np.abs(b)))>64:
        raise ValueError('Expected bounded finite samples')
    n=max(1,round(fs*block_ms/1000))
    floor=10**(floor_db/20)
    rows=[]
    for start in range(0,len(a)-n+1,n):
        x,y=a[start:start+n],b[start:start+n]
        rms=float(np.sqrt(np.mean(x*x)))
        out=float(np.sqrt(np.mean(y*y)))
        if rms<floor:
            continue
        # Least-squares scalar gain, not a model of a nonlinear processor.
        scalar=float(np.sum(x*y)/np.sum(x*x))
        residual=float(np.sqrt(np.mean((y-scalar*x)**2)))
        rows.append({'time_ms':1000*start/fs,'input_rms_db':20*math.log10(rms),
                     'output_rms_db':20*math.log10(max(out,1e-15)),
                     'rms_gain_db':20*math.log10(max(out,1e-15)/rms),
                     'scalar_gain':scalar,'residual_relative_rms':residual/rms})
    return rows


def fit_relaxation(times_ms,values,steady):
    """Fit a one-pole relaxation of a measured scalar control, not a vendor law.

    Return a descriptive time constant only if the signed distance from
    steady state retains its sign and decays; residual error is reported.
    """
    t,y=np.asarray(times_ms,dtype=float),np.asarray(values,dtype=float)
    if t.ndim!=1 or t.shape!=y.shape or len(t)<4 or not math.isfinite(steady) or not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)) or np.any(np.diff(t)<=0):
        raise ValueError('Invalid relaxation series')
    d=y-steady
    if abs(d[0])<1e-12 or np.any(d*d[0]<=0):
        return None
    slope,intercept=np.polyfit(t-t[0],np.log(np.abs(d)),1)
    if slope>=0:
        return None
    predicted=steady+np.sign(d[0])*np.exp(intercept+slope*(t-t[0]))
    rmse=float(np.sqrt(np.mean((predicted-y)**2)))
    return {'tau_ms':float(-1/slope),'rmse':rmse,'samples':len(t),
            'note':'Single-exponential descriptive fit; not an inferred implementation.'}
