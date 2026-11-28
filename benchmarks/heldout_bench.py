import json
import numpy as np
import pedalboard as pb
from skell_vst_decompiler.heldout_models import compare_surfaces,detector_models,tail_windows

CONFIGS=[('Compressor','threshold_db',(-36,-8),'ratio',(2,10),{'attack_ms':5,'release_ms':100}),('NoiseGate','threshold_db',(-45,-18),'ratio',(2,10),{}),('PeakFilter','cutoff_frequency_hz',(200,4000),'gain_db',(-9,9),{'q':1.2}),('Delay','feedback',(.1,.8),'mix',(.1,.8),{'delay_seconds':.12}),('Reverb','room_size',(.1,.9),'damping',(.1,.9),{'wet_level':.5,'dry_level':.5}),('Chorus','rate_hz',(.5,4),'depth',(.1,.9),{'mix':.5}),('Limiter','threshold_db',(-24,-3),'release_ms',(20,250),{})]

def main():
    count=0
    def render(name,kw,x,fs,block):
        nonlocal count
        f=getattr(pb,name)(**kw);y=f.process(np.ascontiguousarray(x.T,dtype=np.float32),fs,buffer_size=block,reset=True).T;count+=1
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('invalid render')
        return y.astype(float)
    def rms(x):return float(np.sqrt(np.mean(x*x)))
    def source(fs):
        t=np.arange(fs)/fs;a=np.repeat([.03,.4,.08,.55],fs//4);a=np.pad(a,(0,fs-len(a)),mode='edge');return np.column_stack((a*np.sin(2*np.pi*220*t),a*.7*np.sin(2*np.pi*440*t)))
    train=np.array([(a,b) for a in (-1,0,1) for b in (-1,0,1)]);hold=np.array([(a,b) for a in (-.5,.5) for b in (-.5,.5)])
    out={'pedalboard':pb.__version__,'surface':[],'rate_block':[],'detector':[],'tail':[]}
    for name,a,ar,b,br,fixed in CONFIGS:
        def kw(q):return {**fixed,a:ar[0]+(q[0]+1)/2*(ar[1]-ar[0]),b:br[0]+(q[1]+1)/2*(br[1]-br[0])}
        for fs in (44100,48000,96000):
            x=source(fs); metric=lambda q:20*np.log10(max(rms(render(name,kw(q),x,fs,128)),1e-15)/rms(x))
            m=compare_surfaces(train,[metric(q) for q in train],hold,[metric(q) for q in hold]);out['surface'].append({'processor':name,'rate':fs,'models':m})
            base=render(name,kw((.25,.25)),x,fs,128)
            errs=[]
            for bs in (64,512,1024):
                y=render(name,kw((.25,.25)),x,fs,bs);errs.append({'block':bs,'relative_rms':rms(y-base)/max(rms(base),1e-15)})
            out['rate_block'].append({'processor':name,'rate':fs,'output_gain_db':20*np.log10(max(rms(base),1e-15)/rms(x)),'block_errors':errs})
    # Compare equal-peak, differing-crest waveforms at multiple levels. No claims of actual detector implementation.
    fs=48000;t=np.arange(2*fs)/fs
    for name,kw in [('Compressor',{'threshold_db':-40,'ratio':4,'attack_ms':1,'release_ms':200}),('Limiter',{'threshold_db':-18,'release_ms':100})]:
        p=[];r=[];g=[];mask=[]
        for k,shape in enumerate((np.sin(2*np.pi*200*t),np.sign(np.sin(2*np.pi*200*t)),np.sin(2*np.pi*200*t)**9,np.sin(2*np.pi*200*t)**3)):
            for amp in (.2,.4,.8):
                x=np.column_stack((amp*shape,amp*shape));y=render(name,kw,x,fs,128);x=x[-fs:];y=y[-fs:];p.append(float(np.max(abs(x))));r.append(rms(x));g.append(20*np.log10(max(rms(y),1e-15)/rms(x)));mask.append(k<2)
        out['detector'].append({'processor':name,'models':detector_models(p,r,g,np.array(mask))})
    for name,kw in [('Delay',{'delay_seconds':.12,'feedback':.8,'mix':.8}),('Reverb',{'room_size':.9,'damping':.1,'wet_level':1.,'dry_level':0.})]:
        for fs in (44100,48000,96000):
            x=np.zeros((12*fs+1,2));x[0,0]=.5;y=render(name,kw,x,fs,128);r=tail_windows(y[1:],fs);out['tail'].append({'processor':name,'rate':fs,'last_active_ms':r['last_active_ms'],'right_censored':r['right_censored'],'final_rms_dbfs':r['windows'][-1]['rms_dbfs']})
    out['renders']=count
    with open('results.json','w') as f:json.dump(out,f,indent=2,allow_nan=False)
    print('renders',count)
    for n,*_ in CONFIGS:
        rows=[r for r in out['surface'] if r['processor']==n];print(n, 'heldout RMSE dB',[[round(m['heldout_rmse'],4) for m in r['models']] for r in rows]);rb=[r for r in out['rate_block'] if r['processor']==n];print('gain dB', [round(r['output_gain_db'],4) for r in rb], 'max block error',max(e['relative_rms'] for r in rb for e in r['block_errors']))
    print('detectors',out['detector']);print('tails',out['tail'])
if __name__=='__main__':main()
