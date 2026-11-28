"""Private original DSP experiments: bass-aware recovery and cascade FIRs."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def spectrum(y,fs,hz):
    n=len(y);z=np.abs(np.fft.rfft(y))**2;z[1:len(z)-(n%2==0)]*=2;k=round(hz*n/fs);fund=z[k];h=z[2*k::k].sum();z[::k]=0
    return [db(np.sqrt(2*fund)/n),db(np.sqrt(h/fund)),db(np.sqrt(z.sum())/n)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--music',action='store_true');p.add_argument('--tones',action='store_true');a=p.parse_args();rows=[];tones=[];limiter=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'lab.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_bass_cascade.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');c=dll.cascade_render;g=dll.bass_guard
        for f in (c,g):f.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        def run(f,k,fs,x):
            y=np.empty_like(x);start=time.perf_counter_ns();ok=f(k,fs,x,y,len(x));ms=(time.perf_counter_ns()-start)/1e6/(len(x)/fs)
            if ok!=1 or not np.isfinite(y).all():raise RuntimeError('render failure')
            return y,ms
        if a.tones:
            for fs in (44100,48000,96000):
                t=np.arange(fs//2+fs//4+256)/fs
                for hz in (1000,3004,11004,17004,20004):
                    for amp in (.1,.5,.9):
                        x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t),amp*np.cos(2*np.pi*hz*t))));tones.append({'fs':fs,'hz':hz,'amp':amp,'metrics':[spectrum(run(c,k,fs,x)[0][fs//2:fs//2+fs//4,0],fs,hz) for k in range(3)]})
            fs=48000;t=np.arange(3*fs+256)/fs
            for hz in (20,30,50,80,100,200,1000,4000):
                for amp in (1.5,3.):
                    x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t),.7*amp*np.sin(2*np.pi*hz*t))));limiter.append({'fs':fs,'hz':hz,'amp':amp,'metrics':[dict(spectrum=spectrum(y[2*fs:3*fs,0],fs,hz),gain_db=db(rms(y[2*fs:3*fs])/rms(x[2*fs:3*fs]))) for y in (run(g,k,fs,x)[0] for k in range(3))]})
        for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('invalid audio')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            parts=[(0,x)] if not a.music else [(round(frac*len(x))-5*fs,x[round(frac*len(x))-5*fs:round(frac*len(x))+5*fs]) for frac in (.25,.5,.75)]
            for offset,v in parts:
                v=np.ascontiguousarray(v);times=[[],[],[]];ys=[None,None,None]
                for rep in range(3):
                    for k in ((0,1,2) if rep%2==0 else (2,1,0)):ys[k],ms=run(c,k,fs,v);times[k].append(ms)
                base=ys[0];colors=[dict(gain_db=db(rms(y)/rms(v)),peak_dbfs=db(np.max(np.abs(y))),matched_difference_db=db(rms(y*rms(base)/rms(y)-base)/rms(base))) for y in ys]
                gs=[run(g,k,fs,base)[0] for k in range(3)];guard=[dict(gain_db=db(rms(y)/rms(base)),sample_peak_dbfs=db(np.max(np.abs(y))),estimated16_dbfs=db(np.max(np.abs(resample_poly(y,16,1,axis=0,window=('kaiser',8.6)))))) for y in gs]
                rows.append(dict(id=item['id'],offset=offset,fs=fs,frames=len(v),color=colors,times=times,guard=guard));print(item['id'],offset,flush=True)
    a.output.write_text(json.dumps(dict(schema=1,rows=rows,color_tones=tones,guard_tones=limiter,limits='Owned native research; 40-sample aligned cascade, 16-sample guard. Harmonic-bin nonharmonic residual omits coincident aliases. Independent 16x estimates not certified true peak. Native wall time includes setup, not host CPU.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
