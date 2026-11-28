import sys
import numpy as np
from scipy.signal import fftconvolve
from skell_vst_decompiler.finite_stereo import probes,measure
fs=96000;x,z,tail=probes(fs,12,4096);h=np.zeros((fs*10+18,2,2));h[0,0,0]=.5;h[-1,1,0]=.15;h[fs,0,1]=-.2;h[0,1,1]=.5

def render(v):
    out=np.zeros_like(v)
    for o in range(2):
        for i in range(2):out[:,o]+=fftconvolve(v[:,i],h[:,o,i])[:len(v)]
    return out

y=np.stack([render(v) for v in x]);hy=np.stack([render(v) for v in z]);r=measure(x,y,y[0],z,hy,fs,tail);print(r['status'],r['holdout_relative'],r['routes']);assert r['status']=='CONSISTENT_FINITE_OBSERVATION';assert r['routes'][2]['peak_sample']==fs*10+17
