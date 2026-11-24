"""Original synthetic controls only; preserve previous models as comparators."""
import json
import numpy as np
from skell_vst_decompiler.gated_pitch import estimate
from skell_vst_decompiler.adaptive_research import adaptive_pitch
from skell_vst_decompiler.recovery_alternatives import compare_recovery
from skell_vst_decompiler.alias_measure import measure
from skell_vst_decompiler.saturation_reference import saturate


def main():
    rng=np.random.default_rng(500);t=np.arange(600)*.01;truth=20+10*t;pitch={}
    for f in (3.5,4.7,5,5.7,7,7.5,'none','chirp','weak','step'):
        v=25*np.sin(2*np.pi*(3.5*t+.35*t*t)) if f=='chirp' else np.zeros_like(t) if f in ('none','step') else 4*np.sin(2*np.pi*5*t) if f=='weak' else 25*np.sin(2*np.pi*f*t)
        tr=truth+np.where(t>=3,200,0) if f=='step' else truth
        y=tr+v+rng.normal(0,3,len(t));a,b,_=adaptive_pitch(y);c,d,e,s=estimate(y)
        rm=lambda x:float(np.sqrt(np.mean(x*x)))
        pitch[str(f)]={'old_center_rmse':rm(a[150:]-tr[150:]),'new_center_rmse':rm(c[150:]-tr[150:]),'old_startup_rmse':rm(a[:50]-tr[:50]),'new_startup_rmse':rm(c[:50]-tr[:50]),'old_vibrato_rmse':rm(b[150:]-v[150:]),'new_vibrato_rmse':rm(d[150:]-v[150:]),'rate_support_fraction':float(np.mean(np.isfinite(e[150:])))}
    t=np.arange(0.,1200.,10.);recovery={}
    for label,clean in [('dual',7*np.exp(-t/47)+5*np.exp(-t/483)),('stretched',12*np.exp(-(t/180)**.55)),('single',12*np.exp(-t/137))]:
        counts={'trials':12,'old_dual_preferred':0,'new_dual_preferred':0}
        for seed in range(291,303):
            r=compare_recovery(t,clean+np.random.default_rng(seed).normal(0,.03,len(t)),.03)
            counts['old_dual_preferred']+=r['previous_preference']=='dual_descriptive_preferred'
            counts['new_dual_preferred']+=r['preference']=='dual_descriptive_preferred'
            if seed==291:counts['example']=r
        recovery[label]=counts
    alias={}
    for fs in (48000,96000):
        for f in (997,7001,11003):
            x=.8*np.sin(2*np.pi*f*np.arange(fs)/fs)
            a=saturate(x,4.,antialias=False);b=saturate(np.r_[x[-1],x],4.)[1:]
            n=fs*16;hi=saturate(.8*np.sin(2*np.pi*f*np.arange(n)/n),4.,antialias=False)
            spec=np.fft.rfft(hi)[:fs//2+1].copy()/16;spec[-1]=0
            ideal=np.fft.irfft(spec,fs)
            alias[f'{fs}_{f}']={k:measure(y,fs,f) for k,y in [('direct',a),('adaa',b),('ideal_periodic_truncation',ideal)]}
    print('SKELL_RESEARCH_GATES_RESULT '+json.dumps({'pitch':pitch,'recovery':recovery,'alias':alias},sort_keys=True))


if __name__=='__main__':main()
