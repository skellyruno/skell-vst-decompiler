"""Private real-audio benchmark plus controlled limiter distortion diagnostics."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def peak(x):return db(np.max(np.abs(x)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--music',action='store_true');p.add_argument('--tones',action='store_true');a=p.parse_args();rows=[];tones=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'lab.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_budget_quiet_symmetric.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');g=dll.research_guard;g.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint,ptr];g.restype=C.c_int;c=dll.research_color;b=dll.research_delay
        for f in (c,b):f.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        def run(f,k,fs,x,rel=None):
            y=np.empty_like(x);stat=np.zeros(1);t=time.perf_counter_ns();ok=f(k,fs,rel,x,y,len(x),stat) if rel is not None else f(k,fs,x,y,len(x));ms=(time.perf_counter_ns()-t)/1e6/(len(x)/fs)
            if ok!=1 or not np.isfinite(y).all():raise RuntimeError('Render failed')
            return y,ms,float(stat[0])
        def metrics(y,base):return {'gain_db':db(rms(y)/rms(base)),'sample_peak_dbfs':peak(y),'estimated16_peak_dbfs':peak(resample_poly(y,16,1,axis=0,window=('kaiser',8.6))),'matched_difference_db':db(rms(y*rms(base)/max(rms(y),1e-15)-base)/max(rms(base),1e-15))}
        if a.tones:
            fs=48000;t=np.arange(2*fs+256)/fs
            for hz in (20,50,100,1000,4000):
                for amp in (1.5,3.):
                    x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t),.7*amp*np.sin(2*np.pi*hz*t))));v=[]
                    for rel in (1.,5.,10.,20.,60.,1000.):
                        ms=[]
                        for k in (0,1):
                            y=run(g,k,fs,x,rel)[0][fs:2*fs,0];z=np.abs(np.fft.rfft(y))**2;fund=z[hz];harm=z[2*hz::hz].sum();ms.append({'thd_dbc':db(np.sqrt(harm/fund)),'gain_db':db(rms(y)/rms(x[fs:2*fs,0]))})
                        v.append({'release_ms':rel,'metrics':ms})
                    tones.append({'hz':hz,'amplitude':amp,'releases':v})
        for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid audio')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            parts=[(0,x)] if not a.music else [(round(frac*len(x))-5*fs,x[round(frac*len(x))-5*fs:round(frac*len(x))+5*fs]) for frac in (.25,.5,.75)]
            for offset,v in parts:
                v=np.ascontiguousarray(v);pad=np.ascontiguousarray(np.pad(v,((0,40),(0,0))));color=[];times=[[],[]]
                for rep in range(3):
                    ys=[None,None]
                    for k in ((0,1) if rep%2==0 else (1,0)):
                        y,ms,_=run(c,k,fs,pad);ys[k]=y;times[k].append(ms)
                    color.append(float(np.max(np.abs(ys[0]-ys[1]))))
                base=ys[0][40:].copy();limit=[]
                for rel in (1.,10.,60.):
                    old=run(g,0,fs,base,rel)[0];new=run(g,1,fs,base,rel)[0];fast,_,skip=run(g,2,fs,base,rel);auto=run(g,3,fs,base,rel)[0]
                    if not np.array_equal(new,fast) or not np.array_equal(auto,new if rel<=10 else old):raise RuntimeError('Guard parity failed')
                    limit.append({'release_ms':rel,'metrics':[{'gain_db':db(rms(y)/rms(base)),'sample_peak_dbfs':peak(y)} for y in (old,new)],'quiet_fraction':skip})
                guard_times=[[],[]]
                for rep in range(3):
                    for j in ((0,1) if rep%2==0 else (1,0)):
                        _,ms,_=run(g,j+1,fs,base,1.);guard_times[j].append(ms)
                n=len(v);dpad=np.ascontiguousarray(np.pad(v,((0,fs//4),(0,0))));a0=run(b,0,fs,dpad)[0];a1=run(b,1,fs,dpad)[0];a2=run(g,3,fs,a0,60.)[0];a3=run(g,3,fs,a1,60.)[0]
                delay=[dict(metrics(y,a0),tail_rms=rms(y[n:])) for y in (a0,a1,a2,a3)]
                rows.append({'id':item['id'],'offset':offset,'fs':fs,'frames':n,'limiter':limit,'guard_times':guard_times,'color_times':times,'color_max_error':max(color),'delay':delay});print(item['id'],offset,flush=True)
    a.output.write_text(json.dumps({'schema':1,'rows':rows,'tones':tones,'limits':'Real audio is private; coherent tone harmonic-bin tests are technical diagnostics. Delay fully wet sample budget, not certified true peak. Paired native timing includes prepare/adapter; no host. Selection fixed at prepare.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
