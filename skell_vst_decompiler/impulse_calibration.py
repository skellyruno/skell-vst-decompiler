"""Explicit impulse-output timing diagnostic; never removes creative delay."""
import numpy as np


def inspect_impulse(source, wet, fs, *, threshold=1e-7, reported_latency=None):
    """One nonzero source sample, two channels, no inferred alignment.

    Returns first/peak arrival and echo peaks, not proof of transport latency.
    """
    x,y=np.asarray(source,float),np.asarray(wet,float)
    if type(fs) is not int or not 8000<=fs<=192000 or x.ndim!=2 or x.shape!=y.shape or x.shape[1]!=2 or not 64<=len(x)<=20*fs:
        raise ValueError('Invalid aligned stereo impulse pair')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.max(abs(x))>1 or np.max(abs(y))>64 or not np.isfinite(threshold) or not 0<threshold<=.01:
        raise ValueError('Invalid signal or threshold')
    if reported_latency is not None and (type(reported_latency) is not int or not 0<=reported_latency<=2*fs):raise ValueError('Invalid reported latency')
    locations=np.argwhere(x!=0)
    if len(locations)!=1:raise ValueError('Exactly one input impulse required')
    origin,ch=map(int,locations[0]);amplitude=x[origin,ch]
    if abs(amplitude)<.01:raise ValueError('Impulse too small')
    outputs=[]
    for c in range(2):
        h=y[:,c]/amplitude;mag=abs(h);active=np.flatnonzero(mag>threshold)
        # Local maxima only, including endpoints; capped reporting, not a tail fit.
        prev=np.r_[0.,mag[:-1]];nxt=np.r_[mag[1:],0.]
        peaks=np.flatnonzero((mag>threshold)&(mag>=prev)&(mag>nxt))
        peak=int(np.argmax(mag)) if len(active) else None
        outputs.append({'channel':c,'first_arrival_samples':int(active[0])-origin if len(active) else None,'peak_arrival_samples':peak-origin if peak is not None else None,'pre_input_peak':float(np.max(mag[:origin])) if origin else 0.,'peak_gain':float(h[peak]) if peak is not None else None,'echo_peaks':[{'offset_samples':int(i)-origin,'gain':float(h[i])} for i in peaks[:16]],'peak_count':len(peaks)})
    return {'sample_rate':fs,'frames':len(x),'source_channel':ch,'source_index':origin,'reported_latency_samples':reported_latency,'outputs':outputs,'note':'Observed host-output timing only; creative delay, compensation, and transport latency are distinct. No alignment applied.'}
