"""Private owned DSP benchmark. No vendor execution, host or listening claim."""
import argparse, ctypes as C, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def rms(x):return float(np.sqrt(np.mean(x*x)))
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def peak(x):return db(np.max(np.abs(x)))
def spec(y,fs,hz):
    n=len(y);z=np.abs(np.fft.rfft(y))**2;z[1:len(z)-(n%2==0)]*=2;k=round(hz*n/fs);fund=z[k];h=np.arange(k,len(z),k);harm=z[h[1:]].sum();z[h]=0;z[0]=0
    return [db(np.sqrt(2*fund)/n),db(np.sqrt(harm/fund)),db(np.sqrt(z.sum())/n)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'native.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_adaptive_native.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');f=dll.adaptive_native;f.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int;g=dll.guard_native;g.argtypes=[C.c_double,ptr,ptr,C.c_uint];g.restype=C.c_int;ap=dll.allpass2;ap.argtypes=[C.c_double,ptr,C.c_uint];ap.restype=C.c_int
        def render(k,fs,attack,x):
            y=np.empty_like(x)
            if f(k,fs,attack,x,y,len(x))!=1 or not np.isfinite(y).all():raise RuntimeError('Render failure')
            return y
        def guard(fs,x):
            y=np.empty_like(x)
            if g(fs,x,y,len(x))!=1 or not np.isfinite(y).all():raise RuntimeError('Guard failure')
            if np.max(np.abs(y))>10**(-1/20)+1e-12:raise RuntimeError('Sample ceiling failed')
            return y
        tone=[];release=[];color=[];phase=[];vocals=[];cal={};seen=set()
        for fs in (44100,48000,96000):
            x=np.full((fs//2,2),.5);goal=-db((10**(-18/20)/.5)**.75)
            def onset(k,t):return int(np.flatnonzero(-20*np.log10(render(k,fs,t,x)[:,0]/.5)>=.9*goal)[0]+1)
            target=onset(0,4);lo,hi=4.,12.
            for _ in range(22):
                mid=(lo+hi)/2
                if onset(3,mid)<target:lo=mid
                else:hi=mid
            cal[fs]=hi;assert all(abs(onset(k,hi)-target)<=1 for k in range(1,4))
            t=np.arange(fs*2)/fs
            for hz in (20,30,50,100,200,1000):
                x=np.ascontiguousarray(np.column_stack((.5*np.sin(2*np.pi*hz*t),.25*np.sin(2*np.pi*hz*t))))
                tone.append(dict(fs=fs,hz=hz,metrics=[spec(render(k,fs,hi,x)[-fs:,0],fs,hz) for k in range(4)]))
            for ms in (10,50,250,1000):
                n=round(fs*ms/1000);x=np.full((n+fs*2,2),.025);x[:n]=.5;row=[]
                for k in range(4):
                    y=render(k,fs,hi,x);gr=-20*np.log10(y[n:,0]/.025);hits=np.flatnonzero(gr<=.1*gr[0]);row.append([float(gr[0]),float(hits[0]*1000/fs) if len(hits) else None])
                release.append(dict(fs=fs,burst_ms=ms,metrics=row))
            t=np.arange(fs//2+fs//4+128)/fs
            for hz in (3004,11004,17004,20004):
                for amp in (.1,.5,.9):
                    x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t),amp*np.cos(2*np.pi*hz*t))))
                    ys=[render(k,fs,hi,x) for k in range(4,8)];assert np.array_equal(ys[0],ys[1]);color.append(dict(fs=fs,hz=hz,amp=amp,metrics=[spec(y[40+fs//2:40+fs//2+fs//4,0],fs,hz) for y in (ys[0],ys[2],ys[3])]))
            for frac in (.05,.25,.5,.75,.95):
                h=np.empty(8192);assert ap(frac,h,len(h))==1;D=1+frac;A=-2*(D-2)/(D+1);B=(D-2)*(D-1)/((D+1)*(D+2));c=(1-frac)/(1+frac)
                for hz in (1000,4000,8000,12000,16000,20000):
                    w=2*np.pi*hz/fs;z=np.exp(-1j*w);num=B+A*z+z*z;den=1+A*z+B*z*z;expected=num/den;meas=np.dot(h,np.exp(-1j*w*np.arange(len(h))));err=abs(expected-meas);assert err<1e-10
                    gd=float(np.real((A*z+2*z*z)/num-(A*z+2*B*z*z)/den));old=1+(1-c*c)/(1+c*c+2*c*np.cos(w));phase.append(dict(fs=fs,fraction=frac,hz=hz,complex_error=err,old_group_delay=old,new_group_delay=gd,ideal=D))
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if fs not in cal or not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid audio')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);ys=[render(k,fs,cal[fs],x) for k in range(4)];base=ys[0];lev=[dict(gain_db=db(rms(y)/rms(x)),peak_dbfs=peak(y),matched_peak_dbfs=peak(y*rms(base)/rms(y))) for y in ys]
            pad=np.ascontiguousarray(np.pad(x,((0,40),(0,0))));ys=[render(k,fs,cal[fs],pad)[40:].copy() for k in range(4,8)];assert np.array_equal(ys[0],ys[1]);base=ys[2];fixed=base*10**(-3/20);guarded=guard(fs,base);metrics=[]
            for y in (ys[0],base,ys[3],fixed,guarded):
                metrics.append(dict(gain_db=db(rms(y)/rms(x)),sample_peak_dbfs=peak(y),estimated_peak_dbfs=peak(resample_poly(y,4,1,axis=0)),over_scale=int(np.count_nonzero(np.abs(y)>1)),matched_difference_db=db(rms(y*rms(base)/rms(y)-base)/rms(base))))
            vocals.append(dict(id=item['id'],stage=item['stage'],fs=fs,leveler=lev,color=metrics));print(item['id'],flush=True)
    a.output.write_text(json.dumps(dict(schema=1,calibration=cal,tone=tone,release=release,color=color,phase=phase,vocals=vocals,limits='Owned research only. Estimated peak uses 4x polyphase, not certified true peak. No host or listening approval. Sample guard after fully wet color, not bypass or partial mix.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
