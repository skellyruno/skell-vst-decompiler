"""Reproducible independent built-in fixture benchmark; no commercial plugin loading."""
import itertools,json
import numpy as np
import pedalboard as pb
from skell_vst_decompiler.envelope_research import recovery_models, detector_frequency_models,surfaces3

def main():
    count=0;out={'scope':'Pedalboard built-in fixtures only','version':pb.__version__,'recovery':[],'detector':[],'surfaces':[]}
    def render(name,kw,x,fs):
        nonlocal count
        f=getattr(pb,name)(**kw);y=f.process(np.ascontiguousarray(x.T,dtype=np.float32),fs,buffer_size=128,reset=True).T;count+=1
        if y.shape!=x.shape or not np.isfinite(y).all():raise ValueError('invalid render')
        return y.astype(float)
    def rms(x):return np.sqrt(np.mean(x*x))
    for fs in (44100,48000,96000):
        n=fs//100;t=np.arange(3*fs)/fs;kw={'threshold_db':-26,'ratio':5,'attack_ms':5,'release_ms':150};curves=[];mask=[]
        for f in (80,200,1000,4000):
            c=np.sin(2*np.pi*f*t);x=np.column_stack((.01*c,.01*c));y=render('Compressor',kw,x,fs);q=20*np.log10(rms(y[-fs:])/rms(x[-fs:]))
            for amp in (.2,.4,.6,.8):
                a=np.repeat([amp,.01,.01],fs)*c;x=np.column_stack((a,a));y=render('Compressor',kw,x,fs)
                v=x[fs:fs+100*n].reshape(100,n,2);w=y[fs:fs+100*n].reshape(100,n,2);g=20*np.log10(np.sqrt(np.mean(w*w,axis=(1,2))/np.mean(v*v,axis=(1,2))))
                curves.append(q-g);mask.append(f!=4000 and amp!=.6)
        out['recovery'].append({'rate':fs,'train_curves':sum(mask),'holdout_curves':len(mask)-sum(mask),'models':recovery_models(np.arange(100)*n/fs,curves,np.array(mask))})
        t=np.arange(2*fs)/fs
        for name,kw in [('Compressor',{'threshold_db':-40,'ratio':4,'attack_ms':1,'release_ms':200}),('Limiter',{'threshold_db':-18,'release_ms':100})]:
            p=[];r=[];f=[];g=[];mask=[]
            for hz in (80,200,1000,4000):
                for shape in (1,3,9):
                    c=np.sin(2*np.pi*hz*t)**shape
                    for amp in (.2,.4,.8):
                        x=np.column_stack((amp*c,amp*c));y=render(name,kw,x,fs);x=x[-fs:];y=y[-fs:];p.append(float(np.max(abs(x))));r.append(float(rms(x)));f.append(hz);g.append(float(20*np.log10(max(rms(y),1e-15)/rms(x))));mask.append(hz!=4000 and shape!=3)
            out['detector'].append({'rate':fs,'processor':name,'train_cases':sum(mask),'holdout_cases':len(mask)-sum(mask),'models':detector_frequency_models(p,r,f,g,np.array(mask))})
        t=np.arange(fs)/fs;env=np.repeat([.03,.4,.08,.55],fs//4);env=np.pad(env,(0,fs-len(env)),mode='edge');x=np.column_stack((env*np.sin(2*np.pi*220*t),env*.7*np.sin(2*np.pi*440*t)))
        tr=np.array(list(itertools.product((-1,0,1),repeat=3)));ho=np.array(list(itertools.product((-.5,.5),repeat=3)))
        for name,axes,fixed in [('Compressor',{'threshold_db':(-36,-8),'ratio':(2,10),'release_ms':(30,300)},{'attack_ms':5}),('Delay',{'feedback':(.1,.8),'mix':(.1,.8),'delay_seconds':(.04,.18)},{}),('Reverb',{'room_size':(.1,.9),'damping':(.1,.9),'wet_level':(.1,.8)},{'dry_level':.5})]:
            def score(q):
                kw={**fixed,**{k:lo+(v+1)/2*(hi-lo) for (k,(lo,hi)),v in zip(axes.items(),q)}};return float(20*np.log10(max(rms(render(name,kw,x,fs)),1e-15)/rms(x)))
            out['surfaces'].append({'rate':fs,'processor':name,'controls':list(axes),'models':surfaces3(tr,[score(q) for q in tr],ho,[score(q) for q in ho])})
    out['renders']=count
    with open('envelope_results.json','w') as f:json.dump(out,f,indent=2,allow_nan=False)
    print('renders',count)
    for k in ('recovery','detector','surfaces'):
        for row in out[k]: print(k,row.get('processor','Compressor'),row['rate'],[(m['model'],round(m['heldout_rmse_db'],5)) for m in row['models']])
if __name__=='__main__':main()
