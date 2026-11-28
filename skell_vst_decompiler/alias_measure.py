"""Coherent periodic tone diagnostics for original offline saturation references."""
import math
import numpy as np


def measure(samples,fs,f0):
    """Normalize non-harmonic power and in-band harmonic power to fundamental.

    Includes noise and folded components outside the expected harmonic bins;
    aliases coinciding with a legitimate harmonic bin are not distinguishable.
    DC is excluded. Require a coherent periodic steady-state signal.
    """
    x=np.asarray(samples,float)
    if (x.ndim!=1 or not 16<=len(x)<=2000000 or not np.all(np.isfinite(x)) or
        not all(math.isfinite(v) for v in (fs,f0)) or not 0<f0<fs/2):
        raise ValueError('Invalid coherent tone')
    cycles=len(x)*f0/fs
    if cycles<1 or abs(cycles-round(cycles))>1e-8:
        raise ValueError('Integer-cycle tone required')
    k=round(cycles);n=len(x);spec=np.fft.rfft(x)/n
    power=2*np.abs(spec)**2;power[0]=0.
    if n%2==0:power[-1]*=.5
    harmonic=np.arange(k,len(power),k)
    fundamental=float(power[k])
    if fundamental<1e-24:raise ValueError('Fundamental below floor')
    non=power.copy();non[harmonic]=0.
    ratio=float(non.sum()/fundamental)
    distortion=float(power[harmonic[1:]].sum()/fundamental)
    return {'fundamental_rms':math.sqrt(fundamental),
            'nonharmonic_db':10*math.log10(max(ratio,1e-30)),
            'harmonic_distortion_db':10*math.log10(max(distortion,1e-30)),
            'dc':float(spec[0].real)}
