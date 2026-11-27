"""Bounded reconstruction research on fingerprinted private vocals; no host claim."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);a=p.parse_args();rows=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'peak.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_bounded_peak.cpp'),str(ROOT/'tests/fixtures/owned_transition_peak.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');b=dll.bounded_peak;b.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];b.restype=C.c_int
        c=dll.selective_color;g=dll.reconstruction_guard
        for f in (c,g):f.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);base=np.empty_like(x)
            if c(1,fs,x,base,len(x))!=1 or not np.isfinite(base).all():raise RuntimeError('Color failed')
            values=[]
            for mode in range(5):
                y=np.empty_like(base);start=time.perf_counter_ns();ok=g(mode,fs,base,y,len(base)) if mode<2 else b(mode-2,fs,60,base,y,len(base));ms=(time.perf_counter_ns()-start)/1e6/(len(base)/fs)
                if ok!=1 or not np.isfinite(y).all():raise RuntimeError('Guard failed')
                values.append({'gain_db':db(rms(y)/rms(base)),'sample_peak_dbfs':db(np.max(np.abs(y))),'estimated_16x_peak_dbfs':db(np.max(np.abs(resample_poly(y,16,1,axis=0,window=('kaiser',8.6))))),'native_ms_per_audio_second':ms})
            rows.append({'id':item['id'],'stage':item['stage'],'metrics':values});print(item['id'],flush=True)
    a.output.write_text(json.dumps({'schema':1,'order':['old_signed','old_absolute','new_absolute','lobe','release_prefix'],'rows':rows,'limits':'Independent 16x estimates, declared finite four-phase ceiling only for bounded variants. Single call wall time includes prepare; not paired DAW CPU. No listening or production adoption.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
