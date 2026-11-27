"""Private authorized owned-audio benchmark. No vendor or DAW processing."""
import argparse,ctypes as C,hashlib,json,pathlib,subprocess,tempfile,time
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
ROOT=pathlib.Path(__file__).resolve().parents[1]
def db(x):return float(20*np.log10(max(float(x),1e-15)))
def rms(x):return float(np.sqrt(np.mean(x*x)))
def peak(x):return db(np.max(np.abs(x)))
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=9);p.add_argument('--tones',action='store_true');a=p.parse_args();rows=[];tones=[];seen=set()
 with tempfile.TemporaryDirectory() as d:
  lib=pathlib.Path(d)/'lib.so';subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'tests/fixtures/owned_transition_peak.cpp'),'-o',str(lib)],check=True)
  dll=C.CDLL(str(lib));ptr=np.ctypeslib.ndpointer(dtype=np.float64,ndim=2,flags='C_CONTIGUOUS');g=dll.reconstruction_guard;c=dll.selective_color;t=dll.transition_render
  for f in (g,c):f.argtypes=[C.c_int,C.c_double,ptr,ptr,C.c_uint];f.restype=C.c_int
  t.argtypes=[C.c_double,ptr,ptr,C.c_uint];t.restype=C.c_int
  def render(f,mode,fs,x):
   y=np.empty_like(x);start=time.perf_counter_ns();ok=f(mode,fs,x,y,len(x)) if mode is not None else f(fs,x,y,len(x));ms=(time.perf_counter_ns()-start)/1e6/(len(x)/fs)
   if ok!=1 or not np.isfinite(y).all():raise RuntimeError('Render failure')
   return y,ms
  if a.tones:
   for fs in (44100,48000,96000):
    t0=np.arange(fs//2+fs//4+256)/fs
    for hz in (3004,11004,17004,20004):
     for amp in (.1,.5,.9):
      x=np.ascontiguousarray(np.column_stack((amp*np.sin(2*np.pi*hz*t0),amp*np.cos(2*np.pi*hz*t0))));metrics=[]
      for k in range(4):
       y,ms=render(c,k,fs,x);z=np.abs(np.fft.rfft(y[fs//2:fs//2+fs//4,0]))**2;n=fs//4;z[1:len(z)-(n%2==0)]*=2;bin=round(hz*n/fs);fund=z[bin];z[::bin]=0
       metrics.append([db(np.sqrt(2*fund)/n),db(np.sqrt(z.sum())/n),ms])
      tones.append({'fs':fs,'hz':hz,'amp':amp,'metrics':metrics})
  for item in json.loads(a.manifest.read_text())['inputs'][a.start:a.start+a.count]:
   src=pathlib.Path(item['path']);digest=hashlib.sha256(src.read_bytes()).hexdigest()
   if digest!=item['sha256'] or digest in seen:raise ValueError('Fingerprint mismatch or duplicate')
   seen.add(digest);x,fs=sf.read(src,dtype='float64',always_2d=True)
   if not len(x) or x.shape[1] not in (1,2) or not np.isfinite(x).all() or rms(x)<=1e-12:raise ValueError('Invalid input')
   if x.shape[1]==1:x=np.repeat(x,2,axis=1)
   x=np.ascontiguousarray(x);colors=[render(c,k,fs,x) for k in range(4)];base=colors[1][0];pred,pms=render(g,0,fs,base);safe,sms=render(g,1,fs,base);fixed=base*10**(-3/20);metrics=[]
   for y,ms in [(base,colors[1][1]),(fixed,0),(pred,pms),(safe,sms)]:metrics.append({'sample_peak':peak(y),'est4':peak(resample_poly(y,4,1,axis=0,window=('kaiser',8.6))),'est16':peak(resample_poly(y,16,1,axis=0,window=('kaiser',8.6))),'gain_db':db(rms(y)/rms(base)),'ms_per_audio_second':ms})
   # Include a 250 ms tail. Transitions measured, not a listening quality score.
   pad=np.ascontiguousarray(np.pad(x,((0,fs//4),(0,0))));dy,dt=render(t,None,fs,pad)
   rows.append({'id':item['id'],'stage':item['stage'],'headroom':metrics,'color':[{'peak':peak(y),'gain_db':db(rms(y)/rms(x)),'ms':ms} for y,ms in colors],'delay':{'peak':peak(dy),'tail_rms':rms(dy[len(x):]),'ms':dt}});print(item['id'],flush=True)
 a.output.write_text(json.dumps({'schema':1,'rows':rows,'tones':tones,'limits':'Owned kernels, fixed 4-phase bound is not certified true peak. 16x estimates independent of bound. Color 40/80 samples alignment; wall time includes setup. No subjective or host tests.'},indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
