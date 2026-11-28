"""Native lifted DC and history-constrained limiter research, private audio only."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--tones',action='store_true');a=p.parse_args();rows=[];tones=[];seen=set();j=np.arange(17);h=[]
 for phase in range(4):
  t=j-8-phase*.25;v=np.sinc(t)*(.42+.5*np.cos(np.pi*t/9)+.08*np.cos(2*np.pi*t/9));v=np.eye(1,17,8).ravel() if phase==0 else v;h.append(v/v.sum())
 h=np.array(h)
 with tempfile.TemporaryDirectory() as d:
  lib=pathlib.Path(d)/'lab.so';subprocess.run(['g++','-std=c++17','-O3','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(ROOT/'experiments/engine_lab'),str(ROOT/'tests/fixtures/owned_lift_history.cpp'),'-o',str(lib)],check=True)
  dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS');c=dll.lifted_color;c.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];c.restype=C.c_int;g=dll.history_guard;g.argtypes=[C.c_int,C.c_double,C.c_double,ptr,ptr,C.c_uint];g.restype=C.c_int
  def run(fn,k,fs,x,rel=None):
   y=np.empty_like(x);t=time.perf_counter_ns();ok=fn(k,fs,x,y,len(x)) if rel is None else fn(k,fs,rel,x,y,len(x));ms=(time.perf_counter_ns()-t)/1e6/(len(x)/fs)
   if ok!=1 or not np.isfinite(y).all():raise RuntimeError('render failure')
   return y,ms
  def metrics(y,base):
   den=np.sum(base*base,axis=1);gain=np.divide(np.sum(y*base,axis=1),den,out=np.ones(len(base)),where=den>1e-10);valid=(den[1:]>1e-10)&(den[:-1]>1e-10);win=np.lib.stride_tricks.sliding_window_view(np.pad(y,((8,8),(0,0))),17,axis=0);declared=float(np.max(np.abs(win@h.T)))
   if declared>10**(-1/20)+1e-12:raise RuntimeError('kernel ceiling failed')
   return dict(gain_db=db(rms(y)/rms(base)),sample_peak_dbfs=db(np.max(np.abs(y))),declared_peak=declared,estimated16_peak_dbfs=db(np.max(np.abs(resample_poly(y,16,1,axis=0,window=('kaiser',8.6))))),gain_step_rms=rms(np.diff(gain)[valid]))
  if a.tones:
   fs=48000;t=np.arange(3*fs+256)/fs
   for hz in (20,50,100):
    for amp in (.9,1.5,3.):
     x=amp*np.sin(2*np.pi*hz*t)+.05*np.sin(2*np.pi*7000*t);x=np.ascontiguousarray(np.column_stack((x,.7*x)))
     for rel in (1.,10.,60.):
      vals=[]
      for k in (0,2):
       y=run(g,k,fs,x,rel)[0][2*fs:3*fs,0];z=np.abs(np.fft.rfft(y))**2;bins=[7000+i*hz for i in range(-8,9) if i];vals.append(dict(sidebands_dbc=db(np.sqrt(z[bins].sum()/z[7000])),gain_db=db(rms(y)/rms(x[2*fs:3*fs,0]))))
      tones.append(dict(hz=hz,amplitude=amp,release_ms=rel,metrics=vals))
  for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
   src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
   if digest!=item['sha256'] or digest in seen:raise ValueError('fingerprint mismatch')
   seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
   if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('invalid input')
   if x.shape[1]==1:x=np.repeat(x,2,axis=1)
   parts=[(0,x)] if item['stage']!='mixed_music' else [(round(frac*len(x))-5*fs,x[round(frac*len(x))-5*fs:round(frac*len(x))+5*fs]) for frac in (.25,.5,.75)]
   for offset,v in parts:
    v=np.ascontiguousarray(v);n=len(v);xpad=np.ascontiguousarray(np.pad(v,((0,40+fs//4),(0,0))));ys=[None]*4;ct=[[] for _ in ys]
    for rep in range(3):
     for k in (range(4) if rep%2==0 else reversed(range(4))):ys[k],ms=run(c,k,fs,xpad);ct[k].append(ms)
    err=[float(np.max(np.abs(y-ys[0]))) for y in ys]
    if max(err)>2e-10:raise RuntimeError('color parity failed')
    base=np.ascontiguousarray(ys[0][40:40+n]);gt=[[],[],[]];gs=[None]*3
    for rep in range(3):
     for k in (range(3) if rep%2==0 else reversed(range(3))):gs[k],ms=run(g,k,fs,base,1.);gt[k].append(ms)
     if not np.array_equal(gs[0],gs[1]) or np.any(np.abs(gs[2])+1e-12<np.abs(gs[1])):raise RuntimeError('guard parity failed')
    rows.append(dict(id=item['id'],stage=item['stage'],offset=offset,frames=n,fs=fs,color_error=err,color_times=ct,guard=[metrics(y,base) for y in gs],guard_times=gt));print(item['id'],offset,flush=True)
 a.output.write_text(json.dumps(dict(schema=1,rows=rows,tones=tones,limits='Full available vocal excerpts, 10s music excerpts; prior cohort. Color comparison includes 250ms appended silence. Gain-step and two-tone sideband diagnostics are not subjective quality. Declared finite kernel only, independent16x estimates not certified true peak. Native timing includes setup.'),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
