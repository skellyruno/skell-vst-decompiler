"""Private owned DSP benchmark, no host or true-peak certification."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--music',action='store_true');p.add_argument('--tones',action='store_true');a=p.parse_args();rows=[];tones=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'lab.so';subprocess.run(['g++','-std=c++17','-O3','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_scheduled_recovery.cpp'),str(ROOT/'tests/fixtures/owned_bass_cascade.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');g=dll.scheduled_render;g.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];g.restype=C.c_int;c=dll.cascade_render;c.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];c.restype=C.c_int
        def run(k,fs,x):
            y=np.empty_like(x);t=time.perf_counter_ns();ok=g(k,fs,1,x,y,len(x));ms=(time.perf_counter_ns()-t)/1e6/(len(x)/fs)
            if ok!=1 or not np.isfinite(y).all():raise RuntimeError('guard failure')
            return y,ms
        if a.tones:
            fs=48000;t=np.arange(3*fs+256)/fs
            for hz in (20,30,50,80,100,200,1000,4000):
                for amp in (1.5,3.):
                    x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t),.7*amp*np.sin(2*np.pi*hz*t))));metrics=[]
                    for k in (0,1):
                        y=run(k,fs,x)[0][2*fs:3*fs,0];z=np.abs(np.fft.rfft(y))**2;fund=z[hz];metrics.append({'thd_dbc':db(np.sqrt(z[2*hz::hz].sum()/fund)),'gain_db':db(rms(y)/rms(x[2*fs:3*fs,0]))})
                    tones.append({'hz':hz,'amplitude':amp,'metrics':metrics})
        for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('invalid audio')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            parts=[(0,x)] if not a.music else [(round(f*len(x))-5*fs,x[round(f*len(x))-5*fs:round(f*len(x))+5*fs]) for f in (.25,.5,.75)]
            for offset,v in parts:
                v=np.ascontiguousarray(v);base=np.empty_like(v)
                if c(0,fs,v,base,len(v))!=1 or not np.isfinite(base).all():raise RuntimeError('color failure')
                times=[[],[]];ys=[None,None]
                for rep in range(3):
                    for k in ((0,1) if rep%2==0 else (1,0)):ys[k],ms=run(k,fs,base);times[k].append(ms)
                    if np.any(np.abs(ys[1])+1e-12<np.abs(ys[0])):raise RuntimeError('unexpected attenuation')
                metrics=[{'gain_db':db(rms(y)/rms(base)),'sample_peak_dbfs':db(np.max(np.abs(y))),'estimated16_dbfs':db(np.max(np.abs(resample_poly(y,16,1,axis=0,window=('kaiser',8.6)))))} for y in ys]
                rows.append({'id':item['id'],'offset':offset,'fs':fs,'frames':len(v),'metrics':metrics,'times':times});print(item['id'],offset,flush=True)
    a.output.write_text(json.dumps({'schema':1,'rows':rows,'tones':tones,'limits':'Declared finite four-phase bound, independent 16x peak estimates not certified true peak. Native wall time includes setup; no DAW CPU or listening.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
