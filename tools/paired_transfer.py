"""Offline stationary-vs-time-varying diagnostic for authorized paired audio.
No vendor code, no exported fitted coefficients. Splits precede fitting.
"""
import argparse
import io
import json
import zipfile
import numpy as np
from scipy import signal, linalg


def nmse(y, p):
    return float(np.sum((y-p)**2)/max(np.sum(y*y),1e-20))


def fit_fir(x, y, length, ridge=1e-3):
    # Zero-padded full convolution normal equations. End effects are a
    # modeling choice; score only the actual observed time interval.
    ac=signal.correlate(x,x,method='fft')[len(x)-1:len(x)-1+length].copy()
    cross=signal.correlate(y,x,method='fft')[len(x)-1:len(x)-1+length]
    ac[0]+=max(1e-12,ac[0]*ridge)
    return linalg.solve_toeplitz(ac,cross,check_finite=True)


def evaluate(x, y, fs, lengths=(1,128,1024,4096)):
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    if x.ndim!=1 or x.shape!=y.shape or not np.isfinite(x).all() or not np.isfinite(y).all() or len(x)<max(lengths)*5 or not 8000<=fs<=192000:
        raise ValueError('aligned finite mono arrays and sufficient data required')
    a=int(.4*len(x));b=int(.6*len(x));slices=(slice(0,a),slice(a,b),slice(b,len(x)))
    if np.sum(x[:a]**2)<1e-12 or min(np.sum(y[s]**2) for s in slices)<1e-12:
        return {'status':'insufficient signal energy'}
    models=[]
    for length in lengths:
        h=fit_fir(x[:a],y[:a],length)
        pred=signal.fftconvolve(x,h)[:len(x)]
        models.append({'taps':length,'train':nmse(y[:a],pred[:a]),'validation':nmse(y[a:b],pred[a:b]),'later':nmse(y[b:],pred[b:])})
    selected=min(models,key=lambda m:m['validation'])
    # Independent diagnostic: lag and correlation in active half-second blocks.
    # Not an alignment correction; selection uses absolute correlation in +/-50ms.
    win=int(fs*.5);lag=int(fs*.05);lags=[];corr=[]
    for i in range(0,len(x)-win+1,win):
        xx=x[i:i+win];yy=y[i:i+win]
        if np.sqrt(np.mean(xx*xx))<1e-3 or np.sqrt(np.mean(yy*yy))<1e-3:continue
        z=signal.correlate(yy,xx,method='fft');z=z[win-1-lag:win+lag]/np.sqrt(np.dot(xx,xx)*np.dot(yy,yy))
        k=int(np.argmax(np.abs(z)));lags.append((k-lag)*1000/fs);corr.append(float(z[k]))
    # Coherence separately per split; no phase or magnitude assumptions.
    coh=[]
    for s in slices:
        f,c=signal.coherence(x[s],y[s],fs=fs,nperseg=512,noverlap=256)
        coh.append([float(np.median(c[(f>=lo)&(f<hi)])) for lo,hi in [(100,500),(500,2000),(2000,4500)]])
    return {'status':'diagnostic','models':models,'chosen_taps':selected['taps'],'selected_later_nmse':selected['later'], 'active_blocks':len(lags),'lag_ms_quantiles':np.percentile(lags,[10,50,90]).tolist() if lags else None,'abs_corr_median':float(np.median(np.abs(corr))) if corr else None,'coherence_medians_train_validation_later':coh,'limits':'Stationary FIR approximation, not recovered algorithm. Same-take later section is not independent performance; no stage/offset identity proof. Block lag is diagnostic only.'}


def selftest():
    rng=np.random.default_rng(22);x=rng.normal(size=60000)*.1
    h=np.zeros(128);h[0]=.6;h[31]=-.25;h[90]=.2
    y=signal.fftconvolve(x,h)[:len(x)];r=evaluate(x,y,12000,(1,128,512))
    assert r['selected_later_nmse']<1e-4 and r['models'][0]['later']>.1
    y2=y.copy();y2[int(.6*len(y)):]*=-1
    r2=evaluate(x,y2,12000,(1,128,512));assert r2['selected_later_nmse']>3.9
    print('known causal FIR and unseen polarity reversal: PASS')


def club(archive):
    import soundfile as sf
    with zipfile.ZipFile(archive) as z:
        def read(n):
            x,fs=sf.read(io.BytesIO(z.read(n)),always_2d=True,dtype='float64')
            if fs!=44100 or x.shape[1]!=2:raise ValueError('unexpected source format')
            return x
        src=read('club gate.wav');raw=read('club raw.wav')
        if np.max(np.abs(src[:,0]-src[:,1]))>1e-7 or np.max(np.abs(raw[:,0]-raw[:,1]))>1e-7:raise ValueError('source not dual mono')
        rows={}
        files={'gate':'club gate.wav','wobble':'club wobble adlib w gate.wav','muffle':'club mufflr adlibs w gate.wav','zaam':'club zaam adlib w gate.wav','angelic_base':'club angelic adlib w gate w no delay.wav','angelic_delay':'club angelic adlib w gate w delay.wav'}
        for name,path in files.items():
            y=read(path);s=raw if name=='gate' else src
            if y.shape!=s.shape:raise ValueError('source duration mismatch')
            x=signal.resample_poly(s.mean(axis=1),1,4)
            m=signal.resample_poly(y.mean(axis=1),1,4);side=signal.resample_poly((y[:,0]-y[:,1])*.5,1,4)
            rows[name]={'mid':evaluate(x,m,11025),'side':evaluate(x,side,11025),'side_mid_db':float(10*np.log10(max(np.sum(side**2),1e-20)/max(np.sum(m*m),1e-20)))}
        return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--selftest',action='store_true');p.add_argument('--club');a=p.parse_args()
    if a.selftest:selftest()
    if a.club:print(json.dumps(club(a.club),indent=2,allow_nan=False))
