"""Create analytical golden WAVs for the existing owned gain/delay VST3 only."""
import argparse,json
from pathlib import Path
import numpy as np
import soundfile as sf


def generate(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=False);fs=48000;n=8192
    t=np.arange(n)/fs;x=np.column_stack((.2*np.sin(2*np.pi*997*t),.15*np.cos(2*np.pi*701*t))).astype(np.float32)
    sf.write(root/'input.wav',x,fs,subtype='FLOAT')
    for name,gain,delay,block in [('gain',.25,False,64),('delay',.5,True,512)]:
        y=x*gain
        if delay:
            y=np.zeros_like(x);y[137:]=x[:-137]*gain
        sf.write(root/(name+'.wav'),y,fs,subtype='FLOAT')
        config=dict(name=name,input={'audio':'input.wav'},reference=name+'.wav',state={'parameters':{'Gain':gain,'Creative Delay':float(delay)}},sample_rate=fs,block_size=block,comparison={'sample':2e-6})
        (root/(name+'.json')).write_text(json.dumps(config,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');generate(p.parse_args().output)
