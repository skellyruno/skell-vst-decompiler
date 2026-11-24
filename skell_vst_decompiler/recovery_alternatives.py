"""Independent descriptive recovery competitor, not a physical compressor model."""
import numpy as np
from scipy.optimize import least_squares


def fit_stretched(times_ms, reduction, steady=0.):
    t,y=np.asarray(times_ms,float),np.asarray(reduction,float)
    if (t.ndim!=1 or t.shape!=y.shape or not 20<=len(t)<=10000 or
        not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)) or
        not np.isfinite(steady) or np.any(np.diff(t)<=0)):
        raise ValueError('Invalid recovery series')
    t=t-t[0];y=y-steady;cut=int(.65*len(t));scale=y[0]
    if scale<=0:raise ValueError('Positive initial reduction required')
    def predict(p,tt):return scale*p[0]*np.exp(-(tt/np.exp(p[1]))**p[2])
    best=None
    for tau,beta in [(30.,.5),(200.,1.),(1000.,1.5)]:
        fit=least_squares(lambda p:(predict(p,t[:cut])-y[:cut])/scale,
            [1.,np.log(tau),beta],bounds=([0.,np.log(5.),.2],[4.,np.log(3000.),2.]),max_nfev=300)
        if fit.success and (best is None or fit.cost<best.cost):best=fit
    if best is None:raise RuntimeError('Recovery optimizer did not converge')
    p=best.x;pred=predict(p,t)
    return {'tau_ms':float(np.exp(p[1])),'amplitude':float(scale*p[0]),'beta':float(p[2]),
        'train_rmse':float(np.sqrt(np.mean((pred[:cut]-y[:cut])**2))),
        'heldout_rmse':float(np.sqrt(np.mean((pred[cut:]-y[cut:])**2)))}


def compare_recovery(times_ms,reduction,noise_sd,steady=0.):
    """Require the dual hypothesis to beat both single and stretched competitors."""
    from .advanced_dsp import recovery_continuous
    from .adaptive_research import assess_recovery
    fits=recovery_continuous(times_ms,reduction,steady)
    stretched=fit_stretched(times_ms,reduction,steady)
    old=assess_recovery(fits,noise_sd)
    ed=fits['2']['heldout_rmse'];es=stretched['heldout_rmse']
    supported=old=='dual_descriptive_preferred' and es-ed>max(noise_sd,.2*es)
    return {'single':fits['1'],'dual':fits['2'],'stretched':stretched,
            'previous_preference':old,'preference':'dual_descriptive_preferred' if supported else 'dual_not_established'}
