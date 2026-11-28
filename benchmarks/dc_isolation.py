"""Separate nonlinear transfer, FIR sampling and DC-blocker effects offline."""
import argparse,hashlib,json,pathlib
import numpy as np
import soundfile as sf
from scipy.signal import firwin,upfirdn,fftconvolve
from alias_reference import compare,shape
FACTORS=(4,8,32)
def render(x,fs,f,mode):
    n=40*f+1;h=firwin(n,.45/f,fs=1.,window='blackman');q=firwin(n,.475/f,fs=1.,window='blackman')
    v=upfirdn(f*h,x,up=f,axis=0)
    if mode=='nonlinear_dc':v=shape(v,fs,f)
    elif mode=='nonlinear_no_dc':
        v=np.clip(v,-8,8);d=10**.6;v=np.tanh(d*(v+.12*v*v))/np.tanh(d)
    y=fftconvolve(v,q.reshape((-1,)+(1,)*(v.ndim-1)),axes=0)[::f][40:40+len(x)]
    if not np.isfinite(y).all():raise ValueError('nonfinite output')
    return y
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();rows=[];seen=set();modes=('linear','nonlinear_no_dc','nonlinear_dc')
    for item in json.loads(a.manifest.read_text())['inputs']:
        src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if digest!=item['sha256'] or digest in seen:raise ValueError('invalid fingerprint')
        seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
        if len(x)<fs or not np.isfinite(x).all():raise ValueError('invalid audio')
        # Same centered analysis and warmup as the factor-isolation study.
        start=len(x)//2-fs//2;v=x[start:start+fs];metrics={}
        for mode in modes:
            ys=[render(v,fs,f,mode)[fs//4:3*fs//4] for f in FACTORS];metrics[mode]=[compare(y,ys[-1]) for y in ys]
        rows.append(dict(id=item['id'],stage=item['stage'],fs=fs,start_frame=start,metrics=metrics))
    a.output.write_text(json.dumps(dict(schema=1,factors=FACTORS,rows=rows,limits='Offline diagnostic: no-DC output not proposed as a replacement; RMS matched differences from same-mode 32x reference, not pure aliases. Centered excerpts, not full audio.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
