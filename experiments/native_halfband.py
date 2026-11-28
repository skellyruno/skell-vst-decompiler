"""Original causal experiment and independent dense filter oracle."""
import ctypes
from pathlib import Path
import numpy as np
from scipy.signal import upfirdn
from .staged_color import design

LATENCY=336


def coefficients(taps,edge):
    h=design(taps,edge).copy();h=.5*(h+h[::-1]);m=taps//2
    h[::2]=0.;h[m]=.5
    return h


def load_native(path):
    lib=ctypes.CDLL(str(Path(path).resolve()));fn=lib.halfband_color
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');fn.argtypes=[ptr,ptr,ctypes.c_uint,ptr,ptr,ctypes.c_double,ctypes.c_int];fn.restype=ctypes.c_int
    a=np.ascontiguousarray(coefficients(641,.49)[1::2]);b=np.ascontiguousarray(coefficients(65,.3)[1::2])
    def process(x,drive=4.,symmetric=True):
        x=np.ascontiguousarray(x,dtype=np.float64)
        if x.ndim!=1 or not 1<=len(x)<=3840000:raise ValueError('invalid input')
        y=np.empty_like(x)
        if fn(x,y,len(x),a,b,drive,int(symmetric))!=1:raise ValueError('native rejected input')
        return y
    return process


def causal_oracle(x,drive=4.):
    x=np.asarray(x,float);a=coefficients(641,.49);b=coefficients(65,.3)
    u=upfirdn(2*a,x,up=2)[:2*len(x)];v=upfirdn(2*b,u,up=2)[:4*len(x)]
    w=upfirdn(b,np.tanh(drive*v),down=2)[:2*len(x)]
    return upfirdn(a,w,down=2)[:len(x)]
