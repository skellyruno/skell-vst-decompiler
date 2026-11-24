"""Offline monophonic F0 reference using public YIN-style difference math.
Independent implementation, not an Evo decoder or a pitch shifter.
"""
import math
import numpy as np


def estimate(samples, fs, low=70., high=1000., threshold=.12):
    if not all(math.isfinite(v) for v in (fs,low,high,threshold)) or not 8000<=fs<=192000 or not 30<=low<high<=fs/4 or not 0<threshold<1:
        raise ValueError('Invalid pitch settings')
    x=np.asarray(samples,dtype=np.float64)
    if x.ndim!=1 or len(x)>65536 or not np.all(np.isfinite(x)):
        raise ValueError('Expected bounded finite mono frame')
    first=max(2,math.ceil(fs/high)); last=math.floor(fs/low)
    if len(x)<2*last+2:
        raise ValueError('Frame too short for requested low frequency')
    x=x-np.mean(x)
    if np.sqrt(np.mean(x*x))<1e-5:
        return None,0.
    width=len(x)-last-1
    ref=x[:width]
    d=np.zeros(last+2)
    for lag in range(1,last+2):
        delta=ref-x[lag:lag+width]
        d[lag]=np.dot(delta,delta)
    cumulative=np.cumsum(d[1:]); norm=np.ones_like(d)
    np.divide(d[1:]*np.arange(1,last+2),cumulative,out=norm[1:],where=cumulative>0)
    for lag in range(first,last+1):
        if norm[lag]<threshold and norm[lag]<=norm[lag-1] and norm[lag]<=norm[lag+1]:
            a,b,c=norm[lag-1:lag+2]; denom=a-2*b+c
            offset=float(np.clip(.5*(a-c)/denom,-.5,.5)) if denom>0 else 0.
            frequency=fs/(lag+offset)
            if low<=frequency<=high:
                return frequency,float(np.clip(1-b,0,1))
    return None,0.
