"""Original offline behavioral diagnostics, not recovered vendor processing."""
import numpy as np


def recovery_models(times_ms, reduction, steady=0., train_fraction=.65):
    """Compare one/two exponential descriptive models on a later held-out tail.

    Fit nonnegative amplitudes on a fixed time-constant grid. No inference
    of actual circuit, state variables, or code. Units are caller-defined.
    """
    t,y=np.asarray(times_ms,dtype=float),np.asarray(reduction,dtype=float)
    if (t.ndim!=1 or t.shape!=y.shape or not 12<=len(t)<=10000
        or not np.all(np.isfinite(t)) or not np.all(np.isfinite(y))
        or not np.isfinite(steady) or np.any(np.diff(t)<=0)
        or not .5<=train_fraction<=.8):
        raise ValueError('Invalid recovery series')
    t=t-t[0]; y=y-steady
    if np.any(y<0) or y[0]<=1e-9:
        raise ValueError('Expected positive reduction above steady value')
    cut=int(len(t)*train_fraction)
    grid=np.geomspace(5.,2000.,32)
    basis=np.exp(-t[:,None]/grid)
    a=basis[:cut]; b=y[:cut]
    best1=None;best2=None
    def candidate(idx,weights):
        pred=basis[:,idx]@weights
        return {'tau_ms':[float(grid[i]) for i in idx],
                'amplitude':[float(x) for x in weights],
                'train_rmse':float(np.sqrt(np.mean((pred[:cut]-b)**2))),
                'heldout_rmse':float(np.sqrt(np.mean((pred[cut:]-y[cut:])**2)))}
    for i in range(len(grid)):
        v=a[:,i]; w=max(0.,float(v@b)/float(v@v))
        row=candidate([i],np.array([w]))
        if best1 is None or row['train_rmse']<best1['train_rmse']:best1=row
        for j in range(i+1,len(grid)):
            design=a[:,[i,j]]
            weights=np.linalg.lstsq(design,b,rcond=None)[0]
            if np.any(weights<0):continue
            row=candidate([i,j],weights)
            if best2 is None or row['train_rmse']<best2['train_rmse']:best2=row
    return {'single':best1,'dual':best2,'train_count':cut,'heldout_count':len(t)-cut,
            'note':'Descriptive model fit, not proof of an implementation. Grid resolution limits estimates.'}


def detector_probes(fs=48000):
    """Identical RMS, different crest factor; stereo link discrimination."""
    if type(fs) is not int or not 8000<=fs<=192000:raise ValueError('Invalid sample rate')
    t=np.arange(fs)/fs
    sine=np.sin(2*np.pi*200*t)
    pulse=np.where(np.arange(fs)%100<10,1.,0.)
    pulse-=np.mean(pulse)
    def scale(x):return .1*x/np.sqrt(np.mean(x*x))
    sine,pulse=scale(sine),scale(pulse)
    return {'sine_dual_mono':np.column_stack((sine,sine)),
            'pulse_dual_mono':np.column_stack((pulse,pulse)),
            'sine_left_only':np.column_stack((sine,np.zeros_like(sine)))}


def detector_levels(x):
    """Global static measurements; not a time-varying envelope."""
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or x.shape[1]!=2 or not len(x) or not np.all(np.isfinite(x)):
        raise ValueError('Expected finite stereo samples')
    return {'linked_peak':float(np.max(np.abs(x))),
            'linked_mean_power_rms':float(np.sqrt(np.mean(x*x))),
            'max_channel_rms':float(np.max(np.sqrt(np.mean(x*x,axis=0))))}
