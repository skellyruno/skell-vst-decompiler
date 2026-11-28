"""Original offline two-stage FIR design experiment. No causal latency guarantee."""
from functools import lru_cache
import numpy as np
from scipy.signal import remez, resample_poly, freqz


@lru_cache(maxsize=12)
def design(taps, edge):
    if taps not in (321,481,641,65) or not .2<=edge<.5:raise ValueError('unsupported design')
    h=remez(taps,[0,edge,1-edge,1],[1,0],fs=2,maxiter=100,grid_density=32)
    if not np.isfinite(h).all():raise ValueError('invalid coefficients')
    h.setflags(write=False)
    return h


def staged(x, taps=641, edge=.49, drive=4.):
    x=np.asarray(x,float)
    if x.ndim!=1 or not 64<=len(x)<=384000 or not np.isfinite(x).all() or not .1<=drive<=20:raise ValueError('invalid signal')
    a=design(taps,edge);b=design(65,.3)
    u=resample_poly(resample_poly(x,2,1,window=a),2,1,window=b)
    return resample_poly(resample_poly(np.tanh(drive*u),1,2,window=b),1,2,window=a)


def response(taps, edge):
    h=design(taps,edge);f,v=freqz(h,worN=131072,fs=2);p=abs(v[f<=edge]);s=abs(v[f>=1-edge]);return dict(taps=taps,edge=edge,pass_ripple_db=float(20*np.log10(p.max()/p.min())),stop_max_db=float(20*np.log10(s.max())))
