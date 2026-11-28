"""Original synthetic time-varying pitch corpus and transparent score."""
import numpy as np


def trajectory_cases(fs=48000):
    if type(fs) is not int or not 8000<=fs<=192000:raise ValueError('Invalid sample rate')
    t=np.arange(fs*2)/fs
    rng=np.random.default_rng(291)
    cases={}
    for name,f in [('vibrato',220*2**((35*np.sin(2*np.pi*5*t))/1200)),
                   ('glide',110*2**(t/2)),
                   ('step',np.where(t<1,220.,330.))]:
        phase=2*np.pi*np.cumsum(f)/fs
        signal=np.sin(phase)+.4*np.sin(2*phase)+.2*np.sin(3*phase)+rng.normal(0,.03,len(t))
        voiced=np.ones(len(t),dtype=bool)
        voiced[(t>=.6)&(t<.8)]=False
        signal[~voiced]=rng.normal(0,.08,np.count_nonzero(~voiced))
        cases[name]=(signal,f,voiced)
    return cases


def score(detector,signal,truth,voiced,fs,frame_ms=65.,hop_ms=10.):
    """Score at window center; exclude windows crossing voiced/note steps."""
    n=round(fs*frame_ms/1000);hop=round(fs*hop_ms/1000)
    if n<2 or hop<1:raise ValueError('Invalid frame or hop')
    errors=[];missed=false_positive=excluded=voiced_total=unvoiced_total=0
    for start in range(0,len(signal)-n+1,hop):
        end=start+n; mid=start+n//2; flags=voiced[start:end]
        if np.any(flags)!=np.all(flags) or (np.max(truth[start:end])/np.min(truth[start:end])>1.3):
            excluded+=1;continue
        hz,_=detector(signal[start:end],fs)
        if flags[0]:
            voiced_total+=1
            if hz is None:missed+=1
            else:errors.append(abs(1200*np.log2(hz/truth[mid])))
        else:
            unvoiced_total+=1
            false_positive+=hz is not None
    return {'voiced_frames':voiced_total,'unvoiced_frames':unvoiced_total,
            'excluded_transition_frames':excluded,'missed_voiced':missed,
            'false_positive_unvoiced':false_positive,'accepted_voiced':len(errors),
            'median_abs_cents':float(np.median(errors)) if errors else None,
            'p95_abs_cents':float(np.percentile(errors,95)) if errors else None,
            'gross_errors_over_50_cents':int(np.count_nonzero(np.asarray(errors)>50))}
