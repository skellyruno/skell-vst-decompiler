"""Independent behavioral descriptions; no inference of a proprietary implementation."""
import numpy as np
from scipy.optimize import least_squares


def recovery_models(times, depths, train):
    """Fit shared recovery descriptions on whole training curves; withhold other curves.

    depths: positive gain deficit in dB relative to an independently measured quiet
    steady-state gain. Initial sample of each withheld curve seeds the prediction.
    No other withheld measurements enter the fit. Errors are dB, not similarity.
    """
    t,d,m=np.asarray(times,float),np.asarray(depths,float),np.asarray(train)
    if t.ndim!=1 or not 5<=len(t)<=1000 or t[0]!=0 or np.any(np.diff(t)<=0) or not np.isfinite(t).all() or t[-1]>30 or d.ndim!=2 or d.shape[1]!=len(t) or not 4<=len(d)<=1000 or not np.isfinite(d).all() or np.max(abs(d))>120 or np.any(d[:,0]<=.05) or m.shape!=(len(d),) or m.dtype!=bool or m.sum()<2 or (~m).sum()<2:
        raise ValueError('invalid recovery observations')
    if np.unique(d[m,0].round(4)).size<2:raise ValueError('initial depth diversity required')
    def predict(p,initial,kind):
        initial=initial[:,None]; u=t[None,:]
        if kind==0:return initial*np.exp(-u/p[0])
        if kind==1:
            a=10**(-initial/20);return -20*np.log10(1-(1-a)*np.exp(-u/p[0]))
        if kind==2:return initial*np.exp(-(u/p[0])**p[1])
        # Vary the decay time with the independently observed initial depth.
        return initial*np.exp(-u/(p[0]*np.exp(p[1]*initial/20)))
    out=[]
    for k,name in enumerate(('db_exponential','linear_gain_exponential','stretched_db','initial_depth_dependent')):
        start=[.15] if k<2 else [.15,1.] if k==2 else [.15,0.]
        bounds=([.001],[10.]) if k<2 else ([.001,.2],[10.,3.]) if k==2 else ([.001,-2.],[10.,2.])
        fit=least_squares(lambda p:(predict(p,d[m,0],k)[:,1:]-d[m,1:]).ravel(),start,bounds=bounds,max_nfev=300)
        if not fit.success:raise RuntimeError('recovery fit did not converge')
        e=predict(fit.x,d[:,0],k)[:,1:]-d[:,1:]
        out.append(dict(model=name,parameters=fit.x.tolist(),train_rmse_db=float(np.sqrt(np.mean(e[m]**2))),heldout_rmse_db=float(np.sqrt(np.mean(e[~m]**2)))))
    return out


def detector_frequency_models(peak,rms,hz,gain,train):
    """Compare level-only, frequency tilt and level/frequency interaction descriptions."""
    p,r,f,y=map(lambda v:np.asarray(v,float),(peak,rms,hz,gain)); m=np.asarray(train)
    if p.ndim!=1 or not 12<=len(p)<=10000 or any(v.shape!=p.shape or not np.isfinite(v).all() for v in (p,r,f,y)) or not np.isfinite(p).all() or np.any(r<=0) or np.any(r>p*(1+1e-12)) or np.any(f<20) or np.any(f>20000) or m.shape!=p.shape or m.dtype!=bool or m.sum()<8 or (~m).sum()<4:
        raise ValueError('invalid detector data')
    out=[]; z=np.log2(f/1000)
    for typ,v in [('peak',p),('rms',r)]:
        x=20*np.log10(v)/20
        for order in range(3):
            cols=[np.ones(len(x)),x]
            if order>=1:cols.append(z)
            if order>=2:cols.append(x*z)
            A=np.column_stack(cols); c,_,rank,_=np.linalg.lstsq(A[m],y[m],rcond=None)
            if rank!=A.shape[1]:raise ValueError('rank deficient detector design')
            e=A@c-y;out.append(dict(model=typ+'_'+str(order),train_rmse_db=float(np.sqrt(np.mean(e[m]**2))),heldout_rmse_db=float(np.sqrt(np.mean(e[~m]**2)))))
    return out


def surfaces3(train_x,train_y,test_x,test_y):
    """Three control axes; disjoint cells; fit main effects, pair and triple interactions."""
    x,z=np.asarray(train_x,float),np.asarray(test_x,float);y,w=np.asarray(train_y,float),np.asarray(test_y,float)
    for a,b in ((x,y),(z,w)):
        if a.ndim!=2 or a.shape[1]!=3 or not 8<=len(a)<=10000 or b.shape!=(len(a),) or not np.isfinite(a).all() or not np.isfinite(b).all() or np.max(abs(a))>1 or len(set(map(tuple,a)))!=len(a):raise ValueError('invalid cells')
    if set(map(tuple,x))&set(map(tuple,z)):raise ValueError('overlapping cells')
    def design(a,k):
        p,q,r=a.T;cols=[np.ones(len(a)),p,q,r]
        if k>=1:cols.extend([p*q,p*r,q*r])
        if k>=2:cols.extend([p*p,q*q,r*r])
        if k>=3:cols.append(p*q*r)
        return np.column_stack(cols)
    out=[]
    for k,n in enumerate(('additive','pairwise','quadratic','three_way')):
        A,B=design(x,k),design(z,k);c,_,rank,_=np.linalg.lstsq(A,y,rcond=None)
        if rank!=A.shape[1]:raise ValueError('rank deficient surface')
        out.append(dict(model=n,train_rmse_db=float(np.sqrt(np.mean((A@c-y)**2))),heldout_rmse_db=float(np.sqrt(np.mean((B@c-w)**2)))))
    return out
