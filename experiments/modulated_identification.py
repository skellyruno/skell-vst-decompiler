"""Original bounded offline modulation descriptions, not unique circuit recovery."""
import numpy as np
from scipy.optimize import least_squares
from scipy.signal import correlate


def predict(x, fs, p, kind):
    x=np.asarray(x,float); p=np.asarray(p,float)
    if x.ndim!=1 or not 32<=len(x)<=768000 or not np.isfinite(x).all() or p.shape!=(5,) or not np.isfinite(p).all() or not 8000<=fs<=192000 or kind not in ('linear','cubic'):
        raise ValueError('invalid observation')
    center,depth,rate,phase,gain=p
    if not 0<=depth<center or center+depth>40 or center-depth<.1 or not .05<=rate<=5 or abs(gain)>2:raise ValueError('invalid delay schedule')
    t=np.arange(len(x)); pos=t-(center+depth*np.sin(2*np.pi*rate*t/fs+phase))*fs/1000
    i=np.floor(pos).astype(int); u=pos-i
    def at(k):return np.where((k>=0)&(k<len(x)),x[np.clip(k,0,len(x)-1)],0.)
    if kind=='linear':return gain*((1-u)*at(i)+u*at(i+1))
    return gain*(-u*(u-1)*(u-2)/6*at(i-1)+(u+1)*(u-1)*(u-2)/2*at(i)-(u+1)*u*(u-2)/2*at(i+1)+(u+1)*u*(u-1)/6*at(i+2))


def track(x,y,fs):
    """Coarse local cross-correlation; only for isolated wet, broadband excitation."""
    x,y=np.asarray(x,float),np.asarray(y,float)
    if x.shape!=y.shape or x.ndim!=1 or not np.isfinite(x).all() or not np.isfinite(y).all() or not 8000<=fs<=192000 or not fs//2<=len(x)<=768000:raise ValueError('invalid track input')
    width=round(fs*.005); lag=round(fs*.04); ts=[];ds=[]
    for start in range(lag,width*(len(x)//width-1),width*2):
        v=y[start:start+width]; a=x[start-lag:start+width]
        c=correlate(a,v,mode='valid',method='fft'); energy=np.sqrt(np.maximum(np.convolve(a*a,np.ones(width),mode='valid'),1e-18)*max(v@v,1e-18)); r=c/energy
        k=int(np.argmax(abs(r)))
        if abs(r[k])>.35:
            ts.append((start+width/2)/fs);ds.append((lag-k)*1000/fs)
    if len(ts)<20:raise ValueError('insufficient correlated windows')
    return np.asarray(ts),np.asarray(ds)


def select(train, validation, threshold=1e-3):
    x,y,fs=train; z,w,sr=validation
    if fs==sr and np.array_equal(x,z):raise ValueError('duplicate input')
    if not 0<threshold<=.05:raise ValueError('invalid threshold')
    t,d=track(x,y,fs); best=None
    for f in np.linspace(.1,4.5,89):
        a=np.column_stack([np.ones(len(t)),np.sin(2*np.pi*f*t),np.cos(2*np.pi*f*t)])
        c=np.linalg.lstsq(a,d,rcond=None)[0];cost=np.mean((a@c-d)**2)
        if best is None or cost<best[0]:best=(cost,f,c)
    _,f,c=best;depth=np.linalg.norm(c[1:]);phase=np.arctan2(c[2],c[1]);center=c[0]
    # Fit in coordinates center=depth+margin; bounded schedules are checked in predict.
    def unpack(q):return np.array([q[0]+q[1],q[1],q[2],q[3],q[4]])
    if not .2<center<25 or depth>=center-.15 or center+depth>=39:raise ValueError('unresolved delay trajectory')
    p0=[center-depth,depth,f,phase,1.];lo=[.15,0.,.05,-8.,-2.];hi=[25.,12.,5.,8.,2.]
    def residual(q,kind):
        p=unpack(q)
        if p[0]+p[1]>40:return np.full(len(x[::3]),100.+p[0]+p[1])
        return (predict(x,fs,p,kind)-y)[::3]/max(np.sqrt(np.mean(y*y)),1e-12)
    reports=[]
    for kind in ('linear','cubic'):
        fit=least_squares(lambda q:residual(q,kind),np.clip(p0,np.array(lo)+1e-8,np.array(hi)-1e-8),bounds=(lo,hi),x_scale='jac',max_nfev=70)
        p=unpack(fit.x);err=float(np.linalg.norm(predict(z,sr,p,kind)-w)/max(np.linalg.norm(w),1e-12));reports.append(dict(kind=kind,converged=bool(fit.success),parameters=p.tolist(),validation=err))
    passing=[r for r in reports if r['converged'] and r['validation']<=threshold]
    return dict(track_windows=len(t),candidates=reports,selected=min(passing,key=lambda r:r['validation']) if passing else None)
