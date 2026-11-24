"""Independent offline two-period similarity reference.

Historical context: US5973252A (1999), publicly disclosed energy and
correlation test. This is an original frame-based experiment, not the
patent's complete tracking/resynthesis system or an Evo implementation.
"""
import math
import numpy as np


def period_error(samples, lag):
    if type(lag) is not int or lag<1:
        raise ValueError('Positive integer lag required')
    x=np.asarray(samples,dtype=np.float64)
    if x.ndim!=1 or len(x)<2*lag or not np.all(np.isfinite(x)):
        raise ValueError('Expected two finite periods')
    a,b=x[-2*lag:-lag],x[-lag:]
    energy=float(np.dot(a,a)+np.dot(b,b))
    if energy<=1e-20:
        return 1.
    diff=a-b
    return float(np.dot(diff,diff)/energy)


def estimate(samples, fs, low=70., high=1000., threshold=.12):
    if not all(math.isfinite(v) for v in (fs,low,high,threshold)) or not 8000<=fs<=192000 or not 30<=low<high<=fs/4 or not 0<threshold<1:
        raise ValueError('Invalid detector settings')
    x=np.asarray(samples,dtype=np.float64)
    if x.ndim!=1 or len(x)>65536 or not np.all(np.isfinite(x)) or np.max(np.abs(x),initial=0)>64:
        raise ValueError('Expected bounded finite mono frame')
    first=max(2,math.ceil(fs/high));last=math.floor(fs/low)
    if len(x)<2*(last+1):
        raise ValueError('Frame too short')
    x=x-np.mean(x)
    if np.sqrt(np.mean(x*x))<1e-5:
        return None,0.
    errors=np.ones(last+2)
    for lag in range(first-1,last+2):
        a,b=x[-2*lag:-lag],x[-lag:]
        energy=float(np.dot(a,a)+np.dot(b,b))
        if energy>1e-20:
            diff=a-b
            errors[lag]=np.dot(diff,diff)/energy
    for lag in range(first,last+1):
        a,b,c=errors[lag-1:lag+2]
        if b<threshold and b<=a and b<=c:
            denom=a-2*b+c
            shift=float(np.clip(.5*(a-c)/denom,-.5,.5)) if denom>0 else 0.
            hz=fs/(lag+shift)
            if low<=hz<=high:
                return hz,float(np.clip(1-b,0.,1.))
    return None,0.
