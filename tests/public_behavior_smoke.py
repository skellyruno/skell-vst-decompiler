"""Synthetic verification of public-behavior-inspired original research controls."""
import json
import numpy as np
from skell_vst_decompiler.pitch_control import RetuneControl
from skell_vst_decompiler.topology_probes import stereo_cases,topology_levels,harmonic_levels


def main():
    fs=48000;t=np.arange(fs)/fs;phase=2*np.pi*1000*t
    x=.6*np.sin(phase)
    colors={name:harmonic_levels(y,fs,1000) for name,y in [
        ('linear',x),('quadratic_control',x+.2*x*x),('odd_tanh_control',np.tanh(2*x))]}
    pitch={}
    for sustain in (0,150):
        c=RetuneControl(retune_ms=0,sustain_ms=sustain)
        residual=[]
        for i in range(200):
            cents=25*np.sin(2*np.pi*5*i*.01)
            _,offset=c.step(440*2**(cents/1200),1.,10.)
            residual.append(cents+offset)
        pitch[str(sustain)]={'initial_100ms_residual_rms_cents':float(np.sqrt(np.mean(np.square(residual[:10])))),
             'sustained_residual_rms_cents':float(np.sqrt(np.mean(np.square(residual[100:]))))}
    print('SKELL_PUBLIC_BEHAVIOR_RESULT '+json.dumps({'stereo':{k:topology_levels(v) for k,v in stereo_cases().items()},
          'harmonics':colors,'sustained_retune':pitch,'scope':'original synthetic controls only'},sort_keys=True))

if __name__=='__main__':main()
