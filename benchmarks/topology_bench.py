import ctypes,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
import pedalboard as pb
from skell_vst_decompiler.topology_gate import screen,knee_models,release_signature,stereo_intervention,rms,candidate_gate


def main():
    ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');fn=ctypes.CDLL('/tmp/topology_dyn.so').topology_render;fn.argtypes=[ptr,ptr,ctypes.c_uint,ctypes.c_double,ptr,ptr,ctypes.c_int,ctypes.c_int];fn.restype=ctypes.c_int
    rng=np.random.default_rng(818);count=0;report={k:[] for k in ('family','dynamics','knee','recovery','gate','stereo')}
    def render(name,kw,x,fs):
        nonlocal count
        y=getattr(pb,name)(**kw).process(np.ascontiguousarray(x.T,dtype=np.float32),fs,buffer_size=128,reset=True).T.astype(float);count+=1
        assert y.shape==x.shape and np.isfinite(y).all();return y
    def config(s):return dict(zip(('threshold_db','ratio','attack_ms','release_ms'),s))
    for fs in (44100,48000,96000):
        n=fs;half=n//2;t=np.arange(n)/fs
        x=rng.uniform(-.4,.4,(n,2));z=rng.uniform(-.3,.3,(n,2));a=x.copy();a[:half]*=.1;shift=fs//20;shifted=np.zeros_like(x);shifted[shift:]=x[:-shift]
        for name,k in [('Gain',{'gain_db':-3}),('PeakFilter',{'cutoff_frequency_hz':1000,'gain_db':6}),('Clipping',{'threshold_db':-12}),('Distortion',{'drive_db':12}),('Compressor',config([-24,4,5,150])),('NoiseGate',{'threshold_db':-24,'ratio':8,'attack_ms':5,'release_ms':100}),('Delay',{'delay_seconds':.07,'feedback':.3,'mix':1}),('Chorus',{'rate_hz':.73,'depth':.6,'mix':1}),('Reverb',{'room_size':.5,'wet_level':1,'dry_level':0})]:
            y=[render(name,k,v,fs) for v in (x,x,.5*x,z,x+z,a,shifted)]
            res=screen(y[:6],half);shift_error=rms(y[6][shift:]-y[0][:-shift])/max(rms(y[0][:-shift]),1e-12)
            report['family'].append(dict(rate=fs,processor=name,**res,time_shift_relative=shift_error,time_invariant_rejected=shift_error>res['threshold'],candidates=candidate_gate(res,shift_error)))
        # Independent intervention: same quiet channel, other changed from silence to loud.
        t=np.arange(fs*2)/fs;base=.02*np.sin(2*np.pi*1000*t);loud=.8*np.sin(2*np.pi*400*t)
        for name,k in [('Compressor',config([-24,4,5,150])),('NoiseGate',{'threshold_db':-24,'ratio':8,'attack_ms':5,'release_ms':100})]:
            for c in (0,1):
                u=np.zeros((len(t),2));u[:,c]=base;v=u.copy();v[:,1-c]=loud
                a=render(name,k,u,fs)[-fs:];b=render(name,k,v,fs)[-fs:]
                # gate may silence target: use absolute difference if so
                report['stereo'].append(dict(rate=fs,processor=name,channel=c,base_rms=rms(a[:,c]),changed_rms=rms(b[:,c]),difference_rms=rms(a[:,c]-b[:,c])))
        # Constant-level input isolates steady detector law without carrier ripple.
        levels=np.arange(-46.,-7.,2);g=[]
        for level in levels:
            u=np.full((fs//2,1),10**(level/20));v=render('Compressor',config([-24,4,1,40]),u,fs);g.append(20*np.log10(rms(v[-fs//4:])/rms(u[-fs//4:])))
        report['knee'].append(dict(rate=fs,models=knee_models(levels,g,np.arange(len(levels))%3!=1)))
        # Quiet suffix after several high levels, separately measured quiet baseline.
        t=np.arange(2*fs)/fs;c=np.sin(2*np.pi*200*t);u=(.01*c)[:,None];v=render('Compressor',config([-24,4,5,150]),u,fs);baseline=20*np.log10(rms(v[-fs:])/rms(u[-fs:]));curves=[];block=fs//100
        for level in (.2,.4,.8):
            u=(np.repeat([level,.01],fs)*c)[:,None];v=render('Compressor',config([-24,4,5,150]),u,fs);a,b=(q[fs:].reshape(-1,block) for q in (u,v));g=20*np.log10(np.sqrt(np.mean(b*b,axis=1)/np.mean(a*a,axis=1)));curves.append(baseline-g)
        report['recovery'].append(dict(rate=fs,curves=release_signature(curves,block/fs)))
        # Detect persistent history at a matched plateau; finite threshold range only.
        t=np.arange(4*fs)/fs;c=np.sin(2*np.pi*200*t);kw={'threshold_db':-24,'ratio':8,'attack_ms':5,'release_ms':100}
        for lev in (.04,.063,.1):
            outputs=[]
            for prefix in (.005,.6):
                u=(np.r_[np.full(fs,prefix),np.full(3*fs,lev)]*c)[:,None];outputs.append(render('NoiseGate',kw,u,fs))
            a,b=outputs;report['gate'].append(dict(rate=fs,level=lev,early_difference=rms(a[fs:fs+fs//10]-b[fs:fs+fs//10]),late_difference=rms(a[-fs:]-b[-fs:])))
    # Joint fit at 48k, compare feedforward vs feedback and amplitude vs power.
    def observe(fs,s,k):
        t=np.arange(fs//2)/fs;env=np.repeat(rng.choice([.01,.035,.1,.25,.5,.8],10),fs//20);x=np.ascontiguousarray(env*(np.sin(2*np.pi*(200+120*k)*t)+.2*np.sin(2*np.pi*(301+140*k)*t))/1.2);y=render('Compressor',config(s),x[:,None],fs)[:,0];return x,y,fs,np.ascontiguousarray(s,dtype=float)
    train=[observe(48000,s,k) for k,s in enumerate([[-24,4,5,150],[-12,2,2,40],[-32,8,15,300]])];test=[observe(fs,s,k+3) for k,(fs,s) in enumerate([(44100,[-27,6,7,110]),(48000,[-15,2.5,15,240]),(96000,[-32,3.5,3,65])])]
    def predict(row,p,fb,power):
        x,y,fs,s=row;out=np.empty_like(x);assert fn(x,out,len(x),fs,s,np.ascontiguousarray(p),fb,power);return out
    def err(rows,p,fb,power):return np.concatenate([(predict(row,p,fb,power)-row[1])[::8] for row in rows])
    for fb in (0,1):
        for power in (0,1):
            f=least_squares(lambda p:err(train,p,fb,power),[0.,1.,.16,.16],bounds=([-10,.2,.01,.01],[10,2,2,2]),max_nfev=80)
            report['dynamics'].append(dict(feedback=bool(fb),power=bool(power),converged=bool(f.success),train_rms=rms(err(train,f.x,fb,power)),holdout_rms=rms(err(test,f.x,fb,power)),parameters=f.x.tolist()))
    report['renders']=count;report['scope']='Independent Pedalboard built-in fixture only; no commercial matching';Path('results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print('renders',count)
    for k in ('dynamics','knee','recovery','gate','stereo'):print(k,report[k])
    print('family',[(r['processor'],r['rate'],r['rejected'],r['time_invariant_rejected']) for r in report['family']])
if __name__=='__main__':main()
