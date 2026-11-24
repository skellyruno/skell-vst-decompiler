"""Synthetic model-identification controls and moving pitch comparison."""
import json
import numpy as np
from skell_vst_decompiler.behavior_models import recovery_models,detector_probes,detector_levels
from skell_vst_decompiler.pitch_trajectory import trajectory_cases,score
from skell_vst_decompiler.pitch_reference import estimate as yin
from skell_vst_decompiler.historical_pitch_reference import estimate as historical


def main():
    t=np.arange(0.,1000.,10.);grid=np.geomspace(5.,2000.,32)
    recovery={name:recovery_models(t,y) for name,y in [
        ('single_control',12*np.exp(-t/grid[16])),
        ('dual_control',8*np.exp(-t/grid[10])+4*np.exp(-t/grid[23]))]}
    fs=48000;cases=trajectory_cases(fs)
    pitch={name:{k:score(fn,*v,fs) for k,v in cases.items()} for name,fn in [
        ('yin_fft',lambda x,s:yin(x,s,backend='fft')),('two_period',historical)]}
    print('SKELL_BEHAVIOR_RESULT '+json.dumps({'recovery':recovery,
        'detector_probes':{k:detector_levels(v) for k,v in detector_probes().items()},
        'pitch_trajectory':pitch,'scope':'synthetic original controls only'},sort_keys=True))

if __name__=='__main__':main()
