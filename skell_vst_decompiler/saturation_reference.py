"""Independent antiderivative anti-aliasing saturation (offline reference).

First-order ADAA of normalized tanh; the two-sample average introduces
frequency-dependent attenuation and roughly half a sample of delay at low
frequencies. This is not a drop-in replacement for the production clipper.
"""
import numpy as np


def saturate(samples, drive=3., *, antialias=True):
    if not np.isfinite(drive) or not .1<=drive<=20.:
        raise ValueError('Invalid drive')
    x=np.asarray(samples,dtype=np.float64)
    if x.ndim!=1 or not len(x) or not np.all(np.isfinite(x)) or np.max(np.abs(x))>64:
        raise ValueError('Expected bounded finite mono samples')
    scale=np.tanh(drive)
    if not antialias:
        return np.tanh(drive*x)/scale
    prev=np.concatenate((x[:1],x[:-1]))
    # log(cosh(z)) = logaddexp(z,-z)-log(2); stable for large z.
    f=(np.logaddexp(drive*x,-drive*x)-np.log(2.))/(drive*scale)
    g=(np.logaddexp(drive*prev,-drive*prev)-np.log(2.))/(drive*scale)
    delta=x-prev
    result=np.tanh(drive*(x+prev)*.5)/scale
    np.divide(f-g,delta,out=result,where=np.abs(delta)>1e-6)
    return result
