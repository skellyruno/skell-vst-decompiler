"""Offline exact-arithmetic multirate lifting of the existing 5 Hz DC blocker."""
import argparse,hashlib,json,pathlib
import numpy as np
import soundfile as sf
from scipy.signal import firwin,upfirdn,lfilter,fftconvolve
from alias_reference import db,rms

def paired(x,fs,factor):
    n=40*factor+1;h=firwin(n,.45/factor,fs=1.,window='blackman');q=firwin(n,.475/factor,fs=1.,window='blackman')
    u=np.clip(upfirdn(factor*h,x,up=factor,axis=0),-8,8);d=10**.6;s=np.tanh(d*(u+.12*u*u))/np.tanh(d)
    p=np.exp(-2*np.pi*5/(factor*fs));v=lfilter([1,-1],[1,-p],s,axis=0)
    old=upfirdn(q,v,down=factor,axis=0)[:40+len(x)]
    # (1-p*z^-1)*sum_{k=0}^{M-1}p^k*z^-k = 1-p^M*z^-M.
    numerator=np.convolve([1.,-1.],p**np.arange(factor));combined=np.convolve(q,numerator)
    down=upfirdn(combined,s,down=factor,axis=0)[:40+len(x)]
    new=lfilter([1.],[1.,-p**factor],down,axis=0)
    if old.shape!=new.shape or not np.isfinite(new).all():raise RuntimeError('invalid render')
    error=float(np.max(np.abs(old-new)))
    if error>2e-10:raise RuntimeError('lifted identity mismatch')
    return {'max_abs_error':error,'relative_error_db':db(rms(old-new)/max(rms(old),1e-15)),'fir_taps':len(q),'combined_taps':len(combined)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();tones=[];audio=[];seen=set();rng=np.random.default_rng(713)
    for fs in (8000,44100,48000,96000,192000,384000):
        t=np.arange(8192)/fs
        for x in (np.eye(1,8192,0).ravel(),np.full(8192,.5),.8*np.sin(2*np.pi*20*t),rng.uniform(-1,1,8192)):
            for f in (2,4,8,16):tones.append(dict(fs=fs,factor=f,metrics=paired(np.column_stack((x,-.7*x)),fs,f)))
    for item in json.loads(a.manifest.read_text())['inputs']:
        src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if digest!=item['sha256'] or digest in seen:raise ValueError('invalid fingerprint')
        seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
        if len(x)<fs or not np.isfinite(x).all():raise ValueError('invalid audio')
        positions=(.25,.5,.75) if item['stage']=='mixed_music' else (.5,)
        for frac in positions:
            start=round(frac*len(x))-fs//2;v=x[start:start+fs]
            audio.append(dict(id=item['id'],stage=item['stage'],fs=fs,start_frame=start,metrics=[dict(factor=f,**paired(v,fs,f)) for f in (4,8)]))
    a.output.write_text(json.dumps(dict(schema=1,tones=tones,audio=audio,limits='Exact arithmetic transfer identity for zero initial state, measured floating-point tolerance only. Not a native implementation or speed claim; FIR symmetry is lost and tail/automation/state migration remain untested. All comparisons include initial transient and alignment prefix.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
