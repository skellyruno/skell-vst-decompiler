"""Original topology diagnostics for aligned authorized/owned observations.
Statuses describe tested input behavior, not unique internal circuit structure.
"""
import numpy as np
from scipy.optimize import least_squares


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float)**2)))


def screen(outputs, suffix_start, tol=1e-5):
    """Outputs for x, x repeat, .5*x, z, x+z, alternate prefix x.
    Caller ensures last input shares x's suffix and all renders start reset.
    """
    y=np.asarray(outputs,float)
    if y.ndim!=3 or y.shape[0]!=6 or y.shape[2]!=2 or not 32<=y.shape[1]<=1920000 or not np.isfinite(y).all() or not 0<suffix_start<y.shape[1] or not 0<tol<.01:
        raise ValueError('invalid aligned observations')
    a,b,c,d,e,f=y; scale=max(rms(a),rms(d),rms(e),1e-12)
    repeat=rms(a-b)/scale; hom=rms(c-.5*a)/scale; add=rms(e-a-d)/scale
    history=rms(f[suffix_start:]-a[suffix_start:])/max(rms(a[suffix_start:]),rms(f[suffix_start:]),1e-12)
    limit=max(tol,5*repeat)
    return dict(repeat=repeat,homogeneity=hom,superposition=add,history=history,
                rejected=(['deterministic_fixed_state'] if repeat>tol else [])+(['linear'] if max(hom,add)>limit else [])+(['memoryless'] if history>limit else []),
                silent=scale<1e-9, threshold=limit)


def stereo_intervention(base,changed,channel=0):
    """Change only other input channel; target must be same aligned nonzero signal."""
    a,b=np.asarray(base,float),np.asarray(changed,float)
    if a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=2 or channel not in (0,1) or len(a)<32 or not np.isfinite(a).all() or not np.isfinite(b).all() or rms(a[:,channel])<1e-9:
        raise ValueError('invalid stereo observation')
    return 20*np.log10(max(rms(b[:,channel]),1e-15)/rms(a[:,channel]))


def knee_curve(level,threshold,slope,width):
    d=np.asarray(level,float)-threshold
    if width<=0:return -slope*np.maximum(d,0)
    return -slope*np.where(d<=-width/2,0,np.where(d>=width/2,d,(d+width/2)**2/(2*width)))


def knee_models(level,gain,train):
    x,y,m=np.asarray(level,float),np.asarray(gain,float),np.asarray(train)
    if x.ndim!=1 or y.shape!=x.shape or m.shape!=x.shape or m.dtype!=bool or not np.isfinite(np.r_[x,y]).all() or m.sum()<6 or (~m).sum()<4 or len(set(x))!=len(x):raise ValueError('invalid level grid')
    out=[]
    for soft in (False,True):
        def fn(p):return knee_curve(x,p[0],p[1],p[2] if soft else 0)
        p=[-24,.75]+([6] if soft else []);lo=[-60,0]+([.001] if soft else []);hi=[0,1]+([30] if soft else [])
        f=least_squares(lambda p:(fn(p)-y)[m],p,bounds=(lo,hi),max_nfev=500)
        if not f.success:raise RuntimeError('fit failed')
        out.append(dict(model='soft' if soft else 'hard',parameters=f.x.tolist(),holdout_rmse_db=rms((fn(f.x)-y)[~m])))
    return out


def release_signature(curves,dt):
    """Positive gain deficits vs steady baseline; report first 10% drop and t50.
    No claim of an internal hold timer or time constant. Right censor if not reached.
    """
    a=np.asarray(curves,float)
    if a.ndim!=2 or not 2<=len(a)<=64 or not 10<=a.shape[1]<=10000 or not np.isfinite(a).all() or np.any(a[:,0]<=.1) or not 0<dt<=.1:raise ValueError('invalid recovery curves')
    out=[]
    for row in a:
        def first(ratio):
            i=np.flatnonzero(row<=ratio*row[0]);return float(i[0]*dt) if len(i) else None
        out.append(dict(initial_db=float(row[0]),first_10pct_drop_seconds=first(.9),t50_seconds=first(.5)))
    return out


def candidate_gate(result,shift_error):
    """Conservative screening: withhold optimization on unstable or silent evidence.
    Candidate descriptions only, not claims of the underlying implementation.
    """
    if not np.isfinite(shift_error) or shift_error<0:raise ValueError('invalid shift residual')
    if result['silent'] or 'deterministic_fixed_state' in result['rejected']:
        return dict(action='RECAPTURE',eligible=[],rejected=[])
    rejected=[]
    if 'linear' in result['rejected']:rejected.extend(['linear_time_invariant','linear_time_varying'])
    if 'memoryless' in result['rejected']:rejected.append('static_transfer')
    if shift_error>result['threshold']:
        if 'linear_time_invariant' not in rejected:rejected.append('linear_time_invariant')
        if 'static_transfer' not in rejected:rejected.append('static_transfer')
    models=['static_transfer','linear_time_invariant','linear_time_varying','nonlinear_stateful']
    return dict(action='SCREENED',eligible=[m for m in models if m not in rejected],rejected=rejected)
