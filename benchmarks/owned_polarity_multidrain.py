"""Private paired comparison of owned limiters and bounded delay scheduling."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time,statistics
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def peak(x):return db(np.max(np.abs(x)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--music',action='store_true');a=p.parse_args();rows=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'lab.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_polarity_multidrain.cpp'),str(ROOT/'tests/fixtures/owned_transition_peak.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');up=np.ctypeslib.ndpointer(dtype=np.uint32,flags='C_CONTIGUOUS');g=dll.polarity_render;g.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];g.restype=C.c_int;c=dll.selective_color;c.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];c.restype=C.c_int;dr=dll.multibank_render;dr.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint,C.c_uint,ptr,up];dr.restype=C.c_int
        def guard(k,fs,release,x):
            y=np.empty_like(x)
            if g(k,fs,release,x,y,len(x))!=1 or not np.isfinite(y).all():raise RuntimeError('Guard failed')
            return y
        def metrics(y,base):return {'gain_db':db(rms(y)/rms(base)),'sample_peak_dbfs':peak(y),'estimated16_peak_dbfs':peak(resample_poly(y,16,1,axis=0,window=('kaiser',8.6)))}
        for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid audio')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            parts=[(0,x)] if not a.music else [(round(frac*len(x))-5*fs,x[round(frac*len(x))-5*fs:round(frac*len(x))+5*fs]) for frac in (.25,.5,.75)]
            for offset,v in parts:
                v=np.ascontiguousarray(v);base=np.empty_like(v)
                if c(1,fs,v,base,len(v))!=1 or not np.isfinite(base).all():raise RuntimeError('Color failed')
                vals=[]
                for release in (1.,60.,1000.):
                    ys=[guard(k,fs,release,base) for k in (0,1)];vals.append({'release_ms':release,'metrics':[metrics(y,base) for y in ys]})
                # Alternating paired timings, same input, output allocated before timer.
                times=[[],[]];buf=np.empty_like(base)
                for rep in range(3):
                    for k in ((0,1) if rep%2==0 else (1,0)):
                        start=time.perf_counter_ns();ok=g(k,fs,60,base,buf,len(base));end=time.perf_counter_ns()
                        if ok!=1 or not np.isfinite(buf).all():raise RuntimeError('Timing failed')
                        times[k].append((end-start)/1e6/(len(base)/fs))
                delay=[];n=len(v);xpad=np.ascontiguousarray(np.pad(v,((0,fs//4),(0,0))));interval=round(.25*fs)
                for k in (0,1):
                    y=np.empty_like(xpad);ev=np.empty(len(xpad)//interval+1);stats=np.zeros(4,dtype=np.uint32)
                    if dr(k,fs,xpad,y,len(xpad),interval,ev,stats)!=1 or not np.isfinite(y).all():raise RuntimeError('Delay failed')
                    safe=guard(1,fs,60,y);delay.append({'requests':int(stats[0]),'accepted':int(stats[1]),'forced_retirements':int(stats[2]),'max_live_banks':int(stats[3]),'wait_ms':[float(t) if t>=0 else None for t in ev[:stats[0]]],'raw_peak_dbfs':peak(y),'guarded':metrics(safe,y),'tail_rms':rms(y[n:])})
                rows.append({'id':item['id'],'stage':item.get('stage','mixed_music'),'offset':offset,'fs':fs,'frames':len(v),'limiter':vals,'paired_ms_per_audio_second':times,'delay':delay});print(item['id'],offset,flush=True)
    a.output.write_text(json.dumps({'schema':1,'rows':rows,'limits':'Finite declared kernel ceiling; 16x independent peak estimate, not certified true peak. Paired native timings include prepare; no host. Delay requests 250ms apart including final silence; accepted target is not audible arrival; forced fade retires old tails. Correlated music excerpts, not isolated stems.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
