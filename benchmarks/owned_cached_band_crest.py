"""Private original DSP comparative benchmark. No host or listening claims."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly,butter,sosfilt
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def peak(x):return db(np.max(np.abs(x)))
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--music',action='store_true');a=p.parse_args();rows=[];seen=set()
 with tempfile.TemporaryDirectory() as d:
  lib=pathlib.Path(d)/'lab.so';subprocess.run(['g++','-std=c++17','-O3','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_cached_band_crest.cpp'),str(ROOT/'tests/fixtures/owned_bass_cascade.cpp'),'-o',str(lib)],check=True)
  dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');f=dll.research_render;c=dll.cascade_render
  for fn in (f,c):fn.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];fn.restype=C.c_int
  def run(fn,k,fs,x):
   y=np.empty_like(x);start=time.perf_counter_ns();ok=fn(k,fs,x,y,len(x));ms=(time.perf_counter_ns()-start)/1e6/(len(x)/fs)
   if ok!=1 or not np.isfinite(y).all():raise RuntimeError('render failed')
   return y,ms
  for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
   src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
   if digest!=item['sha256'] or digest in seen:raise ValueError('fingerprint mismatch or duplicate')
   seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
   if fs not in (44100,48000,96000) or not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('invalid audio')
   if x.shape[1]==1:x=np.repeat(x,2,axis=1)
   parts=[(0,x)] if not a.music else [(round(frac*len(x))-5*fs,x[round(frac*len(x))-5*fs:round(frac*len(x))+5*fs]) for frac in (.25,.5,.75)]
   for offset,v in parts:
    v=np.ascontiguousarray(v);base=run(c,0,fs,v)[0];times=[[],[]];ys=[None,None]
    for rep in range(3):
     for k in ((0,1) if rep%2==0 else (1,0)):ys[k],ms=run(f,k,fs,base);times[k].append(ms)
     if not np.array_equal(*ys):raise RuntimeError('guard parity failed')
    dpad=np.ascontiguousarray(np.pad(v,((0,fs//4),(0,0))));ds=[run(f,k,fs,dpad)[0] for k in (2,3)];delay=[]
    for y in ds:
     safe=run(f,1,fs,y)[0];tail=y[len(v):];lp=sosfilt(butter(4,250,fs=fs,output='sos'),tail,axis=0);hp=sosfilt(butter(4,250,fs=fs,btype='highpass',output='sos'),tail,axis=0)
     delay.append(dict(sample_peak=peak(y),estimated16_peak=peak(resample_poly(y,16,1,axis=0,window=('kaiser',8.6))),guarded_estimated16_peak=peak(resample_poly(safe,16,1,axis=0,window=('kaiser',8.6))),guarded_gain_db=db(rms(safe)/rms(ds[0])),tail_rms=rms(tail),tail_low_rms=rms(lp),tail_high_rms=rms(hp)))
    cs=[run(f,k,fs,v)[0] for k in (4,5)];comp=[];n=round(fs*.005);end=len(v)//n*n;inp=np.max(np.abs(v[:end].reshape(-1,n,2)),axis=(1,2));rise=np.diff(inp,prepend=0);mask=rise>=np.quantile(rise,.9)
    for y in cs:
     m=y*rms(cs[0])/rms(y);mp=np.max(np.abs(m[:end].reshape(-1,n,2)),axis=(1,2));comp.append(dict(gain_db=db(rms(y)/rms(v)),matched_peak=peak(m),onset_proxy=db(rms(mp[mask])),matched_difference_db=db(rms(m-cs[0])/rms(cs[0]))))
    rows.append(dict(id=item['id'],offset=offset,frames=len(v),fs=fs,guard_exact=True,guard_times=times,delay=delay,compressor=comp));print(item['id'],offset,flush=True)
 a.output.write_text(json.dumps(dict(schema=1,rows=rows,limits='Paired native timing includes prepare, no DAW CPU. Estimated16 peak not certified true peak. Fully wet delay only, filtered tail metrics not isolated stems. Crest timing proxy not subjective transient quality.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
