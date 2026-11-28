"""Original stateful delay: independent scalar recurrence and callback partition checks."""
import ctypes,json,time,math,argparse
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def main():
    p=argparse.ArgumentParser();p.add_argument('library');p.add_argument('sources',nargs=3);p.add_argument('--output',required=True);a=p.parse_args()
    lib=ctypes.CDLL(str(Path(a.library).resolve()));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');lib.mod_create.argtypes=[ctypes.c_double];lib.mod_create.restype=ctypes.c_void_p;lib.mod_destroy.argtypes=[ctypes.c_void_p];lib.mod_target.argtypes=[ctypes.c_void_p,ptr];lib.mod_target.restype=ctypes.c_int;lib.mod_reset.argtypes=[ctypes.c_void_p];lib.mod_process.argtypes=[ctypes.c_void_p,ptr,ptr,ctypes.c_uint];lib.mod_process.restype=ctypes.c_int
    rng=np.random.default_rng(841);rows=[];known=[];recorded=[];total=0
    initial=np.array([7.4,3.,.91,1.57,.35,.5,2.,.5]);targets=[np.array([13.,6.,1.7,2.7,-.89,.85,4.,.8]),np.array([4.,1.,.17,.3,.92,.3,.5,1.]),np.array([9.,2.,4.7,2.2,.74,1.,7.,.2])]
    def run(x,fs,block,events):
        nonlocal total
        x=np.ascontiguousarray(x,dtype=np.float64);y=np.empty_like(x);h=lib.mod_create(fs);assert h
        pos=0;idx=0;elapsed=0.;worst=0.;miss=0;calls=0
        try:
            assert lib.mod_target(h,initial);lib.mod_reset(h)
            while pos<len(x):
                if idx<len(events) and pos==events[idx][0]:assert lib.mod_target(h,events[idx][1]);idx+=1
                end=min(pos+block,len(x),events[idx][0] if idx<len(events) else len(x));start=time.perf_counter();assert lib.mod_process(h,x[pos:end],y[pos:end],end-pos);dt=time.perf_counter()-start;elapsed+=dt;worst=max(worst,dt);miss+=dt>(end-pos)/fs;calls+=1;pos=end
        finally:lib.mod_destroy(h)
        total+=1;return y,dict(seconds=elapsed,worst_call_seconds=worst,deadline_misses=miss,calls=calls)
    def oracle(x,fs,events):
        # Non-circular history, direct sample indexing, same documented smoothing law.
        out=np.zeros_like(x);history=np.zeros_like(x);cur=initial.copy();target=cur.copy();phase=0.;alpha=1-math.exp(-1/(.01*fs));k=0
        for i in range(len(x)):
            if k<len(events) and i==events[k][0]:target=events[k][1];k+=1
            cur+=alpha*(target-cur);center,depth,rate,spread,fb,cross,drive,mix=cur;wet=np.zeros(2)
            for c in (0,1):
                d=(center+depth*math.sin(phase+c*spread))*fs*.001;j=int(d);f=d-j
                wet[c]=(1-f)*(history[i-j,c] if i>=j else 0.)+f*(history[i-j-1,c] if i>j else 0.)
            v=(1-cross)*wet+cross*wet[::-1];history[i]=np.clip(x[i]+fb*np.tanh(drive*v)/drive,-8,8);out[i]=(1-mix)*x[i]+mix*wet;phase+=2*math.pi*rate/fs
            if phase>=2*math.pi:phase-=2*math.pi
        return out
    for fs in (44100,48000,96000,192000):
        x=rng.uniform(-.7,.7,(fs//5,2));events=[(len(x)//3,targets[0]),(len(x)*2//3,targets[1])];y,t=run(x,fs,127,events);ref=oracle(x,fs,events);known.append(dict(rate=fs,max_abs_error=float(np.max(abs(y-ref)))))
        n=fs*3;x=rng.uniform(-.9,.9,(n,2));events=[(fs//2,targets[0]),(fs+13,targets[1]),(fs*2+29,targets[2])];base=None
        for b in (64,127,512,1024):
            y,t=run(x,fs,b,events)
            if base is None:base=y.copy()
            rows.append(dict(rate=fs,block=b,peak=float(np.max(abs(y))),max_block_difference=float(np.max(abs(y-base))),**t))
        for i,path in enumerate(a.sources):
            x,sr=sf.read(path,always_2d=True);x=x[:2*sr];x=np.repeat(x,2,axis=1) if x.shape[1]==1 else x;g=math.gcd(fs,sr);x=resample_poly(x,fs//g,sr//g,axis=0);events=[(len(x)//3,targets[i]),(len(x)*2//3,targets[(i+1)%3])];y,t=run(x,fs,127,events);z,_=run(x,fs,1024,events);recorded.append(dict(rate=fs,source=i,peak=float(np.max(abs(y))),max_block_difference=float(np.max(abs(y-z))),**t))
        print(fs,'oracle',known[-1],'max block',max(r['max_block_difference'] for r in rows if r['rate']==fs),flush=True)
    report=dict(scope='original native prototype, independent scalar oracle, reused recorded inputs; Python callback timing proxy',renders=total,known=known,stress=rows,recorded=recorded);Path(a.output).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print('renders',total,'worst oracle',max(r['max_abs_error'] for r in known),'max peak',max(r['peak'] for r in rows),'misses',sum(r['deadline_misses'] for r in rows),'calls',sum(r['calls'] for r in rows),'recorded peak',max(r['peak'] for r in recorded),flush=True)
if __name__=='__main__':main()
