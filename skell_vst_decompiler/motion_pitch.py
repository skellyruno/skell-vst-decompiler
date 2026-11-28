"""Original slow-motion-aware causal frame-domain pitch research; not a vendor model or audio engine."""
import math
import numpy as np


def estimate(cents, hop_ms=10., measurement_sd=3., step_cents=80.):
    """Compare vibrato hypotheses with slow-motion and linear-trend hypotheses.

    Slow oscillator components are retained as intentional pitch movement.
    The frequency bands and evidence threshold are heuristic.

    Return center, estimated vibrato, supported rate (NaN if unsupported),
    and a soft support weight. NaN observations reset all states. No future
    samples or audio synthesis; evidence thresholds are heuristic.
    """
    y=np.asarray(cents,float)
    if (y.ndim!=1 or not 0<len(y)<=100000 or np.any(np.isinf(y)) or
        np.any(np.abs(y[np.isfinite(y)])>20000) or
        not all(math.isfinite(v) for v in (hop_ms,measurement_sd,step_cents)) or
        not 1<=hop_ms<=50 or not 0<measurement_sd<=50 or not 30<=step_cents<=300):
        raise ValueError('Invalid trajectory')
    dt=hop_ms/1000.;freq=np.r_[0.,np.arange(.75,2.51,.25),np.arange(3.,8.01,.25)];n=len(freq);cut=int(np.searchsorted(freq,3.))
    F=np.repeat(np.eye(4)[None,:,:],n,axis=0);F[:,0,1]=dt
    c,s=np.cos(2*np.pi*freq*dt),np.sin(2*np.pi*freq*dt)
    F[:,2,2]=F[:,3,3]=c;F[:,2,3]=s;F[:,3,2]=-s
    H=np.array([1.,0.,1.,0.]);Q=np.repeat(np.diag([.015,4.,.2,.2])[None,:,:],n,axis=0)*(hop_ms/10.)
    Q[0,2:,2:]=0
    P0=np.repeat(np.diag([100.,100.,400.,400.])[None,:,:],n,axis=0);P0[0,2:,2:]=0
    R=measurement_sd**2;I=np.eye(4);forget=np.exp(-dt/.35)
    center=np.full(len(y),np.nan);vib=center.copy();rate=center.copy();support=np.zeros(len(y));x=None
    age=0.;blend=0.;mix=1.
    for i,z in enumerate(y):
        if np.isnan(z):x=None;continue
        if x is not None:
            x=(F@x[:,:,None])[:,:,0];P=F@P@F.transpose(0,2,1)+Q
        if x is None or abs(z-last_weights@(x@H))>step_cents:
            x=np.tile([z,0.,0.,0.],(n,1));P=P0.copy()
            loss=np.zeros(n);age=0.;blend=0.;mix=1.
        PH=P@H;variance=PH@H+R;innovation=z-x@H
        loss=forget*loss+.5*(innovation**2/variance+np.log(variance))
        vloss=loss[cut:];w=np.exp(-(vloss-vloss.min()));w/=w.sum()
        tloss=loss[:cut];u=np.exp(-(tloss-tloss.min()));u/=u.sum()
        K=PH/variance[:,None];x+=K*innovation[:,None]
        A=I-K[:,:,None]*H[None,None,:];P=A@P@A.transpose(0,2,1)+R*K[:,:,None]*K[:,None,:]
        # Compare against a simple trend; penalize selection among many oscillators.
        advantage=tloss.min()-vloss.min()-math.log(n-cut)
        amplitude=float(w@np.hypot(x[cut:,2],x[cut:,3]))
        strength=float(np.clip((advantage-.5)/2.,0.,1.)*np.clip((amplitude-.6*measurement_sd)/max(.6*measurement_sd,1.),0.,1.))
        if age<.10:strength=0.
        blend+=(-math.expm1(-dt/.025))*(strength-blend)
        # Provisional center during startup; no frequency declaration yet.
        # Smoothly hand off to the supported model over 100 ms.
        provisional=max(0.,min(1.,(.20-age)/.10))
        mix=provisional+(1-provisional)*blend
        last_weights=np.r_[(1-mix)*u,mix*w]
        center[i]=(1-mix)*(u@(x[:cut,0]+x[:cut,2]))+mix*(w@x[cut:,0]);vib[i]=mix*(w@x[cut:,2]);support[i]=blend
        if blend>=.5:rate[i]=w@freq[cut:]
        age+=dt
    return center,vib,rate,support
