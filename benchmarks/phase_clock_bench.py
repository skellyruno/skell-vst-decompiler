"""Independent Pedalboard fixture observations; no commercial plugins loaded."""
import argparse,json,math
from pathlib import Path
import numpy as np
import pedalboard as pb
import soundfile as sf
from scipy.signal import resample_poly
from experiments.phase_clock import load_clock,interpolate,infer_delay


def main():
    p=argparse.ArgumentParser();p.add_argument('library');p.add_argument('sources',nargs=3,type=Path);p.add_argument('--output',required=True);a=p.parse_args()
    clock=load_clock(a.library);rng=np.random.default_rng(744);rows=[];tracks=[];holds=[];neg=[];renders=0
    def render(x,fs,center,depth,rate,block,feedback=0):
        nonlocal renders
        renders+=1
        return pb.Chorus(rate_hz=rate,depth=depth,centre_delay_ms=center,feedback=feedback,mix=1).process(np.ascontiguousarray(x[None,:],dtype=np.float32),fs,buffer_size=block,reset=True)[0]
    def err(x,y):return float(np.linalg.norm(x-y)/max(np.linalg.norm(y),1e-12))
    for fs in (44100,48000,96000):
        n=2*fs;X=rng.uniform(-.6,.6,(8,n)).astype(np.float32);Y=np.stack([render(x,fs,7.4,.3,.91,128) for x in X]);ideal=clock(n,fs,7.4,3.,.91,False);single=clock(n,fs,7.4,3.,.91,True)
        # Earlier fitted sinusoid supplies local search center. It does not train the new clock.
        t=np.arange(n)/fs;guess=(7.399393+3.000137*np.sin(2*np.pi*.910416*t-3.142167))*fs/1000
        d,e=infer_delay(X,Y,guess);mask=(t>.05)&(e<1e-5)
        if np.mean(mask)<.9:raise ValueError('insufficient verified interpolation observations')
        tracks.append(dict(rate=fs,valid_fraction=float(np.mean(mask)),interpolation_rms=float(np.sqrt(np.mean(e[mask]**2))),ideal_delay_rmse_samples=float(np.sqrt(np.mean((d[mask]-ideal[mask])**2))),single_delay_rmse_samples=float(np.sqrt(np.mean((d[mask]-single[mask])**2)))))
    # Three configurations including two unseen controls; longer histories and fresh host reset per render.
    for fs in (44100,48000,96000,192000):
        for center,depth,rate in ((7.4,.3,.91),(13.,.45,1.7),(4.,.15,.17)):
            n=10*fs;x=rng.uniform(-.6,.6,n).astype(np.float32);d0=clock(n,fs,center,10*depth,rate,False);d1=clock(n,fs,center,10*depth,rate,True);v0=interpolate(x,d0);v1=interpolate(x,d1);base=None
            for block in (64,128,512,1024):
                y=render(x,fs,center,depth,rate,block)
                if base is None:base=y.copy()
                rows.append(dict(rate=fs,center_ms=center,depth=depth,lfo_hz=rate,block=block,seconds=10,ideal_error=err(v0,y),single_error=err(v1,y),block_error=float(np.max(abs(y-base)))))
        for i,path in enumerate(a.sources):
            x,sr=sf.read(path,always_2d=True);g=math.gcd(sr,fs);x=resample_poly(x[:2*sr,0],fs//g,sr//g).astype(np.float32);center,depth,rate=((7.4,.3,.91),(13.,.45,1.7),(4.,.15,.17))[i]
            y=render(x,fs,center,depth,rate,128);v0=interpolate(x,clock(len(x),fs,center,10*depth,rate,False));v1=interpolate(x,clock(len(x),fs,center,10*depth,rate,True));holds.append(dict(rate=fs,source=i,ideal_error=err(v0,y),single_error=err(v1,y)))
        x=rng.uniform(-.6,.6,fs).astype(np.float32);y=render(x,fs,7.4,.3,.91,128,.5);v=interpolate(x,clock(len(x),fs,7.4,3.,.91,True));neg.append(dict(rate=fs,feedback=.5,relative_error=err(v,y)))
        print(fs,'completed',flush=True)
    report=dict(scope='independent Pedalboard built-in Chorus; isolated wet zero-feedback observations; negative feedback control',renders=renders,track=tracks,long_history=rows,recorded_holdout=holds,negative=neg);Path(a.output).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('renders',renders,'track',tracks,'long max ideal/single/block',max(r['ideal_error'] for r in rows),max(r['single_error'] for r in rows),max(r['block_error'] for r in rows),'holdout max',max(r['single_error'] for r in holds),'neg',neg,flush=True)
if __name__=='__main__':main()
