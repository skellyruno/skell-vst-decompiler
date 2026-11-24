"""Seeded independent controls and periodic reference; no vendor input."""
import json
import numpy as np
from scipy.signal import lfilter
from skell_vst_decompiler.gated_pitch import estimate as baseline
from skell_vst_decompiler.motion_pitch import estimate as challenger
from skell_vst_decompiler.coloration_compare import compare,oversampled
from skell_vst_decompiler.saturation_reference import saturate


def main():
    pitch={}
    for name in ('white','ar','glide','slow','step','weak','strong','offgrid','chirp','mixed'):
        rows=[]
        for seed in (101,207,309):
            rng=np.random.default_rng(seed);t=np.arange(600)*.01;truth=20+10*t
            noise=rng.normal(0,3,len(t));v=np.zeros_like(t)
            if name=='ar':
                noise=lfilter([1],[1,-.85],noise);noise*=3/np.std(noise)
            if name=='glide':truth+=30*np.tanh((t-3)*4)
            if name in ('slow','mixed'):truth+=25*np.sin(2*np.pi*1.3*t)
            if name=='step':truth+=100*(t>=3)
            if name=='weak':v=4*np.sin(2*np.pi*4.7*t)
            if name=='strong':v=25*np.sin(2*np.pi*5*t)
            if name in ('offgrid','mixed'):v=25*np.sin(2*np.pi*4.7*t)
            if name=='chirp':v=25*np.sin(2*np.pi*(3.5*t+.35*t*t))
            row=[]
            for fun in (baseline,challenger):
                c,w,f,s=fun(truth+v+noise)
                row.extend([np.sqrt(np.mean((c[150:]-truth[150:])**2)),np.mean(np.isfinite(f[150:]))])
            rows.append(row)
        pitch[name]=dict(zip(('baseline_center_rmse','baseline_rate_support','challenger_center_rmse','challenger_rate_support'),map(float,np.mean(rows,axis=0))))
    color={}
    for fs in (48000,96000):
        for f in (997,7001,11003):
            x=.8*np.sin(2*np.pi*f*np.arange(fs)/fs);n=fs*16
            hi=saturate(.8*np.sin(2*np.pi*f*np.arange(n)/n),4,antialias=False)
            spec=np.fft.rfft(hi)[:fs//2+1]/16;spec[-1]=0;ref=np.fft.irfft(spec,fs)
            color[f'{fs}_{f}']={k:compare(y,ref,fs,f) for k,y in (
                ('direct',saturate(x,4,antialias=False)),('adaa',saturate(np.r_[x[-1],x],4)[1:]),
                ('2x',oversampled(x,4,2)),('4x',oversampled(x,4,4)),('8x',oversampled(x,4,8)))}
    print('SKELL_MOTION_COLOR_RESULT '+json.dumps({'pitch':pitch,'coloration':color},sort_keys=True))


if __name__=='__main__':main()
