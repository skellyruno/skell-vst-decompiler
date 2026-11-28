"""Independent offline research; not a vendor algorithm or real-time engine."""
import math
import numpy as np


def adaptive_pitch(cents, hop_ms=10., measurement_sd=3., step_cents=80.):
    """Causal oscillator bank with exponentially forgotten innovation scores.

    Returns pitch center, vibrato, and weighted frequency; frequency is a
    model diagnostic, not a reliable estimate when vibrato is absent.
    """
    y=np.asarray(cents,float)
    if (y.ndim!=1 or not 0<len(y)<=100000 or np.any(np.isinf(y)) or
        not all(math.isfinite(v) for v in (hop_ms,measurement_sd,step_cents)) or
        not 1<=hop_ms<=50 or not 0<measurement_sd<=50 or not 30<=step_cents<=300):
        raise ValueError('Invalid trajectory')
    dt=hop_ms/1000.;freq=np.arange(3.,8.01,.5);n=len(freq)
    F=np.repeat(np.eye(4)[None,:,:],n,axis=0);F[:,0,1]=dt
    c,s=np.cos(2*np.pi*freq*dt),np.sin(2*np.pi*freq*dt)
    F[:,2,2]=F[:,3,3]=c;F[:,2,3]=s;F[:,3,2]=-s
    H=np.array([1.,0.,1.,0.]);Q=np.diag([.015,4.,.2,.2])*(hop_ms/10.)
    R=measurement_sd**2;I=np.eye(4);forget=np.exp(-dt/.35)
    center=np.full(len(y),np.nan);vib=center.copy();rate=center.copy();x=None
    for i,z in enumerate(y):
        if np.isnan(z):x=None;continue
        if x is not None:
            x=(F@x[:,:,None])[:,:,0];P=F@P@F.transpose(0,2,1)+Q
        if x is None or abs(z-weights@(x@H))>step_cents:
            x=np.tile([z,0.,0.,0.],(n,1));P=np.repeat(np.diag([100.,100.,400.,400.])[None,:,:],n,axis=0)
            loss=np.zeros(n);weights=np.full(n,1/n)
        PH=P@H;variance=PH@H+R;innovation=z-x@H
        loss=forget*loss+.5*(innovation**2/variance+np.log(variance))
        weights=np.exp(-(loss-loss.min()));weights/=weights.sum()
        K=PH/variance[:,None];x+=K*innovation[:,None]
        A=I-K[:,:,None]*H[None,None,:];P=A@P@A.transpose(0,2,1)+R*K[:,:,None]*K[:,None,:]
        center[i]=weights@x[:,0];vib[i]=weights@x[:,2];rate[i]=weights@freq
    return center,vib,rate


def assess_recovery(models, noise_sd):
    """Conservative descriptive preference, not inference of internal DSP states.

    Require meaningful held-out improvement, separated time constants and
    meaningful amplitudes. The noise estimate must be supplied independently.
    """
    if not math.isfinite(noise_sd) or noise_sd<=0:
        raise ValueError('Positive noise estimate required')
    single,dual=models['1'],models['2']
    a=np.asarray(dual['amplitudes'],float);tau=np.asarray(dual['tau_ms'],float)
    e1,e2=single['heldout_rmse'],dual['heldout_rmse']
    if (a.shape!=(2,) or tau.shape!=(2,) or not np.all(np.isfinite(a)) or not np.all(np.isfinite(tau)) or np.any(a<0) or np.any(tau<=0) or not all(math.isfinite(v) and v>=0 for v in (e1,e2))):
        raise ValueError('Invalid model summary')
    dual_supported=(e1-e2>max(2*noise_sd,.2*e1) and
                    max(tau)/min(tau)>=2 and min(a)>max(3*noise_sd,.05*a.sum()))
    return 'dual_descriptive_preferred' if dual_supported else 'dual_not_established'
