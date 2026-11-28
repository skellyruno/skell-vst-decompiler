"""Compare independent descriptions of two owner-exported chains; no vendor code or audio export."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import correlate,correlation_lags
from scipy.optimize import least_squares


def compare(base_path,target_path):
    paths=[Path(base_path),Path(target_path)]; inputs=[sf.read(p,always_2d=True) for p in paths]
    (x,fs),(y,sr)=inputs
    if fs!=sr or x.shape!=y.shape or x.ndim!=2 or x.shape[1]!=2 or len(x)<fs*15 or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('reference format mismatch')
    # Do not optimize alignment or shift samples: verify known declared zero lag.
    a=x[fs:4*fs,0];b=y[fs:4*fs,0];cc=correlate(b,a,mode='full',method='fft');lags=correlation_lags(len(b),len(a));near=np.abs(lags)<=128;lag=int(lags[near][np.argmax(cc[near])]);
    if lag!=0:raise ValueError('nonzero lag; investigate capture before comparison')
    n=len(x);split=n//3;train=x[:split:16].ravel();truth=y[:split:16].ravel()
    gain=float(train@truth/(train@train))
    # Independently chosen smooth saturating description, no exact plugin equation claim.
    def saturate(v,p):return p[0]*np.tanh(v*p[1])
    fit=least_squares(lambda p:saturate(train,p)-truth,[1.,1.],bounds=([.001,.001],[10.,20.]),max_nfev=100)
    if not fit.success:raise RuntimeError('fit failed')
    def metrics(a,b):
        delta=a-b;return {'relative_rms':float(np.sqrt(np.mean(delta**2)/np.mean(b**2))),'peak_abs_error':float(np.max(abs(delta))), 'correlation':float(np.corrcoef(a.ravel(),b.ravel())[0,1])}
    rows=[]
    for name,lo,hi in [('fit',0,split),('validation',split,2*split),('final_holdout',2*split,n)]:
        v,w=x[lo:hi],y[lo:hi];rows.append({'section':name,'frames':len(v),'observed_gain_db':float(10*np.log10(np.mean(w*w)/np.mean(v*v))),'unchanged':metrics(v,w),'scalar_gain':metrics(v*gain,w),'smooth_saturation':metrics(saturate(v,fit.x),w)})
    # Residual conditioned on input amplitude: descriptive, not evidence of clipper internals.
    lo=2*split;v=x[lo:];w=y[lo:];res=saturate(v,fit.x)-w;bins=[]
    for lower,upper in [(0,.1),(.1,.3),(.3,.6),(.6,1.01)]:
        m=(abs(v)>=lower)&(abs(v)<upper)
        if m.any():bins.append({'input_abs_range':[lower,upper],'samples':int(m.sum()),'residual_rms':float(np.sqrt(np.mean(res[m]**2)))})
    return {'scope':'owner four- vs five-processor chain exports; downstream stages not isolated','sample_rate':fs,'frames':n,'observed_lag_samples':lag,'sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],'training_scalar_gain':gain,'training_saturation_parameters':fit.x.tolist(),'sections':rows,'holdout_amplitude_bins':bins}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('master_only');p.add_argument('master_plus_clip');p.add_argument('output',type=Path);a=p.parse_args();r=compare(a.master_only,a.master_plus_clip);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r,indent=2))
