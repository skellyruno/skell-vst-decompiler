"""Independent periodic offline coloration comparisons; not a streaming processor."""
import math
import numpy as np
from scipy.signal import resample_poly
from .saturation_reference import saturate


def oversampled(samples, drive=4., factor=4):
    """Periodic, zero-phase polyphase reference; never use as real-time DSP."""
    x=np.asarray(samples,dtype=float)
    if x.ndim!=1 or not 16<=len(x)<=192000 or not np.all(np.isfinite(x)) or np.max(np.abs(x))>16 or type(factor) is not int or factor not in (2,4,8):
        raise ValueError('Invalid periodic input')
    high=resample_poly(x,factor,1,window=('kaiser',8.),padtype='wrap')
    wet=saturate(high,drive,antialias=False)
    return resample_poly(wet,1,factor,window=('kaiser',8.),padtype='wrap')


def compare(samples, reference, fs, f0):
    """Compare raw and fundamental-gain/phase-matched waveform errors.

    Fundamental phase estimates a constant delay modulo a tone period; this
    is not general alignment or a plugin latency measurement. Report raw
    error too, so matching cannot hide frequency-response changes.
    """
    x,y=(np.asarray(a,dtype=float) for a in (samples,reference))
    if x.ndim!=1 or x.shape!=y.shape or not 16<=len(x)<=192000 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or not all(math.isfinite(v) for v in (fs,f0)) or not 0<f0<fs/2:
        raise ValueError('Invalid periodic comparison')
    n=len(x);cycles=n*f0/fs;k=round(cycles)
    if k<1 or abs(cycles-k)>1e-8:raise ValueError('Coherent tone required')
    X,Y=np.fft.rfft(x),np.fft.rfft(y)
    if min(abs(X[k]),abs(Y[k]))<1e-9:raise ValueError('Fundamental below floor')
    phase=float(np.angle(X[k]/Y[k]));gain=float(abs(Y[k])/abs(X[k]))
    shift=phase*n/(2*np.pi*k)
    # Real Nyquist coefficient cannot represent an arbitrary fractional shift.
    # Preserve raw comparison; omit that bin from the matched comparison only.
    X*=gain*np.exp(-2j*np.pi*np.arange(len(X))*shift/n)
    if n%2==0:X[-1]=Y[-1]=0.
    aligned=np.fft.irfft(X,n);target=np.fft.irfft(Y,n)
    def error(a,b):return float(20*np.log10(max(np.linalg.norm(a-b)/np.linalg.norm(b),1e-15)))
    return {'raw_error_db':error(x,y),'matched_error_db':error(aligned,target),
            'fundamental_gain_to_reference_db':20*math.log10(gain),
            'fundamental_phase_deg':math.degrees(phase),
            'phase_equivalent_shift_samples':shift}
