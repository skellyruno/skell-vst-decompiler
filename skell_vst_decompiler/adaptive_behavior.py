"""Independent offline behavioral models. No vendor loading or source reconstruction."""
import numpy as np
from scipy.optimize import least_squares


def envelope_features(x,y,fs,block_ms=5):
    """Aligned stereo input/output; scalar block projection, not an internal gain trace."""
    x,y=np.asarray(x,float),np.asarray(y,float)
    if type(fs)!=int or not 8000<=fs<=192000 or x.shape!=y.shape or x.ndim!=2 or x.shape[1]!=2 or not np.isfinite(x).all() or not np.isfinite(y).all() or not 1<=block_ms<=20:
        raise ValueError('invalid observation')
    n=round(fs*block_ms/1000); k=len(x)//n
    if not 1<=k<=100000:raise ValueError('invalid duration')
    a,b=(v[:k*n].reshape(k,n,2) for v in (x,y))
    power=np.sum(a*a,axis=(1,2)); ok=power>1e-8
    g=np.divide(np.sum(a*b,axis=(1,2)),power,out=np.ones(k),where=ok)
    ok &= g>1e-6
    return {'peak':np.max(abs(a),axis=(1,2)),'gain_db':20*np.log10(np.maximum(g,1e-6)),'valid':ok,'dt':n/fs}


def predict(peak,dt,p,kind):
    """Block-rate descriptions: one envelope, dual envelope, adaptive release.
    This is not a production sample-rate processor. Initial state is silence.
    """
    peak=np.asarray(peak,float); p=np.asarray(p,float)
    if kind not in ('single','dual','adaptive') or p.shape!=({'single':(4,), 'dual':(6,), 'adaptive':(7,)}[kind]) or not np.isfinite(p).all() or not np.isfinite(peak).all() or peak.ndim!=1 or np.any(peak<0) or not 0<dt<=.02 or not (-80<=p[0]<=0 and 0<=p[1]<=1 and np.all(p[2:4]>0)):
        raise ValueError('invalid model')
    if kind!='single' and (p[4]<=0 or not 0<=p[5]<=1):raise ValueError('invalid slow release or mix')
    if kind=='adaptive' and not 0<=p[6]<=4:raise ValueError('invalid depth dependence')
    target=np.maximum(0,20*np.log10(np.maximum(peak,1e-12))-p[0])*p[1]
    a=np.exp(-dt/p[2]);r=np.exp(-dt/p[3]);slow_r=np.exp(-dt/p[4]) if kind!='single' else r
    fast=slow=0.;out=np.empty(len(peak))
    for i,v in enumerate(target):
        rr=a if v>fast else r
        fast=v+rr*(fast-v)
        if kind=='single':out[i]=-fast;continue
        sr=a if v>slow else (np.exp(-dt/(p[4]*(1+p[6]*slow/20))) if kind=='adaptive' else slow_r)
        slow=v+sr*(slow-v);out[i]=-((1-p[5])*fast+p[5]*slow)
    return out


def fit_envelopes(train,holdout):
    """Train exclusively on supplied training sequences, score separately supplied holdouts.
    Dataset identity/disjointness is the caller's responsibility. No gain fitting on holdout.
    """
    if not 1<=len(train)<=32 or not 1<=len(holdout)<=32:raise ValueError('invalid sequence count')
    def residual(rows,p,kind):
        return np.concatenate([(predict(r['peak'],r['dt'],p,kind)-r['gain_db'])[r['valid']] for r in rows])
    out=[]
    for kind in ('single','dual','adaptive'):
        p=[-24,.7,.005,.15];lo=[-60,0,.0005,.005];hi=[-1,1,.2,2.]
        if kind!='single':p += [.3,.3];lo += [.02,0];hi += [4.,1.]
        if kind=='adaptive':p += [.5];lo += [0];hi += [4.]
        fit=least_squares(lambda p:residual(train,p,kind),p,bounds=(lo,hi),max_nfev=100)
        if not fit.success:raise RuntimeError('fit failed')
        rmse=lambda a:float(np.sqrt(np.mean(a*a)))
        out.append({'model':kind,'parameters':fit.x.tolist(),'train_rmse_db':rmse(residual(train,fit.x,kind)),'holdout_rmse_db':rmse(residual(holdout,fit.x,kind)),'holdout_per_sequence_db':[rmse(residual([r],fit.x,kind)) for r in holdout]})
    return out


def bandlimited_tone(fs,hz,phase,seconds=1):
    """Three coherent harmonics, all strictly below Nyquist. Fixed amplitudes, varied phase."""
    if type(fs)!=int or not 8000<=fs<=192000 or type(hz)!=int or not 20<=hz or 3*hz>=fs/2 or not np.isfinite(phase) or type(seconds)!=int or not 1<=seconds<=4:raise ValueError('invalid spectral grid')
    t=np.arange(fs*seconds)/fs; w=2*np.pi*hz*t
    return np.sin(w)+.6*np.sin(2*w+phase)+.35*np.sin(3*w-phase)


def isolated_echoes(y,fs,threshold=1e-5,min_gap_ms=5):
    """Find local peak per contiguous group of above-threshold samples; signed amplitude.
    Designed for isolated impulse echoes, not dense reverb or arbitrary music.
    """
    y=np.asarray(y,float)
    if y.ndim!=1 or not 1<=len(y)<=30*fs or not np.isfinite(y).all() or not 8000<=fs<=192000 or not 0<threshold<1 or not 0<min_gap_ms<=100:raise ValueError('invalid echo observation')
    idx=np.flatnonzero(abs(y)>threshold); gap=max(1,round(fs*min_gap_ms/1000)); groups=np.split(idx,np.flatnonzero(np.diff(idx)>gap)+1)
    out=[]
    for g in groups:
        if len(g):
            i=int(g[np.argmax(abs(y[g]))]);out.append({'sample':i,'seconds':i/fs,'signed_peak':float(y[i])})
    return out
