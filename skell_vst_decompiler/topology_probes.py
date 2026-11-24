"""Independent signal probes for stereo linkage, frequency response and coloration.

Analyze only explicitly aligned authorized renders. No target execution.
"""
import numpy as np


def stereo_cases(fs=48000):
    if type(fs) is not int or not 8000<=fs<=192000:
        raise ValueError('Invalid sample rate')
    t=np.arange(fs)/fs
    x=.2*np.sin(2*np.pi*200*t)
    q=.2*np.cos(2*np.pi*200*t)
    return {'in_phase':np.column_stack((x,x)),
            'opposite':np.column_stack((x,-x)),
            'quadrature':np.column_stack((x,q)),
            'left_only':np.column_stack((x,np.zeros_like(x))),
            'asymmetric':np.column_stack((x,.25*x))}


def topology_levels(samples):
    x=np.asarray(samples,dtype=float)
    if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.all(np.isfinite(x)):
        raise ValueError('Expected finite stereo samples')
    return {'pre_detection_mean_rms':float(np.sqrt(np.mean(np.mean(x,axis=1)**2))),
            'channel_power_rms':float(np.sqrt(np.mean(x*x))),
            'max_channel_rms':float(np.max(np.sqrt(np.mean(x*x,axis=0))))}


def harmonic_levels(samples,fs,f0,orders=5):
    """Coherent single-tone projection; does not measure intermodulation or all noise."""
    x=np.asarray(samples,dtype=float)
    if (x.ndim!=1 or not len(x) or not np.all(np.isfinite(x)) or
        not np.isfinite(fs) or fs<=0 or not np.isfinite(f0) or f0<=0 or
        type(orders) is not int or not 2<=orders<=20 or orders*f0>=fs/2):
        raise ValueError('Invalid harmonic measurement')
    cycles=len(x)*f0/fs
    if abs(cycles-round(cycles))>1e-8 or cycles<1:
        raise ValueError('Require a coherent integer-cycle window')
    phase=2*np.pi*f0*np.arange(len(x))/fs
    rms=[]
    for k in range(1,orders+1):
        a=2*np.mean(x*np.cos(k*phase)); b=2*np.mean(x*np.sin(k*phase))
        rms.append(float(np.hypot(a,b)/np.sqrt(2)))
    if rms[0]<1e-12:raise ValueError('Fundamental below measurement floor')
    return {'fundamental_rms':rms[0],
            'relative_harmonics_db':[float(20*np.log10(max(v/rms[0],1e-15))) for v in rms[1:]],
            'selected_thd_ratio':float(np.linalg.norm(rms[1:])/rms[0])}
