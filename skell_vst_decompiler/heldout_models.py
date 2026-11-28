"""Independent descriptive models for authorized aligned measurements, not source recovery."""
import numpy as np


def design(x, order):
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]!=2 or not np.isfinite(x).all() or np.max(np.abs(x),initial=0)>1:
        raise ValueError('two normalized axes in [-1,1] required')
    a,b=x.T
    cols=[np.ones(len(x)),a,b]
    if order>=1: cols.append(a*b)
    if order>=2: cols.extend([a*a,b*b])
    return np.column_stack(cols)


def compare_surfaces(train_x, train_y, test_x, test_y):
    """Fit only training cells, score three fixed models on distinct withheld cells."""
    tx,hx=np.asarray(train_x,float),np.asarray(test_x,float)
    ty,hy=np.asarray(train_y,float),np.asarray(test_y,float)
    for x,y in ((tx,ty),(hx,hy)):
        design(x,2)
        if not 1<=len(x)<=10000 or y.shape!=(len(x),) or not np.isfinite(y).all() or len(set(map(tuple,x)))!=len(x):
            raise ValueError('invalid or duplicate measurements')
    if set(map(tuple,tx))&set(map(tuple,hx)) or len(tx)<6 or len(hx)<3:
        raise ValueError('distinct training and holdout required')
    rows=[]
    for order,name in enumerate(('additive','interaction','quadratic')):
        a,b=design(tx,order),design(hx,order)
        coef,_,rank,_=np.linalg.lstsq(a,ty,rcond=None)
        if rank!=a.shape[1]:raise ValueError('rank deficient training design')
        rows.append({'model':name,'train_rmse':float(np.sqrt(np.mean((a@coef-ty)**2))), 'heldout_rmse':float(np.sqrt(np.mean((b@coef-hy)**2)))})
    return rows


def detector_models(peak,rms,observed,train_mask):
    """Compare affine log-level descriptions; not evidence of internal detector type."""
    p,r,y=np.asarray(peak,float),np.asarray(rms,float),np.asarray(observed,float)
    mask=np.asarray(train_mask)
    if p.ndim!=1 or p.shape!=r.shape or p.shape!=y.shape or mask.shape!=p.shape or mask.dtype!=bool or not 6<=len(p)<=10000 or not np.isfinite(np.r_[p,r,y]).all() or np.any(r<=0) or np.any(r>p*(1+1e-12)) or mask.sum()<3 or (~mask).sum()<3:
        raise ValueError('invalid detector observations')
    rows=[]
    for name,v in [('peak',p),('rms',r)]:
        a=np.column_stack((np.ones(len(v)),20*np.log10(v)))
        coef,_,rank,_=np.linalg.lstsq(a[mask],y[mask],rcond=None)
        if rank!=2:raise ValueError('insufficient level diversity')
        rows.append({'model':name,'train_rmse_db':float(np.sqrt(np.mean((a[mask]@coef-y[mask])**2))), 'heldout_rmse_db':float(np.sqrt(np.mean((a[~mask]@coef-y[~mask])**2)))})
    return rows


def tail_windows(audio,fs,*,window_ms=100,threshold_db=-90):
    """Measure full tail RMS windows and flag right censoring; no RT60 extrapolation."""
    a=np.asarray(audio,float)
    if type(fs)!=int or not 8000<=fs<=192000 or a.ndim!=2 or a.shape[1]!=2 or not 1<=len(a)<=30*fs or not np.isfinite(a).all() or not np.isfinite(window_ms) or not 1<=window_ms<=1000 or not np.isfinite(threshold_db) or not -150<=threshold_db<=-20:
        raise ValueError('invalid tail input')
    n=max(1,round(fs*window_ms/1000)); rows=[]
    for i in range(0,len(a),n):
        x=a[i:i+n]; db=float(20*np.log10(max(1e-15,np.sqrt(np.mean(x*x)))))
        rows.append({'end_ms':1000*min(i+n,len(a))/fs,'rms_dbfs':db})
    active=[r for r in rows if r['rms_dbfs']>threshold_db]
    return {'last_active_ms':active[-1]['end_ms'] if active else None,'right_censored':rows[-1]['rms_dbfs']>threshold_db,'windows':rows}


def recurrence_models(train,holdout):
    """Fit AR orders 1 and 2 on one observed decay, predict another recursively.

    Two measured initial samples seed each holdout; no subsequent fitting.
    Use only a declared homogeneous, zero-input response segment.
    """
    a,b=np.asarray(train,float),np.asarray(holdout,float)
    if any(x.ndim!=1 or not 8<=len(x)<=100000 or not np.isfinite(x).all() for x in (a,b)) or np.linalg.norm(a)<1e-12 or np.linalg.norm(b)<1e-12:
        raise ValueError('invalid response')
    out=[]
    for order in (1,2):
        A=np.column_stack([a[2-j:len(a)-j] for j in range(1,order+1)])
        c,_,rank,_=np.linalg.lstsq(A,a[2:],rcond=1e-10)
        if rank!=order:
            out.append({'order':order,'status':'UNIDENTIFIABLE'});continue
        roots=np.roots(np.r_[1,-c]);stable=bool(np.max(abs(roots))<=1)
        if not stable:
            out.append({'order':order,'status':'UNSTABLE'});continue
        y=np.zeros_like(b);y[:2]=b[:2]
        for i in range(2,len(b)):y[i]=sum(c[j]*y[i-j-1] for j in range(order))
        out.append({'order':order,'status':'SCORED','heldout_relative_error':float(np.linalg.norm(y[2:]-b[2:])/max(np.linalg.norm(b[2:]),1e-15)),'train_relative_error':float(np.linalg.norm(A@c-a[2:])/max(np.linalg.norm(a[2:]),1e-15))})
    return out
