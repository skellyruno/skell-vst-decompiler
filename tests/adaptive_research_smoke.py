"""Deterministic original synthetic controls; no vendor audio."""
import json
import numpy as np
from skell_vst_decompiler.adaptive_research import adaptive_pitch,assess_recovery
from skell_vst_decompiler.advanced_dsp import split_pitch,recovery_continuous


def main():
    rng=np.random.default_rng(901);t=np.arange(600)*.01;truth=20+10*t;pitch={}
    for f in (3.5,4,4.7,5,5.7,6,7,7.5,'chirp','none'):
        v=25*np.sin(2*np.pi*(3.5*t+.35*t*t)) if f=='chirp' else np.zeros_like(t) if f=='none' else 25*np.sin(2*np.pi*f*t)
        y=truth+v+rng.normal(0,3,len(t));a,b=split_pitch(y);c,d,e=adaptive_pitch(y)
        def err(x,z):return float(np.sqrt(np.mean((x[150:]-z[150:])**2)))
        pitch[str(f)]={'fixed_center_rmse':err(a,truth),'adaptive_center_rmse':err(c,truth),'fixed_vibrato_rmse':err(b,v),'adaptive_vibrato_rmse':err(d,v),'mean_bank_frequency_hz':float(np.mean(e[150:]))}
    t=np.arange(0.,1200.,10.);counts={}
    for noise in (.03,.1,.3):
        for label,clean in [('single',12*np.exp(-t/137)),('separated_dual',7*np.exp(-t/47)+5*np.exp(-t/483)),('close_dual',7*np.exp(-t/100)+5*np.exp(-t/150))]:
            results=[]
            for seed in range(12):
                y=clean+np.random.default_rng(seed).normal(0,noise,len(t))
                results.append(assess_recovery(recovery_continuous(t,y),noise))
            counts[f'{label}_{noise}']={'trials':len(results),'dual_preferred':results.count('dual_descriptive_preferred')}
    print('SKELL_ADAPTIVE_RESEARCH_RESULT '+json.dumps({'pitch':pitch,'recovery':counts},sort_keys=True))


if __name__=='__main__':main()
