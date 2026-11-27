"""Private owned DSP comparisons. Keep manifest, audio and per-input rows local."""
import argparse, ctypes as C, hashlib, json, pathlib, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def rms(x):return float(np.sqrt(np.mean(x*x)))
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def peak(x):return float(np.max(np.abs(x)))
def spectrum(y,fs,hz):
    z=np.abs(np.fft.rfft(y))**2; k=round(hz*len(y)/fs)
    z[1:len(z)-(len(y)%2==0)]*=2; fund=z[k];harm=np.arange(k,len(z),k);dist=z[harm[1:]].sum();z[0]=0;z[harm]=0
    return {'fundamental':float(np.sqrt(2*fund)/len(y)),'thd_dbc':db(np.sqrt(dist/fund)),'residual_dbc':db(np.sqrt(z.sum()/fund))}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--delay-include',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--listen-dir',type=pathlib.Path);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--tones',action='store_true');a=p.parse_args()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'tracks.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(a.delay_include.resolve()),str(ROOT/'tests/fixtures/owned_refinement_tracks.cpp'),'-o',str(lib)],check=True)
        f=C.CDLL(str(lib)).render_tracks;ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');f.argtypes=[C.c_int,C.c_double,C.c_double,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        def render(k,fs,param,wet,x):
            y=np.empty_like(x)
            if f(k,fs,param,wet,x,y,len(x))!=1 or not np.isfinite(y).all():raise RuntimeError('Render failed')
            return y
        tone=[];step=[];saturation=[];vocal=[];seen=set()
        for fs in ((44100,48000,96000) if a.tones else ()):
            x=np.full((fs,2),.5);ys=[render(k,fs,4,1,x) for k in (0,1,2)];goal=-db((10**(-18/20)/.5)**.75)
            step.append({'fs':fs,'t90_ms':[float((np.flatnonzero(-20*np.log10(y[:,0]/.5)>=.9*goal)[0]+1)*1000/fs) for y in ys]})
            t=np.arange(fs*2)/fs
            for hz in (50,100,200,1000):
                x=np.ascontiguousarray(np.column_stack((.5*np.sin(2*np.pi*hz*t),.25*np.sin(2*np.pi*hz*t))))
                ys=[render(k,fs,4,1,x)[-fs:,0] for k in (0,1,2)]
                tone.append({'fs':fs,'hz':hz,'metrics':[spectrum(y,fs,hz) for y in ys]})
            t=np.arange(fs+fs//4)/fs
            for hz in (1000,8000,12000,16000,20000):
                for amp in (.01,.1,.5,.9):
                    x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t),amp*np.cos(2*np.pi*hz*t))))
                    base=render(3,fs,0,1,x);zero=render(4,fs,0,1,x)
                    if not np.array_equal(base,zero):raise RuntimeError('Zero correction parity')
                    ys=[base]+[render(4,fs,c,1,x) for c in (.25,.5,1)]
                    saturation.append({'fs':fs,'hz':hz,'amp':amp,'metrics':[spectrum(y[-fs//4:,0],fs,hz) for y in ys]})
        for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);row={'id':item['id'],'stage':item['stage'],'fs':fs,'frames':len(x)}
            def metrics(ys):
                return [{'gain_db':db(rms(y)/rms(x)),'peak_dbfs':db(peak(y)),'over_scale':int(np.count_nonzero(np.abs(y)>1)),'matched_difference_db':db(rms(y*rms(ys[0])/rms(y)-ys[0])/rms(ys[0]))} for y in ys]
            row['leveler']=metrics([render(k,fs,4,1,x) for k in (0,1,2)])
            pad=np.ascontiguousarray(np.pad(x,((0,40),(0,0))));base=render(3,fs,0,1,pad);zero=render(4,fs,0,1,pad)
            if not np.array_equal(base,zero):raise RuntimeError('Vocal zero correction parity')
            row['color']=metrics([base[40:]]+[render(4,fs,c,1,pad)[40:] for c in (.25,.5,1)])
            row['presence']={};listen={'original':x}
            for w in (.5,1):
                ys=[render(k,fs,0,w,x) for k in (5,6)];row['presence'][str(w)]=metrics(ys)
                for label,y in zip(('legacy','complementary'),ys):listen[f'{label}_{int(w*100)}']=y*rms(x)/rms(y)
            # Isolated six echoes of a high-energy 125 ms vocal segment.
            n=round(.125*fs);hop=max(1,n//2);start=max(range(0,max(1,len(x)-n+1),hop),key=lambda i:rms(x[i:i+n]));seg=x[start:start+n];D=round(.25*fs);inp=np.ascontiguousarray(np.pad(seg,((0,7*D-len(seg)),(0,0))))
            ys=[render(k,fs,D+.5,1,inp) for k in (7,8)];row['delay']=[{'peak_dbfs':db(peak(y)),'echo_rms_db':[db(rms(y[e*D:e*D+n+64])) for e in range(1,7)]} for y in ys]
            if a.listen_dir and item['stage'] in ('dry_archive_labeled','processed_module_input'):
                folder=a.listen_dir/item['id'];folder.mkdir(parents=True,exist_ok=True)
                gain=min(1.,10**(-1/20)/max(peak(resample_poly(v,4,1,axis=0)) for v in listen.values()))
                for label,v in listen.items():sf.write(folder/(label+'.flac'),gain*v,fs,subtype='PCM_24')
            vocal.append(row);print(item['id'],flush=True)
        a.output.write_text(json.dumps({'schema':1,'step':step,'tones':tone,'saturation':saturation,'vocals':vocal,'limits':'Fixed controls, original owned code only. Sample peaks, nonharmonic residual omits coincident aliases. Listening files RMS matched with common group headroom. No listening approval or production integration.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
