"""Independent fixture state measurements; no installed commercial plugin loading."""
import json
import numpy as np
import pedalboard as pb
from skell_vst_decompiler.heldout_models import recurrence_models


def main():
    out=[]; count=0
    def render(name,kwargs,x,fs):
        nonlocal count
        y=getattr(pb,name)(**kwargs).process(np.ascontiguousarray(x,dtype=np.float32),fs,buffer_size=128,reset=True); count+=1
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('invalid render')
        return y
    for fs in (44100,48000,96000):
        for name,kwargs in [('LowpassFilter',{'cutoff_frequency_hz':1000}),('PeakFilter',{'cutoff_frequency_hz':1500,'gain_db':9,'q':1.2})]:
            arrays=[]
            for amp in (.5,-.2):
                x=np.zeros((2,1024),np.float32);x[0,0]=amp
                arrays.append(render(name,kwargs,x,fs)[0,2:256].astype(float))
            out.append(dict(processor=name,rate=fs,models=recurrence_models(*arrays)))
        # A quiet steady-state control supplies the reference, not a fit to the holdout.
        kwargs={'threshold_db':-20.,'ratio':4.,'attack_ms':5.,'release_ms':150.}
        block=fs//100;t=np.arange(2*fs)/fs; carrier=np.sin(2*np.pi*200*t)
        x=np.tile(.01*carrier,(2,1));y=render('Compressor',kwargs,x,fs)
        target=np.sqrt(np.mean(y[0,-fs:]**2)/np.mean(x[0,-fs:]**2))
        curves=[]
        for amp in (.8,.4):
            x=np.tile(carrier*np.repeat([amp,.01],fs),(2,1));y=render('Compressor',kwargs,x,fs)
            g=np.sqrt(np.mean(y[0,fs:].reshape(-1,block).astype(float)**2,axis=1)/np.mean(x[0,fs:].reshape(-1,block)**2,axis=1))
            curves.append((g-target)[:60])
        out.append(dict(processor='Compressor recovery',rate=fs,models=recurrence_models(*curves)))
    with open('state_results.json','w') as f:json.dump({'renders':count,'observations':out},f,indent=2,allow_nan=False)
    print('renders',count);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
