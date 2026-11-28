"""Independent offline DSP diagnostics. No vendor implementation or audio synthesis."""
import math
import numpy as np
from scipy.optimize import least_squares


def split_pitch(cents, hop_ms=10., vibrato_hz=5., *, measurement_sd=3., step_cents=80.):
    """Causal linear state estimator: pitch center, slope, oscillator pair.

    Fixed oscillator frequency; abrupt innovations reset the state. NaN marks
    unvoiced. Returns center and vibrato estimates, not audio output.
    """
    y=np.asarray(cents,dtype=float)
    if y.ndim!=1 or not 0<len(y)<=100000 or np.any(np.isinf(y)) or not all(math.isfinite(v) for v in (hop_ms,vibrato_hz,measurement_sd,step_cents)) or not 1<=hop_ms<=50 or not 2<=vibrato_hz<=9 or not 0<measurement_sd<=50 or not 30<=step_cents<=300:
        raise ValueError('Invalid pitch trajectory')
    dt=hop_ms/1000.; angle=2*np.pi*vibrato_hz*dt
    c,s=np.cos(angle),np.sin(angle)
    F=np.array([[1,dt,0,0],[0,1,0,0],[0,0,c,s],[0,0,-s,c]])
    H=np.array([1.,0.,1.,0.]); I=np.eye(4)
    Q=np.diag([.015,4.,.2,.2])*(hop_ms/10.)
    R=measurement_sd**2
    center=np.full(len(y),np.nan);vib=center.copy();state=None
    for i,z in enumerate(y):
        if np.isnan(z):state=None;continue
        if state is not None:
            state=F@state;P=F@P@F.T+Q
        if state is None or abs(z-H@state)>step_cents:
            state=np.array([z,0.,0.,0.]);P=np.diag([100.,100.,400.,400.])
        K=P@H/(H@P@H+R)
        state+=K*(z-H@state)
        A=I-np.outer(K,H);P=A@P@A.T+R*np.outer(K,K)
        center[i],vib[i]=state[0],state[2]
    return center,vib


def recovery_continuous(times_ms,reduction,steady=0.):
    """Train on early 65%, compare held-out prediction for off-grid recovery."""
    t,y=np.asarray(times_ms,float),np.asarray(reduction,float)
    if t.ndim!=1 or t.shape!=y.shape or not 20<=len(t)<=10000 or not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)) or not np.isfinite(steady) or np.any(np.diff(t)<=0):
        raise ValueError('Invalid recovery series')
    t=t-t[0];y=y-steady;cut=int(.65*len(t))
    if y[0]<=0:raise ValueError('Positive initial reduction required')
    scale=y[0]
    def predict(p,tt,n):return np.exp(-tt[:,None]/np.exp(p[n:]))@p[:n]*scale
    result={}
    for n in (1,2):
        best=None
        for seed in ([80.],[300.],[1000.]) if n==1 else ([20.,200.],[50.,600.],[150.,1500.]):
            fit=least_squares(lambda p:(predict(p,t[:cut],n)-y[:cut])/scale,
                np.r_[np.full(n,1/n),np.log(seed)],bounds=(np.r_[np.zeros(n),np.full(n,np.log(5.))],np.r_[np.full(n,4.),np.full(n,np.log(3000.))]),max_nfev=300)
            if fit.success and (best is None or fit.cost<best.cost):best=fit
        if best is None:raise RuntimeError('Recovery optimizer did not converge')
        p=best.x; pred=predict(p,t,n);idx=np.argsort(p[n:]);result[str(n)]={'tau_ms':np.exp(p[n:])[idx].tolist(),'amplitudes':(scale*p[:n])[idx].tolist(),'train_rmse':float(np.sqrt(np.mean((pred[:cut]-y[:cut])**2))),'heldout_rmse':float(np.sqrt(np.mean((pred[cut:]-y[cut:])**2)))}
    return result


def two_tone_imd(samples,fs,f1=1700.,f2=2300.):
    """Coherent two-tone projection of difference/sum and third-order products."""
    x=np.asarray(samples,float)
    if x.ndim!=1 or not 0<len(x)<=1000000 or not np.all(np.isfinite(x)) or not all(math.isfinite(v) for v in (fs,f1,f2)) or not 0<f1<f2<2*f1 or 2*f2-f1>=fs/2 or f1+f2>=fs/2:raise ValueError('Invalid two-tone measurement')
    freqs=[f1,f2,f2-f1,f1+f2,2*f1-f2,2*f2-f1]
    if len(set(freqs))!=len(freqs) or any(abs(len(x)*f/fs-round(len(x)*f/fs))>1e-8 for f in freqs):raise ValueError('Distinct coherent bins required')
    t=np.arange(len(x))/fs
    amp=np.array([2*abs(np.mean(x*np.exp(-2j*np.pi*f*t))) for f in freqs]);ref=np.linalg.norm(amp[:2])
    if ref<1e-12:raise ValueError('Fundamentals below floor')
    return {'fundamental_peak_rss':float(ref),'imd2_db':float(20*np.log10(max(np.linalg.norm(amp[2:4])/ref,1e-15))),'imd3_db':float(20*np.log10(max(np.linalg.norm(amp[4:])/ref,1e-15)))}
