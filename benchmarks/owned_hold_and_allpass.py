"""Independent owned DSP: matched attack, crest hold, and allpass phase limits.
Private manifest and per-recording measurements must stay local.
"""
import argparse, ctypes as C, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
ROOT=pathlib.Path(__file__).resolve().parents[1]
HOLDS=(0,2,5,8,12,20)
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def phase_audit():
    rows=[];max_err=0.
    for fs in (44100,48000,96000):
        for fraction in (.05,.25,.5,.75,.95):
            a=(1-fraction)/(1+fraction);h=np.empty(4096);h[0]=a;h[1]=1-a*a
            for n in range(2,len(h)):h[n]=-a*h[n-1]
            for hz in (1000,4000,8000,12000,16000,20000):
                w=2*np.pi*hz/fs;z=np.exp(-1j*w);H=(a+z)/(1+a*z)
                measured=np.dot(h,np.exp(-1j*w*np.arange(len(h))))
                error=abs(measured-H);max_err=max(max_err,error)
                if error>1e-10:raise RuntimeError('Allpass impulse oracle mismatch')
                gd=(1-a*a)/(1+a*a+2*a*np.cos(w))
                rows.append({'fs':fs,'fraction':fraction,'hz':hz,'magnitude_db':db(abs(measured)),'group_delay_samples':float(gd),'excess_after_8_passes_samples':float(8*(gd-fraction))})
    return {'rows':rows,'max_complex_error':max_err,'limits':'Ideal fixed first-order allpass model, not integrated delay or time modulation.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'hold.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_hold_sweep.cpp'),'-o',str(lib)],check=True)
        f=C.CDLL(str(lib)).hold_sweep;ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');f.argtypes=[C.c_int,C.c_double,C.c_double,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        def render(mode,fs,attack,hold,x):
            y=np.empty_like(x)
            if f(mode,fs,attack,hold,x,y,len(x))!=1 or not np.isfinite(y).all():raise RuntimeError('Render failed')
            return y
        calibration=[];tone=[];release=[];vocals=[];seen=set();tuned={}
        for fs in (44100,48000,96000):
            step=np.full((fs//2,2),.5);goal=-db((10**(-18/20)/.5)**.75)
            def onset(mode,attack,hold):
                y=render(mode,fs,attack,hold,step);return int(np.flatnonzero(-20*np.log10(y[:,0]/.5)>=.9*goal)[0]+1)
            target=onset(0,4,0);lo,hi=4.,12.
            for _ in range(22):
                mid=(lo+hi)/2
                if onset(1,mid,0)<target:lo=mid
                else:hi=mid
            tuned[fs]=hi
            ts=[onset(1,hi,h) for h in HOLDS]
            if any(abs(t-target)>1 for t in ts):raise RuntimeError('Calibration mismatch')
            calibration.append({'fs':fs,'attack_ms':hi,'baseline_t90_samples':target,'candidate_t90_samples':ts})
            configs=[(0,4,0)]+[(1,hi,h) for h in HOLDS]
            for hz in (20,30,50,80,100,200,1000):
                t=np.arange(fs*2)/fs;x=np.ascontiguousarray(np.column_stack((.5*np.sin(2*np.pi*hz*t),.25*np.sin(2*np.pi*hz*t))))
                values=[]
                for mode,attack,hold in configs:
                    y=render(mode,fs,attack,hold,x)[-fs:,0];z=np.abs(np.fft.rfft(y))**2;fund=z[hz];values.append({'thd_dbc':db(np.sqrt(z[2*hz::hz].sum()/fund)),'gain_db':db(rms(y)/rms(x[-fs:,0]))})
                tone.append({'fs':fs,'hz':hz,'metrics':values})
            for duration in (10,50,250,1000):
                n=round(duration*fs/1000);x=np.full((n+2*fs,2),.025);x[:n]=.5;values=[]
                for mode,attack,hold in configs:
                    y=render(mode,fs,attack,hold,x);g=-20*np.log10(y[n:,0]/.025);hits=np.flatnonzero(g<=.1*g[0]);values.append({'initial_gr_db':float(g[0]),'recovery_ms':float(hits[0]*1000/fs) if len(hits) else None})
                release.append({'fs':fs,'burst_ms':duration,'metrics':values})
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if fs not in tuned or not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);base=render(0,fs,4,0,x);values=[]
            for mode,attack,hold in [(0,4,0)]+[(1,tuned[fs],h) for h in HOLDS]:
                y=base if mode==0 else render(mode,fs,attack,hold,x);matched=y*rms(base)/rms(y)
                values.append({'gain_db':db(rms(y)/rms(x)),'peak_dbfs':db(np.max(np.abs(y))),'matched_peak_dbfs':db(np.max(np.abs(matched))),'over_scale_samples':int(np.count_nonzero(np.abs(y)>1)),'matched_difference_db':db(rms(matched-base)/rms(base))})
            vocals.append({'id':item['id'],'stage':item['stage'],'fs':fs,'metrics':values})
    a.output.write_text(json.dumps({'schema':1,'holds_ms':HOLDS,'calibration':calibration,'tone':tone,'release':release,'vocals':vocals,'allpass':phase_audit(),'limits':'Matched t90 for one step amplitude, not all dynamics. Harmonic-bin distortion and sample peaks only. No listening or host validation.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
