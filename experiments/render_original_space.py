"""Private audio measurements for the original C++ FDN (not a vendor render)."""
import argparse, json, subprocess, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt


def db(x): return float(20*np.log10(max(float(x),1e-15)))
def rms(x): return float(np.sqrt(np.mean(np.square(x,dtype=np.float64))))
def run(renderer, x, fs, duck):
    with tempfile.TemporaryDirectory() as d:
        a,b=Path(d)/'in.raw',Path(d)/'out.raw';x.astype('<f4').tofile(a)
        subprocess.run([str(Path(renderer).resolve()),str(fs),str(duck),str(a),str(b)],check=True,timeout=30)
        y=np.fromfile(b,dtype='<f4').reshape(-1,2).astype(np.float64)
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('Invalid render')
        return y

def decay_estimate(x,fs,band=None):
    if band:x=sosfilt(butter(3,band,fs=fs,btype='bandpass',output='sos'),x,axis=0)
    energy=np.cumsum(np.sum(x*x,axis=1)[::-1])[::-1]
    ed=10*np.log10(np.maximum(energy/energy[0],1e-30));t=np.arange(len(x))/fs
    m=(ed<=-5)&(ed>=-25)
    if m.sum()<20:raise ValueError('Insufficient decay range')
    slope,intercept=np.polyfit(t[m],ed[m],1);fit=slope*t[m]+intercept
    return {'estimated_rt60_from_t20_s':float(-60/slope),'fit_r2':float(1-np.sum((ed[m]-fit)**2)/np.sum((ed[m]-ed[m].mean())**2))}

def experiment(renderer,source,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    audio,fs=sf.read(source,dtype='float64',always_2d=True)
    if audio.shape[1]==1:audio=np.repeat(audio,2,axis=1)
    if audio.shape[1]!=2 or not np.isfinite(audio).all() or len(audio)<12*fs:raise ValueError('Need finite 12s stereo/mono audio')
    n=12*fs;idx=max(range(len(audio)//n),key=lambda i:rms(audio[i*n:(i+1)*n]));dry=audio[idx*n:(idx+1)*n].copy()
    # Controlled impulse: disable duck so that the decay measurement is linear.
    results={'sample_rate':fs,'excerpt_seconds':12,'source_start_seconds':12*idx,'nominal_low_frequency_decay_s':1.8,'damping_hz':4200,'decay':{},'music':{},'note':'Original offline DSP, not TVB or VMR renders. T20 regression estimate, RMS not LUFS. No subjective listening rating.'}
    for rate in (44100,48000,96000):
        imp=np.zeros((rate*6,2));imp[0,0]=1.;y=run(renderer,imp,rate,0)
        results['decay'][str(rate)]={'broadband':decay_estimate(y,rate),**{name:decay_estimate(y,rate,band) for name,band in [('250Hz',(177,354)),('1kHz',(707,1414)),('4kHz',(2828,5657)),('8kHz',(5657,11314))]}}
        if rate==48000:sf.write(out/'impulse_48k.wav',y,rate,subtype='FLOAT')
    x=np.pad(dry,((0,fs*4),(0,0)));wet=run(renderer,x,fs,0);duck=run(renderer,x,fs,9)
    for name,y in [('unducked',wet),('ducked',duck)]:
        results['music'][name]={'active_wet_rms_dbfs':db(rms(y[:n])),'tail_wet_rms_dbfs':db(rms(y[n:n+fs])),'peak_dbfs':db(np.max(abs(y))),'active_stereo_correlation':float(np.corrcoef(y[:n].T)[0,1])}
        sf.write(out/(name+'_wet.wav'),y,fs,subtype='FLOAT')
    a=x+wet;b=x+duck;b*=rms(a)/max(rms(b),1e-15);scale=min(1,.95/max(np.max(abs(a)),np.max(abs(b))));
    for name,y in [('matched_unducked',a),('matched_ducked',b),('dry',x)]:sf.write(out/(name+'.wav'),y*scale,fs,subtype='FLOAT')
    results['music']['wet_active_change_db']=db(rms(duck[:n])/rms(wet[:n]));results['music']['first_tail_second_change_db']=db(rms(duck[n:n+fs])/rms(wet[n:n+fs]))
    results['music']['matched_rms_difference_db']=db(rms(a)/rms(b));(out/'metrics.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n');return results

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('out');p.add_argument('--renderer',required=True);a=p.parse_args();print(json.dumps(experiment(a.renderer,a.source,a.out),indent=2))
