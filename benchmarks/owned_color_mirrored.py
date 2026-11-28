"""Native FIR hot-loop comparison, private fingerprinted audio only."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--music',action='store_true');a=p.parse_args();rows=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'color.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_color_mirrored.cpp'),'-o',str(lib)],check=True)
        f=C.CDLL(str(lib)).mirrored_color;ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');f.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all():raise ValueError('Invalid audio')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            parts=[(0,x)] if not a.music else [(round(frac*len(x))-5*fs,x[round(frac*len(x))-5*fs:round(frac*len(x))+5*fs]) for frac in (.25,.5,.75)]
            for offset,v in parts:
                v=np.ascontiguousarray(v);ys=[np.empty_like(v),np.empty_like(v)];times=[[],[]]
                for rep in range(3):
                    for k in ((0,1) if rep%2==0 else (1,0)):
                        start=time.perf_counter_ns();ok=f(k,fs,v,ys[k],len(v));end=time.perf_counter_ns()
                        if ok!=1 or not np.isfinite(ys[k]).all():raise RuntimeError('Render failed')
                        times[k].append((end-start)/1e6/(len(v)/fs))
                    if not np.array_equal(*ys):raise RuntimeError('Output mismatch')
                rows.append({'id':item['id'],'offset':offset,'frames':len(v),'fs':fs,'exact':True,'ms_per_audio_second':times});print(item['id'],offset,flush=True)
    a.output.write_text(json.dumps({'schema':1,'rows':rows,'limits':'Exact numeric equality for tested inputs and compiler; wall time includes prepare; not DAW CPU or cross-compiler bit identity.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
