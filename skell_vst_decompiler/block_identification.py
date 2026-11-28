"""Original block-oriented hypotheses for aligned offline observations."""
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.optimize import least_squares

ORDERS={'static':(0,0),'pre':(1,0),'post':(0,1),'pre2':(2,0),'post2':(0,2),'split':(1,1)}


def predict(x, fs, model, p, order=1):
    pre,post=ORDERS[model]
    if order not in (1,2):raise ValueError('invalid filter order')
    x=np.asarray(x,float);p=np.asarray(p,float)
    if x.ndim!=1 or not 1<=len(x)<=768000 or not 8000<=fs<=192000 or not np.isfinite(x).all() or np.max(abs(x))>4 or p.shape!=(2+pre+post,) or not np.isfinite(p).all():raise ValueError('invalid observation')
    drive,gain,*cuts=np.exp(p)
    if not .1<=drive<=40 or not .01<=gain<=10 or any(not 100<=c<.49*fs for c in cuts):raise ValueError('out of range')
    def filt(z, cs):
        for c in cs:z=sosfilt(butter(order,c,fs=fs,output='sos'),z)
        return z
    return gain*filt(np.tanh(drive*filt(x,cuts[:pre])),cuts[pre:])


def fit_candidates(train, validation, models=tuple(ORDERS), limit=1e-4, order=1):
    """Fit training only, choose simplest passing separate validation. No unique topology claim."""
    if not 1<=len(train)<=8 or not 1<=len(validation)<=8 or not 0<limit<=.01:raise ValueError('invalid fit budget')
    rows=[]
    for x,y,fs in [*train,*validation]:
        x,y=np.asarray(x,float),np.asarray(y,float)
        if x.shape!=y.shape or x.ndim!=1 or len(x)<1024 or len(x)>768000 or not np.isfinite(y).all() or np.linalg.norm(y)<1e-8:raise ValueError('invalid target')
        predict(x,fs,'static',np.zeros(2),order);rows.append((x,y,fs))
    if any(a[2]==b[2] and np.array_equal(a[0],b[0]) for a in rows[:len(train)] for b in rows[len(train):]):raise ValueError('duplicate input')
    maxcut=min(16000.,.45*min(row[2] for row in rows))
    def residual(group,name,p):
        return np.concatenate([(predict(x,fs,name,p,order)-y)[::4]/max(np.sqrt(np.mean(y*y)),1e-12) for x,y,fs in group])
    out=[]
    for name in models:
        n=sum(ORDERS[name]);lo=np.log([.101,.011]+[101.]*n);hi=np.log([39.,9.9]+[maxcut]*n)
        starts=[np.log([3.,.9]+[1800.,6500.][:n]),np.log([7.,.8]+[6500.,1800.][:n])] if n else [np.log([3.,.9])]
        fits=[least_squares(lambda p:residual(rows[:len(train)],name,p),np.clip(p,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=75) for p in starts]
        valid=[f for f in fits if f.success]
        if not valid:
            out.append(dict(model=name,parameters=None,converged=False,validation_relative_rms=None,evaluations=sum(f.nfev for f in fits)));continue
        f=min(valid,key=lambda r:r.cost)
        out.append(dict(model=name,parameters=f.x.tolist(),converged=True,training_relative_rms=float(np.sqrt(np.mean(residual(rows[:len(train)],name,f.x)**2))),validation_relative_rms=float(np.sqrt(np.mean(residual(rows[len(train):],name,f.x)**2))),evaluations=sum(f.nfev for f in fits)))
    ok=[r for r in out if r['converged'] and r['validation_relative_rms']<=limit]
    best=min(ok,key=lambda r:(len(r['parameters']),r['validation_relative_rms'])) if ok else None
    return dict(candidates=out,selected=best['model'] if best else None,status='SUPPORTED_DESCRIPTION' if best else 'NO_PASSING_DESCRIPTION',threshold=limit,filter_order=order)


def fit_orders(train, validation, limit=1e-4):
    """Compare both bounded filter orders on the same data; no isolated-stage access needed."""
    reports=[fit_candidates(train,validation,limit=limit,order=o) for o in (1,2)]
    passing=[(r['filter_order'],c) for r in reports for c in r['candidates'] if c['converged'] and c['validation_relative_rms']<=limit]
    chosen=min(passing,key=lambda oc:(len(oc[1]['parameters']),oc[0]*sum(ORDERS[oc[1]['model']]),oc[1]['validation_relative_rms'])) if passing else None
    return dict(orders=reports,selected=dict(order=chosen[0],**chosen[1]) if chosen else None,status='SUPPORTED_DESCRIPTION' if chosen else 'NO_PASSING_DESCRIPTION',threshold=limit)
