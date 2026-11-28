"""Owned/synthetic fixtures only. Compare broadband observations and noise sensitivity."""
import json,time
import numpy as np
from scipy.signal import fftconvolve
import pedalboard as pb
from skell_vst_decompiler.broadband import measure,stimulus


def render_fir(x,h):
    y=np.zeros_like(x)
    for o in range(2):
        for i in range(2):
            for c in range(2):y[c,:,o]+=fftconvolve(x[c,:,i],h[:,o,i])[:x.shape[1]]
    return y


def main():
    rng=np.random.default_rng(38); results=[]; noise_results=[]; renders=0
    settings=[('Gain',{'gain_db':-3}),('PeakFilter',{'cutoff_frequency_hz':1200,'gain_db':6,'q':1.2}),('HighpassFilter',{'cutoff_frequency_hz':200}),('Delay',{'delay_seconds':.07,'feedback':.2,'mix':1.}),('Distortion',{'drive_db':24}),('Compressor',{'threshold_db':-28,'ratio':6,'attack_ms':2,'release_ms':80}),('Chorus',{'rate_hz':.73,'depth':.6,'mix':1.})]
    for fs in (44100,48000,96000):
        x,z=stimulus(fs,1,.12),stimulus(fs,2,.35)
        for name,kw in settings:
            def run(v):
                nonlocal renders
                y=[]
                for c in v:
                    f=getattr(pb,name)(**kw);out=f.process(np.ascontiguousarray(c.T,dtype=np.float32),fs,buffer_size=128,reset=True).T;renders+=1
                    y.append(out)
                return np.stack(y)
            t=time.perf_counter();r=measure(x,run(x),z,run(z));results.append(dict(processor=name,rate=fs,elapsed_seconds=time.perf_counter()-t,**r))
        # Compare two one-sample impulses against two broadband captures at equal peak,
        # identical output noise RMS; broadband deliberately uses much greater energy.
        n=fs; h=rng.normal(0,.0005,(256,2,2));h[0,0,0]+=.5;h[0,1,1]+=.6;h[12,1,0]+=.1;h[19,0,1]-=.07
        a,b=stimulus(n,4,.35),stimulus(n,5,.35);clean=render_fir(b,h)
        for noise in (1e-5,1e-4,1e-3):
            y=render_fir(a,h)+rng.normal(0,noise,a.shape);r=measure(a,y,b,clean)
            impulse=np.zeros((2,3*n,2));impulse[0,0,0]=.35;impulse[1,0,1]=.35
            w=render_fir(impulse,h)+rng.normal(0,noise,impulse.shape)
            # Known FIR length available ONLY on owned oracle; favor impulse estimator.
            estimate=w[:,:len(h),:].transpose(1,2,0)/.35
            pred=render_fir(b,estimate);error=float(np.linalg.norm(pred[:,n:]-clean[:,n:])/np.linalg.norm(clean[:,n:]))
            noise_results.append(dict(rate=fs,noise_rms=noise,impulse_holdout_relative_rms=error,broadband_holdout_relative_rms=r['heldout_relative_rms'],broadband_status=r['status']))
    report=dict(scope='independent Pedalboard built-in processors and known FIR fixtures; no commercial target',pedalboard=pb.__version__,actual_fixture_renders=renders,results=results,noise_comparisons=noise_results)
    with open('broadband_results.json','w') as f:json.dump(report,f,indent=2,allow_nan=False)
    print('renders',renders)
    for r in results:print(r['processor'],r['rate'],r['status'],round(r['repeat_relative_rms'],6),round(r['heldout_relative_rms'],6),round(r['spectral_relative_disagreement'],6))
    for r in noise_results:print(r)
if __name__=='__main__':main()
