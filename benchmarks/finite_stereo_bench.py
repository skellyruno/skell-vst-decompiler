"""Independent original FIR and Pedalboard fixtures; no commercial execution."""
import argparse,json,time,math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve,resample_poly
import pedalboard as pb
from skell_vst_decompiler.finite_stereo import probes,measure


def main():
    p=argparse.ArgumentParser();p.add_argument('sources',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=[]
    for path in a.sources:
        q,fs=sf.read(path,always_2d=True);source.append((np.repeat(q,2,axis=1) if q.shape[1]==1 else q,fs))
    rng=np.random.default_rng(97);rows=[];noise=[];count=0
    for fs in (44100,48000,96000):
        x,z,tail=probes(fs,6,4096,.04);extra=fs; x=np.pad(x,((0,0),(0,extra),(0,0)));z=np.pad(z,((0,0),(0,extra),(0,0)))
        hold=[z[0]]
        for q,sr in source:
            g=math.gcd(sr,fs);q=resample_poly(q[:sr],fs//g,sr//g,axis=0);q=q[:fs];b=np.zeros_like(z[0]);b[:len(q)]=q*.08/max(np.max(abs(q)),1e-9);hold.append(b)
        hold=np.stack(hold)
        for name,kw in [('Gain',{'gain_db':-3}),('PeakFilter',{'cutoff_frequency_hz':1000,'gain_db':6,'q':1.2}),('Delay',{'delay_seconds':.17,'feedback':.4,'mix':1.}),('Reverb',{'room_size':.5,'wet_level':1,'dry_level':0}),('Distortion',{'drive_db':24}),('Chorus',{'rate_hz':.73,'depth':.6,'mix':1.})]:
            def render(v):
                nonlocal count
                y=pb.__dict__[name](**kw).process(np.ascontiguousarray(v.T,dtype=np.float32),fs,buffer_size=128,reset=True).T;count+=1
                assert y.shape==v.shape and np.isfinite(y).all();return y
            st=time.perf_counter();y=np.stack([render(v) for v in x]);r=measure(x,y,render(x[0]),hold,np.stack([render(v) for v in hold]),fs,tail)
            rows.append(dict(processor=name,rate=fs,elapsed_seconds=time.perf_counter()-st,**r));print(fs,name,r['status'],r['holdout_relative'],r['guard_relative'],flush=True)
        h=np.zeros((fs*3+1,2,2));h[0,0,0]=.5;h[0,1,1]=.6;h[fs*2+37,0,1]=.13;h[fs*2+173,1,0]=-.12
        h[fs:fs+4096]+=rng.normal(0,.0002,(4096,2,2));h[-1,1,1]=.025
        def fir(v):
            out=np.zeros_like(v)
            for o in range(2):
                for i in range(2):out[:,o]+=fftconvolve(v[:,i],h[:,o,i])[:len(v)]
            return out
        y=np.stack([fir(v) for v in x]);hy=np.stack([fir(v) for v in hold]);clean=hy[0]
        for sigma in (1e-6,1e-5):
            noisy=y+rng.normal(0,sigma,y.shape);r=measure(x,noisy,y[0]+rng.normal(0,sigma,y[0].shape),hold[:1],hy[:1],fs,tail)
            impulse=np.zeros_like(x);impulse[0,0,0]=.04;impulse[1,0,1]=.04
            w=np.stack([fir(v) for v in impulse])+rng.normal(0,sigma,impulse.shape)
            estimate=w[:,:len(h),:].transpose(1,2,0)/.04
            pred=np.zeros_like(clean)
            for o in range(2):
                for i in range(2):pred[:,o]+=fftconvolve(hold[0,:,i],estimate[:,o,i])[:len(clean)]
            err=float(np.linalg.norm(pred-clean)/np.linalg.norm(clean));noise.append(dict(rate=fs,noise_rms=sigma,impulse_relative=err,finite_relative=r['holdout_relative'],finite_status=r['status']))
            print('noise',noise[-1],flush=True)
    a.output.write_text(json.dumps(dict(scope='independent fixtures and known FIR; two archived source recordings used only as heldout audio; no vendor capture',fixture_renders=count,results=rows,noise=noise),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
