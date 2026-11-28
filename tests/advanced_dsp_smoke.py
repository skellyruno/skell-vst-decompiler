"""Reproduce local independent synthetic DSP measurements."""
import json
import numpy as np
from skell_vst_decompiler.advanced_dsp import split_pitch,recovery_continuous,two_tone_imd

def main():
    rng=np.random.default_rng(27);t=np.arange(400)*.01;truth=20+10*t
    pitch={}
    for f in (4,5,6):
        v=25*np.sin(2*np.pi*f*t);y=truth+v+rng.normal(0,3,len(t));c,w=split_pitch(y)
        pitch[str(f)]={'raw_center_rmse':float(np.sqrt(np.mean((y[100:]-truth[100:])**2))),'estimated_center_rmse':float(np.sqrt(np.mean((c[100:]-truth[100:])**2))),'vibrato_rmse':float(np.sqrt(np.mean((w[100:]-v[100:])**2)))}
    t=np.arange(0.,1200.,10.);y=7*np.exp(-t/47)+5*np.exp(-t/483)+rng.normal(0,.015,len(t));r=recovery_continuous(t,y)
    fs=48000;t=np.arange(fs)/fs;x=.25*(np.sin(2*np.pi*1700*t)+np.sin(2*np.pi*2300*t))
    imd={k:two_tone_imd(v,fs) for k,v in [('linear',x),('quadratic',x+.4*x*x),('cubic',x+.4*x*x*x)]}
    print('SKELL_ADVANCED_DSP_RESULT '+json.dumps({'pitch':pitch,'recovery':r,'imd':imd},sort_keys=True))

if __name__=='__main__':main()
