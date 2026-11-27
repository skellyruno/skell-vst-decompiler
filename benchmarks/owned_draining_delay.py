"""Compare independently implemented delay transitions on the same private excerpts."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);a=p.parse_args();rows=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'delay.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_draining_delay.cpp'),str(ROOT/'tests/fixtures/owned_bounded_peak.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');ev=np.ctypeslib.ndpointer(dtype=np.float64,ndim=1,flags='C_CONTIGUOUS');f=dll.drain_render;f.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint,ev];f.restype=C.c_int;g=dll.bounded_peak;g.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];g.restype=C.c_int
        for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all():raise ValueError('Invalid input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            n=len(x);x=np.ascontiguousarray(np.pad(x,((0,fs//4),(0,0))));ys=[];events=[]
            for k in range(2):
                y=np.empty_like(x);e=np.empty(2)
                if f(k,fs,x,y,len(x),e)!=1 or not np.isfinite(y).all():raise RuntimeError('Delay failure')
                ys.append(y);events.append([None if v<0 else float((v-i*len(x)//3)*1000/fs) for i,v in enumerate(e,1)])
            guard=np.empty_like(x)
            if g(2,fs,60,ys[1],guard,len(guard))!=1 or not np.isfinite(guard).all():raise RuntimeError('Guard failure')
            ys.append(guard);metrics=[{'peak_dbfs':db(np.max(np.abs(y))),'estimated16_peak_dbfs':db(np.max(np.abs(resample_poly(y,16,1,axis=0,window=('kaiser',8.6))))),'tail_rms':rms(y[n:]),'gain_db_relative_to_draining':db(rms(y)/rms(ys[1]))} for y in ys]
            rows.append({'id':item['id'],'stage':item['stage'],'request_to_active_target_ms':events,'metrics':metrics});print(item['id'],flush=True)
    a.output.write_text(json.dumps({'schema':1,'order':['previous_output_crossfade','draining_input_crossfade','draining_plus_release_bound'],'rows':rows,'limits':'Active target denotes old crossfade completion for previous design and new bank acceptance for draining design; not time of audible new echo. 250ms measured tail, not entire decay. No host, tempo automation or listening claim.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
