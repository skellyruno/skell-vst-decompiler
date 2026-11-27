"""Same-filter oversampling factor audit, using an independent offline chain."""
import argparse,hashlib,json,pathlib
import numpy as np
import soundfile as sf
from scipy.signal import firwin,upfirdn,fftconvolve
from alias_reference import shape,compare,render
FACTORS=(4,8,16,32)
def fast_render(x,fs,factor):
    span=40;n=factor*span+1
    h=firwin(n,.45/factor,fs=1.,window='blackman');q=firwin(n,.475/factor,fs=1.,window='blackman')
    v=shape(upfirdn(factor*h,x,up=factor,axis=0),fs,factor)
    y=fftconvolve(v,q.reshape((-1,)+(1,)*(v.ndim-1)),axes=0)[::factor][span:span+len(x)]
    if not np.isfinite(y).all():raise ValueError('nonfinite render')
    return y
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();tones=[];audio=[];seen=set()
    rng=np.random.default_rng(61);errors=[]
    for factor in FACTORS:
        x=rng.uniform(-1,1,(2048,2));err=float(np.max(np.abs(fast_render(x,48000,factor)-render(x,48000,factor,40,.45,.475))))
        if err>2e-12:raise RuntimeError('FFT convolution oracle mismatch')
        errors.append(err)
    def evaluate(x,fs,sl):
        ys=[fast_render(x,fs,f)[sl] for f in FACTORS];return [compare(y,ys[-1]) for y in ys]
    for fs in (44100,48000,96000):
        t=np.arange(fs//4+fs//8+512)/fs
        for freqs in ((1000,),(7008,),(17008,),(1000,11008),(7008,11008),(15008,17008)):
            for amp in (.1,.5,.9):
                x=sum(amp/len(freqs)*np.sin(2*np.pi*f*t) for f in freqs)
                tones.append(dict(fs=fs,frequencies=freqs,amp=amp,metrics=evaluate(x,fs,slice(fs//4,fs//4+fs//8))))
    for item in json.loads(a.manifest.read_text())['inputs']:
        src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
        if digest!=item['sha256'] or digest in seen:raise ValueError('invalid fingerprint')
        seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
        if len(x)<fs or not np.isfinite(x).all():raise ValueError('invalid audio')
        positions=(.25,.5,.75) if item['stage']=='mixed_music' else (.5,)
        for frac in positions:
            start=round(frac*len(x))-fs//2;v=x[start:start+fs]
            audio.append(dict(id=item['id'],stage=item['stage'],fs=fs,start_frame=start,metrics=evaluate(v,fs,slice(fs//4,3*fs//4))))
    a.output.write_text(json.dumps(dict(schema=1,factors=FACTORS,fft_oracle_max_error=errors,tones=tones,audio=audio,limits='Fixed normalized FIR cutoffs/window/span, not exactly identical sampled coefficients or DC pole across factors. Reference error includes residual alias, numerical quadrature and tiny filter differences; not a pure alias metric. Offline no CPU or listening claim.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
