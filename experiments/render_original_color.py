from pathlib import Path
import json
import numpy as np
from scipy.signal import resample_poly, butter, sosfilt
from scipy.io import wavfile
from skell_vst_decompiler.audio_probe import measure
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('output',type=Path)
out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
results=[]
for fs,tone in [(48000,1000),(48000,17000),(96000,31000)]:
    x=(.5*np.sin(2*np.pi*tone*np.arange(fs*3)/fs)).astype(np.float64)
    stem=f'{fs}_{tone}Hz'
    wavfile.write(out/(stem+'_dry.wav'),fs,x.astype(np.float32))
    for factor in (1,4):
        z=x if factor==1 else resample_poly(x,4,1,window=('kaiser',10.0))
        # Original asymmetric soft saturation experiment, not TVB/VMR emulation.
        y=(np.tanh(3*z+.12)-np.tanh(.12)) / 1.12
        y=sosfilt(butter(1,15,fs=fs*factor,btype='highpass',output='sos'),y)
        if factor!=1:y=resample_poly(y,1,4,window=('kaiser',10.0))
        file=out/(stem+f'_original_{factor}x.wav');wavfile.write(file,fs,y.astype(np.float32))
        r=measure(file,tone,source='Independent offline Skell color candidate, NOT TVB or VMR');r['oversampling_factor']=factor;results.append(r)
(out/'measurements.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
for r in results:
    c=r['channels'][0];print(r['sample_rate'],r['tone_hz'],r['oversampling_factor'],round(c['fundamental_dbfs'],3),c['unambiguous_harmonic_power_dbc'],c['unambiguous_alias_candidate_power_dbc'],round(c['dc'],9))
