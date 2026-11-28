"""Independent offline model selection. No plugin loading or topology uniqueness claim."""
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.optimize import least_squares

MODELS = {'wet': 3, 'parallel': 4, 'split': 5}


def predict(x, fs, kind, p):
    x, p = np.asarray(x, float), np.asarray(p, float)
    if kind not in MODELS or p.shape != (MODELS[kind],) or not np.isfinite(p).all() or x.ndim != 1 or not 1 <= len(x) <= 768000 or not np.isfinite(x).all() or not 8000 <= fs <= 192000:
        raise ValueError('invalid input')
    if not 100 < p[0] < .49*fs or not .1 <= p[1] <= 40:
        raise ValueError('invalid cutoff or drive')
    lo = sosfilt(butter(1, p[0], fs=fs, output='sos'), x)
    wet = np.tanh(p[1]*lo)*p[2]
    if kind == 'wet': return wet
    if kind == 'parallel': return wet+p[3]*x
    if not .1 <= p[3] <= 40: raise ValueError('invalid high drive')
    return wet + p[4]*np.tanh(p[3]*(x-lo))


def select(train, validation, threshold=1e-4):
    """Joint fit at known rates, validation uses full waveform, no alignment fit."""
    if not train or not validation or not 0 < threshold <= .01:
        raise ValueError('invalid selection')
    for a in train:
        for b in validation:
            if a[2] == b[2] and np.array_equal(a[0], b[0]): raise ValueError('duplicate observation')
    ceiling = min(12000., .45*min(r[2] for r in train+validation))
    reports=[]
    def residual(rows, kind, p):
        out=[]
        for x,y,fs in rows:
            if np.shape(x)!=np.shape(y) or not np.isfinite(y).all() or np.linalg.norm(y)<1e-9: raise ValueError('invalid target')
            out.append((predict(x,fs,kind,p)-y)/np.sqrt(np.mean(y*y)))
        return np.concatenate(out)
    for kind in MODELS:
        lo=[101.,.101,-2.];hi=[ceiling,39.,2.]
        if kind=='parallel':lo+=[-2.];hi+=[2.]
        if kind=='split':lo+=[.101,-2.];hi+=[39.,2.]
        starts=[]
        for cut,d in ((1300.,2.),(4500.,6.)):
            p=[cut,d,.4]+([.4] if kind=='parallel' else [2.,.4] if kind=='split' else [])
            starts.append(np.clip(p,np.array(lo)+1e-6,np.array(hi)-1e-6))
        fits=[least_squares(lambda p:residual(train,kind,p),p,bounds=(lo,hi),x_scale='jac',max_nfev=100) for p in starts]
        ok=[f for f in fits if f.success]
        if not ok: reports.append(dict(kind=kind,converged=False,validation=None));continue
        best=min(ok,key=lambda f:f.cost)
        reports.append(dict(kind=kind,converged=True,parameters=best.x.tolist(),validation=float(np.sqrt(np.mean(residual(validation,kind,best.x)**2))),evaluations=sum(f.nfev for f in fits)))
    passing=[r for r in reports if r['converged'] and r['validation']<=threshold]
    return dict(candidates=reports,selected=min(passing,key=lambda r:(MODELS[r['kind']],r['validation'])) if passing else None)


def delayed(x, delay, gain, drive, kind):
    """Original finite delayed recurrence. Return wet echo only, zero initial state."""
    x=np.asarray(x,float)
    if x.ndim!=1 or not 1<=len(x)<=768000 or not np.isfinite(x).all() or type(delay)!=int or not 1<=delay<=len(x) or not 0<=gain<.95 or not .1<=drive<=10 or kind not in ('linear','inside','outside'):
        raise ValueError('invalid delay description')
    w=np.zeros_like(x)
    for i in range(delay,len(x),delay):
        m=min(delay,len(x)-i); u=x[i-delay:i-delay+m];v=w[i-delay:i-delay+m]
        w[i:i+m]=u+gain*(np.tanh(drive*v)/drive if kind=='inside' else v)
    return np.tanh(drive*w)/drive if kind=='outside' else w


def fit_echo(impulse, train, validation, threshold=1e-4):
    """First nonzero arrival constrains delay; fit candidate recurrence on training."""
    q=np.asarray(impulse,float)
    if q.ndim!=1 or not np.isfinite(q).all() or np.max(abs(q))<1e-8:raise ValueError('missing impulse response')
    ix=np.flatnonzero(abs(q)>np.max(abs(q))*1e-5)
    if not len(ix) or ix[0]<1:raise ValueError('no isolated wet delay')
    d=int(ix[0]); reports=[]
    def error(rows,k,p):
        return np.concatenate([(delayed(x,d,p[0],p[1] if len(p)>1 else 1.,k)-y)/max(np.sqrt(np.mean(y*y)),1e-12) for x,y in rows])
    for k in ('linear','inside','outside'):
        lo=[0.] if k=='linear' else [0.,.1];hi=[.949] if k=='linear' else [.949,10.]
        f=least_squares(lambda p:error(train,k,p),[.5] if k=='linear' else [.5,2.],bounds=(lo,hi),max_nfev=80)
        reports.append(dict(kind=k,parameters=f.x.tolist(),converged=bool(f.success),validation=float(np.sqrt(np.mean(error(validation,k,f.x)**2)))))
    ok=[r for r in reports if r['converged'] and r['validation']<=threshold]
    return dict(delay=d,candidates=reports,selected=min(ok,key=lambda r:(len(r['parameters']),r['validation'])) if ok else None)
