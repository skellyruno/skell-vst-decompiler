"""Native pairwise streaming and LP validation on authorized private excerpts."""
import argparse,ctypes as C,hashlib,json,pathlib,time,subprocess,tempfile
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from pair_bound import kernel,previous,lp,detector,CEILING
from alias_reference import render,db,rms
ROOT=pathlib.Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=39);a=p.parse_args();rows=[];oracle=[];seen=set();h=kernel();rng=np.random.default_rng(721)
 with tempfile.TemporaryDirectory() as d:
  lib=pathlib.Path(d)/'pair.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-ffp-contract=off','-shared','-fPIC','-I'+str(ROOT/'experiments/engine_lab'),str(ROOT/'tests/fixtures/owned_forward_pair_cap.cpp'),str(ROOT/'tests/fixtures/owned_forward_pair_stream.cpp'),'-o',str(lib)],check=True)
  dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');f=dll.pair_stream;f.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int;cap=dll.pair_cap;cap.argtypes=[ptr,ptr,C.c_double];cap.restype=C.c_double
  def check(w,r):
   w=np.ascontiguousarray(w);r=np.ascontiguousarray(r);old=previous(w,r);new=max(old,cap(w,r,CEILING));return old,new
  if a.start==0:
   for i in range(256):
    w=rng.normal(0,.4,17);r=np.exp(-1/(.001*rng.uniform(1,60,17)*48000));old,new=check(w,r);peak=lp(w,r,new)
    if peak>CEILING+2e-8:raise RuntimeError('LP violation')
    oracle.append(dict(kind='random',old=old,new=new,lp_peak=peak))
  for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
   src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
   if digest!=item['sha256'] or digest in seen:raise ValueError('fingerprint mismatch')
   seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
   if len(x)<fs or x.shape[1] not in (1,2) or not np.isfinite(x).all():raise ValueError('invalid input')
   if x.shape[1]==1:x=np.repeat(x,2,axis=1)
   positions=(.25,.5,.75) if item['stage']=='mixed_music' else (.5,)
   for fraction in positions:
    start=round(fraction*len(x))-fs//2;v=x[start:start+fs];base=np.ascontiguousarray(render(v,fs,4,40,.45,.475));times=[[],[]];ys=[np.empty_like(base),np.empty_like(base)]
    for rep in range(3):
     for k in ((0,1) if rep%2==0 else (1,0)):
      t=time.perf_counter_ns();ok=f(k,fs,1.,base,ys[k],len(base));times[k].append((time.perf_counter_ns()-t)/1e6/(len(base)/fs))
      if ok!=1 or not np.isfinite(ys[k]).all():raise RuntimeError('render failure')
     if np.any(np.abs(ys[1])+1e-12<np.abs(ys[0])):raise RuntimeError('unexpected attenuation')
    metrics=[]
    for y in ys:
     padded=np.pad(y,((8,8),(0,0)));win=np.lib.stride_tricks.sliding_window_view(padded,17,axis=0)
     declared=float(np.max(np.abs(win@h.T)))
     if declared>CEILING+1e-12:raise RuntimeError('reconstruction violation')
     metrics.append(dict(gain_db=db(rms(y)/rms(base)),sample_peak_dbfs=db(np.max(np.abs(y))),declared_peak=declared,estimated16_peak_dbfs=db(np.max(np.abs(resample_poly(y,16,1,axis=0,window=('kaiser',8.6)))))))
    r=detector(base,fs)
    for group in np.array_split(np.arange(fs//4,3*fs//4),4):
     at=int(group[np.argmax(np.max(np.abs(base[group]),axis=1))]);seg=base[at-8:at+9];poles=r[at-8:at+9];weights=[sign*phase*seg[:,ch] for phase in h for ch in (0,1) for sign in (1,-1)]
     pairs=[check(w,poles) for w in weights];old=min(p[0] for p in pairs);new=min(p[1] for p in pairs);peak=max(lp(w,poles,new) for w in weights)
     if peak>CEILING+2e-8:raise RuntimeError('audio LP violation')
     oracle.append(dict(kind='audio',id=item['id'],stage=item['stage'],start_frame=start,old=old,new=new,lp_peak=peak))
    rows.append(dict(id=item['id'],stage=item['stage'],start_frame=start,fs=fs,frames=len(v),metrics=metrics,times=times));print(item['id'],start,flush=True)
 a.output.write_text(json.dumps(dict(schema=1,rows=rows,oracle=oracle,limits='One-second reused excerpts, not independent recordings or held-out. Native guard against identical offline saturated inputs, finite declared kernel only. LP numerical tolerance. Native wall time includes prepare, not DAW CPU. 16x estimates not certified true peaks.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
