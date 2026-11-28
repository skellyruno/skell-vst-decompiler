"""Private follow-up: intersample estimate convergence and local native timing.
Keep per-recording measurements private. Neither a certified true-peak test nor DAW CPU.
"""
import argparse,ctypes as C,hashlib,json,pathlib,statistics,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();rows=[];seen=set()
    with tempfile.TemporaryDirectory() as d:
        lib=pathlib.Path(d)/'native.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_adaptive_native.cpp'),'-o',str(lib)],check=True)
        dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');f=dll.adaptive_native;f.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int;g=dll.guard_native;g.argtypes=[C.c_double,ptr,ptr,C.c_uint];g.restype=C.c_int
        for item in json.loads(a.manifest.read_text())['inputs']:
            src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
            if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
            seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
            if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all():raise ValueError('Invalid input')
            if x.shape[1]==1:x=np.repeat(x,2,axis=1)
            x=np.ascontiguousarray(x);pad=np.ascontiguousarray(np.pad(x,((0,40),(0,0))));buf=np.empty_like(pad)
            if f(6,fs,7.83,pad,buf,len(pad))!=1:raise RuntimeError('Color render failed')
            color=buf[40:].copy();guard=np.empty_like(color)
            if g(fs,color,guard,len(color))!=1 or not np.isfinite(guard).all():raise RuntimeError('Guard failed')
            values=[]
            for y in (color,color*10**(-3/20),guard,guard*10**(-2.5/20)):
                values.append([db(np.max(np.abs(y)))]+[db(np.max(np.abs(resample_poly(y,k,1,axis=0,window=('kaiser',8.6))))) for k in (4,8,16)])
            # Timings on all 36 excerpts, three alternating paired repetitions; output allocated before clock.
            timing=[];out=np.empty_like(x)
            for pair in ((0,3),(4,6)):
                times=[[],[]]
                for rep in range(3):
                    for j in ((0,1) if rep%2==0 else (1,0)):
                        start=time.perf_counter_ns();ok=f(pair[j],fs,7.8342437744140625,x,out,len(x));end=time.perf_counter_ns()
                        if ok!=1 or not np.isfinite(out).all():raise RuntimeError('Timing render failed')
                        times[j].append((end-start)/1e6/(len(x)/fs))
                timing.append([statistics.median(t) for t in times])
            rows.append({'id':item['id'],'stage':item['stage'],'peaks_dbfs':values,'paired_ms_per_audio_second':timing});print(item['id'],flush=True)
    a.output.write_text(json.dumps({'schema':1,'rows':rows,'peak_order':['untrimmed','fixed_minus3','guard_minus1','guard_minus1_then_minus2p5'],'peak_estimator':['sample','4x','8x','16x'],'timing_order':['original_leveler_vs_adaptive','original_color_vs_split'],'limits':'Local native wall time includes prepare and adapter, not host CPU. Kaiser polyphase interpolation estimates, not certified true peaks. No listening claim.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
