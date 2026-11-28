"""Independent offline clock hypothesis and fractional delay observations."""
import ctypes
from pathlib import Path
import numpy as np


def load_clock(path):
    lib=ctypes.CDLL(str(Path(path).resolve()))
    fn=lib.phase_clock
    fn.argtypes=[np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS'),ctypes.c_uint,ctypes.c_double,ctypes.c_float,ctypes.c_float,ctypes.c_float,ctypes.c_int]
    fn.restype=ctypes.c_int
    def clock(n,fs,center,depth,rate,single):
        if type(n)!=int or not 1<=n<=3840000:raise ValueError('invalid length')
        d=np.empty(n,np.float32)
        if fn(d,n,fs,center,depth,rate,int(single))!=1:raise ValueError('invalid clock')
        return d
    return clock


def interpolate(x, delay):
    x,d=np.asarray(x,float),np.asarray(delay,float)
    if x.ndim!=1 or x.shape!=d.shape or not np.isfinite(x).all() or not np.isfinite(d).all() or np.any(d<0):raise ValueError('invalid fractional delay')
    pos=np.arange(len(x))-d;i=np.floor(pos).astype(np.int64);u=pos-i
    def at(k):return np.where((k>=0)&(k<len(x)),x[np.clip(k,0,len(x)-1)],0.)
    return (1-u)*at(i)+u*at(i+1)


def infer_delay(x,y,guess,radius=12):
    """Fit per-sample linear interpolation using multiple independent reset captures.
    Only known wet gain unity; candidate search localized by an initial clock.
    Returns delay and per-sample residual; a low residual does not prove uniqueness.
    """
    x,y=np.asarray(x,float),np.asarray(y,float);g=np.asarray(guess,float)
    if x.ndim!=2 or x.shape!=y.shape or not 4<=len(x)<=16 or not 32<=x.shape[1]<=384000 or g.shape!=(x.shape[1],) or not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(g).all() or type(radius)!=int or not 1<=radius<=32 or np.any(g<0):raise ValueError('invalid observations')
    n=x.shape[1];t=np.arange(n);i=np.floor(t-g).astype(np.int64);best=np.full(n,np.inf);pos=np.zeros(n)
    for k in range(-radius,radius+1):
        j=i+k;a=x[:,np.clip(j,0,n-1)];b=x[:,np.clip(j+1,0,n-1)]-a
        frac=np.clip(np.sum((y-a)*b,axis=0)/np.maximum(np.sum(b*b,axis=0),1e-18),0,1)
        err=np.mean((a+b*frac-y)**2,axis=0);err[(j<0)|(j+1>=n)]=np.inf
        choose=err<best;best[choose]=err[choose];pos[choose]=j[choose]+frac[choose]
    return t-pos,np.sqrt(best)
