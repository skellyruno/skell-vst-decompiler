"""Finite alias diagnostics on coherent tones; does not identify internal oversampling factor."""
import numpy as np
from scipy.signal import resample_poly, firwin


def color(x, factor, drive=4., span=10):
    x=np.asarray(x,float)
    if x.ndim!=1 or not 64<=len(x)<=384000 or not np.isfinite(x).all() or factor not in (1,2,4,8,16) or not .1<=drive<=20 or type(span)!=int or span not in (10,40,100,200):raise ValueError('invalid input')
    if factor==1:return np.tanh(drive*x)
    h=firwin(2*span*factor+1,1/factor,window=('kaiser',8.6))
    return resample_poly(np.tanh(drive*resample_poly(x,factor,1,window=h)),1,factor,window=h)


def signature(y,fs,hz):
    y=np.asarray(y,float)
    if y.ndim!=1 or len(y)!=fs or not np.isfinite(y).all() or not 20<=hz<fs/2 or int(hz)!=hz:raise ValueError('one coherent second required')
    spec=np.abs(np.fft.rfft(y)/len(y))**2;weights=np.full(len(spec),2.);weights[0]=1
    if len(y)%2==0:weights[-1]=1
    mask=np.ones(len(spec),bool);mask[0]=False
    for h in range(int((fs/2-1)//hz)+1):
        i=int(h*hz);mask[max(0,i-1):i+2]=False
    # Energy outside integer harmonic bins includes aliases, noise and modulation, not uniquely alias.
    total=float(np.sum(weights*spec));other=float(np.sum(weights[mask]*spec[mask]))
    return dict(nonharmonic_db=float(10*np.log10(max(other/max(total,1e-30),1e-30))),fundamental_peak=float(2*np.sqrt(spec[int(hz)])))
